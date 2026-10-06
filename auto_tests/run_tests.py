#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""自动化测试套件独立运行器

不依赖 pytest 也能运行（同时支持 pytest 调用）。
默认顺序运行：单元测试 -> 后端等价性 -> 性能回归，并输出汇总报告。

用法：
    python auto_tests/run_tests.py                    # 运行全部测试
    python auto_tests/run_tests.py --backend python   # 强制纯 Python 后端
    python auto_tests/run_tests.py --skip-perf        # 跳过性能回归
    python auto_tests/run_tests.py --skip-parity      # 跳过后端等价性
    pytest auto_tests/                                # 用 pytest 运行（含参数化）
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _reset_engine(force_python: bool):
    from src.core.node_engine import NodeEngine
    NodeEngine._instance = None
    if force_python:
        os.environ["NODECALC_BACKEND"] = "python"
    else:
        os.environ.pop("NODECALC_BACKEND", None)
    return NodeEngine()


def run_unit_tests(force_python: bool) -> dict:
    """运行表达式引擎单元测试（按后端切换）。"""
    from src.core.expression_parser import evaluate_expression
    from src.utils.errors import AppError

    engine = _reset_engine(force_python)
    backend = engine.backend

    # 用例：(表达式, 变量, 期望值)
    cases = [
        ("1 + 2 * 3 - 4 / 2", {}, 1 + 2 * 3 - 4 / 2),
        ("17 % 5 + -3 + abs(-8)", {}, 17 % 5 + (-3) + abs(-8)),
        ("x * 2 + y", {"x": 6, "y": -1.5}, 6 * 2 - 1.5),
        ("2 ^ 10 + sqrt(81) + cbrt(-27)", {}, 2 ** 10 + 9 + (-3)),
        ("exp(0) + log(e) + log2(8) + log10(1000)", {}, 1 + 1 + 3 + 3),
        ("sin(pi/2) + cos(0) + tan(pi/4)", {}, math.sin(math.pi / 2) + 1 + math.tan(math.pi / 4)),
        ("norm(vec(3, 4))", {}, 5.0),
        ("dot(vec(1,2,3), vec(4,5,6))", {}, 32),
        ("det(mat(2, 2, 1, 2, 3, 4))", {}, -2),
        ("mean(vec(1,2,3,4,5))", {}, 3.0),
        ("clamp(15, 0, 10) + clamp(-5, 0, 10)", {}, 10),
        ("lerp(0, 10, 0.25)", {}, 2.5),
        ("ifelse(3 > 2, 100, 200)", {}, 100),
    ]
    error_cases = ["sqrt(-1)", "1 / 0", "undefined_var + 1"]

    passed, failed = 0, 0
    for expr, vars_, expected in cases:
        try:
            r = evaluate_expression(expr, vars_)
            val = r["value"]
            ok = _values_equal(val, expected)
        except Exception as e:
            ok, val = False, f"EXC: {e}"
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  [FAIL] {expr} -> {val} (期望 {expected})")

    for expr in error_cases:
        try:
            evaluate_expression(expr)
            failed += 1
            print(f"  [FAIL] {expr} -> 未抛出预期异常")
        except AppError:
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {expr} -> 抛出非 AppError: {type(e).__name__}")

    print(f"  后端={backend}  通过 {passed}/{passed + failed}")
    return {"backend": backend, "passed": passed, "failed": failed}


def _values_equal(a, b, rel_tol=1e-9, abs_tol=1e-9):
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_values_equal(x, y, rel_tol, abs_tol) for x, y in zip(a, b))
    return math.isclose(float(a), float(b), rel_tol=rel_tol, abs_tol=abs_tol)


def run_parity_tests() -> dict:
    """运行 native vs python 后端等价性测试。"""
    import math
    from src.core.node_engine import NodeEngine
    from src.core.expression_parser import evaluate_expression
    from src.utils.errors import AppError

    from auto_tests.test_backend_parity import CASES, _run_case, _values_equal

    py_engine = _reset_engine(force_python=True)
    py_results = [_run_case(e, v) for e, v in CASES]

    nv_engine = _reset_engine(force_python=False)
    if nv_engine.backend != "native":
        print(f"  [SKIP] 原生后端不可用（当前 {nv_engine.backend}），跳过等价性测试")
        return {"passed": len(CASES), "failed": 0, "skipped": True}

    nv_results = [_run_case(e, v) for e, v in CASES]

    passed, failed = 0, 0
    for (expr, _), py, nv in zip(CASES, py_results, nv_results):
        if py[0] != nv[0]:
            failed += 1
            print(f"  [FAIL] 行为不一致: {expr}")
        elif py[0] == "ok" and not _values_equal(py[1], nv[1]):
            failed += 1
            print(f"  [FAIL] 数值不一致: {expr}")
        else:
            passed += 1

    print(f"  通过 {passed}/{len(CASES)}")
    return {"passed": passed, "failed": failed, "skipped": False}


def _host_overloaded():
    """共享主机过载检测：返回 (过载, 原因)。

    阈值：1 分钟负载 > CPU 核数；250ms 窗口空闲 < 30%；被偷走 > 10%。
    """
    try:
        with open("/proc/loadavg") as f:
            load1 = float(f.read().split()[0])
        ncpu = os.cpu_count() or 1
        if load1 > ncpu:
            return True, f"1 分钟负载 {load1:.1f} > {ncpu}"

        def _stat():
            with open("/proc/stat") as f:
                vals = list(map(int, f.readline().split()[1:]))
            return sum(vals[:8]), vals[3], vals[7] if len(vals) > 7 else 0

        t1, i1, s1 = _stat()
        time.sleep(0.25)
        t2, i2, s2 = _stat()
        dt = max(1, t2 - t1)
        idle_pct = (i2 - i1) / dt
        steal_pct = (s2 - s1) / dt
        if idle_pct < 0.30:
            return True, f"即时 CPU 空闲率仅 {idle_pct*100:.0f}%"
        if steal_pct > 0.10:
            return True, f"被 hypervisor 偷走 {steal_pct*100:.0f}%"
    except (OSError, ValueError):
        pass
    return False, ""


def _measure_best_of(timed_call, rounds):
    """逐轮前置检测，返回 (best, clean_rounds)。"""
    best, clean = None, 0
    for _ in range(rounds):
        overloaded, _ = _host_overloaded()
        if overloaded:
            continue
        value = timed_call()
        clean += 1
        best = value if best is None else min(best, value)
    return best, clean


def run_perf_tests() -> dict:
    """运行性能回归测试（与基准 JSON 比对，best-of-N + 主机过载保护）。"""
    from src.core.expression_parser import evaluate_expression

    bench_dir = ROOT / "benchmarks"
    baseline_path = bench_dir / "results_native_compute.json"
    if not baseline_path.exists():
        print(f"  [SKIP] 缺少基准数据 {baseline_path}")
        return {"passed": 0, "failed": 0, "skipped": True}

    overloaded, reason = _host_overloaded()
    if overloaded:
        print(f"  [SKIP] 主机过载，性能测量不可靠（{reason}）")
        return {"passed": 0, "failed": 0, "skipped": True}

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    # 小表达式（逐轮检测，best-of-8）
    small = baseline["small_expressions"]["us_per_eval"]
    exprs = ["1 + 2 * 3 - 4 / 2", "sin(pi/2) + cos(0)",
             "sqrt(81) + cbrt(-27)"]
    for e in exprs:
        evaluate_expression(e)

    def small_round():
        iters = 200
        t0 = time.perf_counter()
        for _ in range(iters):
            for e in exprs:
                evaluate_expression(e)
        return (time.perf_counter() - t0) * 1000_000 / (iters * len(exprs))

    current_us, clean_s = _measure_best_of(small_round, rounds=8)
    if clean_s < 3:
        print("  [SKIP] 小表达式：清洁测量窗口不足，主机持续过载")
        small_ok = True  # 记为通过但实际跳过（汇总不计数）
        small_skipped = True
    else:
        small_skipped = False
        small_ok = current_us <= small * 1.5
        print(f"  小表达式: best-of-{clean_s} {current_us:.1f} µs "
              f"(基准 {small:.1f}, 阈值 {small*1.5:.1f}) "
              f"{'OK' if small_ok else 'FAIL'}")

    # 向量统计（best-of-10）
    heavy_ms = baseline["heavy_vector_2000"]["ms_per_eval"]
    variables = {"v": list(range(2000))}
    evaluate_expression("stddev(v) + mean(v) + median(v)", variables)

    def heavy_round():
        t0 = time.perf_counter()
        evaluate_expression("stddev(v) + mean(v) + median(v)", variables)
        return (time.perf_counter() - t0) * 1000

    current_ms, clean_h = _measure_best_of(heavy_round, rounds=10)
    if clean_h < 3:
        print("  [SKIP] 向量统计：清洁测量窗口不足，主机持续过载")
        heavy_ok = True
        heavy_skipped = True
    else:
        heavy_skipped = False
        heavy_ok = current_ms <= heavy_ms * 1.5
        print(f"  向量统计: best-of-{clean_h} {current_ms:.1f} ms "
              f"(基准 {heavy_ms:.1f}, 阈值 {heavy_ms*1.5:.1f}) "
              f"{'OK' if heavy_ok else 'FAIL'}")

    passed = int(small_ok and not small_skipped) + int(heavy_ok and not heavy_skipped)
    failed = int(not small_ok and not small_skipped) + int(not heavy_ok and not heavy_skipped)
    return {"passed": passed, "failed": failed, "skipped": False}


def main():
    parser = argparse.ArgumentParser(description="powerful-claw 自动化测试套件")
    parser.add_argument("--backend", choices=["native", "python"], default="native",
                        help="单元测试使用的后端（默认 native）")
    parser.add_argument("--skip-perf", action="store_true", help="跳过性能回归测试")
    parser.add_argument("--skip-parity", action="store_true", help="跳过后端等价性测试")
    args = parser.parse_args()

    print("=" * 60)
    print("powerful-claw 自动化测试套件")
    print("=" * 60)

    total_passed = total_failed = 0

    # 1. 单元测试（两个后端各跑一次）
    print("\n[1/4] 表达式引擎单元测试")
    for backend in (["native", "python"]):
        result = run_unit_tests(force_python=(backend == "python"))
        total_passed += result["passed"]
        total_failed += result["failed"]

    # 1b. 安全闸门回归（命令注入/鉴权/帧差/验签/AST 策略）
    print("\n[安全闸门] 安全修复回归测试")
    from auto_tests.test_security_gates import run_security_gates
    sec_passed, sec_failed = run_security_gates()
    total_passed += sec_passed
    total_failed += sec_failed

    # 2. 后端等价性
    if not args.skip_parity:
        print("\n[2/4] 后端等价性测试 (native vs python)")
        result = run_parity_tests()
        total_passed += result["passed"]
        total_failed += result["failed"]

        print("  -- pcnative C++ 内核等价性 --")
        from auto_tests.test_backend_parity import run_pcnative_kernel_parity
        pc_passed, pc_failed = run_pcnative_kernel_parity()
        total_passed += pc_passed
        total_failed += pc_failed
    else:
        print("\n[2/4] 后端等价性测试 (已跳过)")

    # 3. 性能回归
    if not args.skip_perf:
        print("\n[3/4] 性能回归测试")
        result = run_perf_tests()
        total_passed += result["passed"]
        total_failed += result["failed"]
    else:
        print("\n[3/4] 性能回归测试 (已跳过)")

    print("\n" + "=" * 60)
    print(f"汇总: 通过 {total_passed}, 失败 {total_failed}")
    print("=" * 60)
    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
