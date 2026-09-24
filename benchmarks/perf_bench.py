"""性能基准脚本（迁移前后使用同一脚本测量）

子命令：
  importtime   采集 `import src.ui.customtkinter_app` 的 -X importtime，输出 Top 热点与总耗时
  startup      多个全新子进程冷启动导入 UI 模块，输出中位加载耗时（核心验收指标）
  compute      NodeEngine 计算负载微基准（Python 后端 vs C++ 原生后端）

用法：
  python benchmarks/perf_bench.py importtime
  python benchmarks/perf_bench.py startup --runs 7
  python benchmarks/perf_bench.py compute --iters 2000
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMPORT_TARGET = "src.ui.customtkinter_app"


def _python_exe():
    return sys.executable


def cmd_importtime(args):
    """解析 -X importtime，输出 self 耗时 Top N 及目标模块累计耗时"""
    proc = subprocess.run(
        [_python_exe(), "-X", "importtime", "-c", f"import {IMPORT_TARGET}"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    rows = []
    for line in proc.stderr.splitlines():
        m = re.match(r"import time:\s+(\d+) \|\s+(\d+) \|(.*)", line)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(3).strip()))

    total_ms = next((cum / 1000 for _, cum, name in rows if name == IMPORT_TARGET), None)
    print(f"目标模块 {IMPORT_TARGET} 累计导入耗时: {total_ms:.1f} ms")
    print(f"{'self(ms)':>10}  {'cum(ms)':>10}  模块")
    for self_us, cum_us, name in sorted(rows, reverse=True)[:args.top]:
        print(f"{self_us / 1000:>10.1f}  {cum_us / 1000:>10.1f}  {name}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"total_ms": total_ms,
                        "top": [{"self_ms": s / 1000, "cum_ms": c / 1000, "module": n}
                                for s, c, n in sorted(rows, reverse=True)[:args.top]]},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")


def cmd_startup(args):
    """全新子进程冷导入，父进程计时；输出多次运行的统计值"""
    code = (
        "import time, sys;"
        f"t0=time.perf_counter(); import {IMPORT_TARGET};"
        "sys.stderr.write(f'{(time.perf_counter()-t0)*1000:.1f}')"
    )
    samples = []
    for i in range(args.runs):
        t0 = time.perf_counter()
        proc = subprocess.run([_python_exe(), "-c", code], cwd=ROOT,
                              capture_output=True, text=True)
        wall_ms = (time.perf_counter() - t0) * 1000
        # 优先使用进程内测量（剔除解释器自身冷启动），否则退回父进程墙钟
        inproc_ms = float(proc.stderr.strip().splitlines()[-1]) if proc.stderr.strip() else wall_ms
        samples.append(inproc_ms)
        print(f"run {i + 1}/{args.runs}: {inproc_ms:.1f} ms")

    result = {
        "runs": args.runs,
        "median_ms": round(statistics.median(samples), 1),
        "mean_ms": round(statistics.fmean(samples), 1),
        "min_ms": round(min(samples), 1),
        "max_ms": round(max(samples), 1),
        "samples_ms": [round(x, 1) for x in samples],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                       encoding="utf-8")


# NodeEngine 计算负载：覆盖算术/函数/向量/矩阵等 44 个节点的典型表达式
COMPUTE_EXPRESSIONS = [
    "1 + 2 * 3 - 4 / 2",
    "(2 + 3) ^ 2 + sqrt(16)",
    "sin(pi/2) + cos(0) + log(e)",
    "abs(-7) + max([3, 9]) + min([3, 9])",
    "sum([1,2,3,4,5,6])",
    "det(mat(2, 2, 1, 2, 3, 4))",
    "dot([1,2,3], [4,5,6])",
    "norm([3, 4])",
    "mean([1,2,3,4,5]) + sum([1,2,3,4,5])",
    "median([5,1,3,2,4]) + stddev([1,2,3,4,5])",
]


def _flatten_sum(value):
    """把标量/向量/矩阵结果归约为数值，用作正确性校验和"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        total = 0.0
        for item in value:
            total += _flatten_sum(item)
        return total
    return 0.0


def cmd_compute(args):
    """表达式引擎固定负载微基准（解析->节点图编译->执行），标注当前后端"""
    sys.path.insert(0, str(ROOT))
    from src.core.expression_parser import evaluate_expression
    from src.core.node_engine import NodeEngine

    backend = getattr(NodeEngine(), "backend", "unknown")

    def run_loop(expr, variables, iters):
        evaluate_expression(expr, variables)  # 预热
        t0 = time.perf_counter()
        checksum = 0.0
        for _ in range(iters):
            r = evaluate_expression(expr, variables)
            checksum += _flatten_sum(r.get("value"))
        return (time.perf_counter() - t0) * 1000, checksum

    # 场景 A：小表达式混合负载（Python 解析器占主导，反映交互输入场景）
    elapsed_ms, checksum = 0.0, 0.0
    for _ in range(args.iters):
        t0 = time.perf_counter()
        for expr in COMPUTE_EXPRESSIONS:
            r = evaluate_expression(expr)
            checksum += _flatten_sum(r.get("value"))
        elapsed_ms += (time.perf_counter() - t0) * 1000
    total_evals = args.iters * len(COMPUTE_EXPRESSIONS)
    result = {
        "backend": backend,
        "small_expressions": {
            "iters": args.iters,
            "expressions": len(COMPUTE_EXPRESSIONS),
            "total_evals": total_evals,
            "elapsed_ms": round(elapsed_ms, 1),
            "us_per_eval": round(elapsed_ms * 1000 / total_evals, 3),
            "evals_per_sec": round(total_evals / (elapsed_ms / 1000), 1),
            "checksum": round(checksum, 3),
        },
    }

    # 场景 B：2000 元素向量统计（节点内核大数据量，C++ 价值场景）
    heavy_vars = {"v": list(range(2000))}
    heavy_iters = max(5, args.iters // 100)
    heavy_ms, heavy_checksum = run_loop(
        "stddev(v) + mean(v) + median(v)", heavy_vars, heavy_iters)
    result["heavy_vector_2000"] = {
        "iters": heavy_iters,
        "elapsed_ms": round(heavy_ms, 1),
        "ms_per_eval": round(heavy_ms / heavy_iters, 3),
        "checksum": round(heavy_checksum, 3),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                       encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="AI电脑控制 性能基准（迁移前后统一口径）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_imp = sub.add_parser("importtime")
    p_imp.add_argument("--top", type=int, default=20)
    p_imp.add_argument("--json-out", default=None)
    p_imp.set_defaults(func=cmd_importtime)

    p_st = sub.add_parser("startup")
    p_st.add_argument("--runs", type=int, default=7)
    p_st.add_argument("--json-out", default=None)
    p_st.set_defaults(func=cmd_startup)

    p_cp = sub.add_parser("compute")
    p_cp.add_argument("--iters", type=int, default=2000)
    p_cp.add_argument("--json-out", default=None)
    p_cp.set_defaults(func=cmd_compute)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
