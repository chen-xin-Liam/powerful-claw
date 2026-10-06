"""性能回归测试

用基准数据（来自 benchmarks/results_native_compute.json）作为阈值，
断言当前原生后端不发生严重回退。

抗噪设计（共享/云主机上绝对计时波动大）：
  1. 当前值取多次测量的最小值（best-of-N，最小化外部争用影响）；
  2. 基准同样为 best-of-N；
  3. 采样前检测主机负载，1 分钟 loadavg 持续高于 CPU 核数×1.25
     或即时空闲率过低时跳过测试，而非误报失败；
  4. 阈值采用 1.5x 容差。
"""
import json
import os
import time
from pathlib import Path

import pytest

from src.core.node_engine import NodeEngine
from src.core.expression_parser import evaluate_expression


ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "benchmarks"

SMALL_EXPRS = [
    "1 + 2 * 3 - 4 / 2",
    "17 % 5 + -3 + abs(-8)",
    "2 ^ 10 + sqrt(81) + cbrt(-27)",
    "exp(0) + log(e) + log2(8) + log10(1000)",
    "sin(pi/2) + cos(0) + tan(pi/4)",
]


def _host_overloaded():
    """返回 (是否过载, 原因)。仅 Linux 检测，其余平台放行。

    阈值：1 分钟负载 > CPU 核数；250ms 窗口空闲 < 30%；被偷走 > 10%。
    """
    try:
        load1 = float(Path("/proc/loadavg").read_text().split()[0])
        ncpu = os.cpu_count() or 1
        if load1 > ncpu:
            return True, f"1 分钟负载 {load1:.1f} > {ncpu}"

        def _stat():
            with open("/proc/stat") as f:
                vals = list(map(int, f.readline().split()[1:]))
            # user nice system idle iowait irq softirq steal ...
            total = sum(vals[:8])
            return total, vals[3], vals[7] if len(vals) > 7 else 0

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
    except OSError:
        pass
    return False, ""


def _measure_best_of(timed_call, rounds, min_clean=3):
    """逐轮前置检测，仅保留清洁窗口样本，返回 (best, clean_rounds)。

    测量期间突发争用只会抬高该轮样本，不可能成为最小值
    （只要存在 ≥2 个清洁轮）。
    """
    best = None
    clean = 0
    for _ in range(rounds):
        overloaded, _ = _host_overloaded()
        if overloaded:
            continue
        value = timed_call()
        clean += 1
        best = value if best is None else min(best, value)
    return best, clean


@pytest.fixture(autouse=True)
def _force_native_backend():
    """性能测试必须在原生后端上运行，显式重置单例避免被其他测试污染。"""
    os.environ.pop("NODECALC_BACKEND", None)
    NodeEngine._instance = None
    engine = NodeEngine()
    if engine.backend != "native":
        pytest.skip(f"原生后端不可用（当前 {engine.backend}），跳过性能回归")
    yield


def _load_baseline(filename):
    path = BENCH_DIR / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def test_small_expression_not_regression():
    """小表达式混合负载 best-of-N 不超过基准的 1.5 倍。"""
    baseline = _load_baseline("results_native_compute.json")
    if baseline is None or "small_expressions" not in baseline:
        pytest.skip("缺少小表达式基准数据 (results_native_compute.json)")

    for expr in SMALL_EXPRS:
        evaluate_expression(expr)

    iters = 200

    def one_round():
        t0 = time.perf_counter()
        for _ in range(iters):
            for expr in SMALL_EXPRS:
                evaluate_expression(expr)
        return (time.perf_counter() - t0) * 1000 * 1000 \
            / (iters * len(SMALL_EXPRS))

    us_per_eval, clean = _measure_best_of(one_round, rounds=8)
    if clean < 3:
        pytest.skip(f"清洁测量窗口不足（仅 {clean} 个），主机持续过载")

    baseline_us = baseline["small_expressions"]["us_per_eval"]
    threshold = baseline_us * 1.5
    print(f"小表达式: best-of-{clean} {us_per_eval:.1f} µs/eval, "
          f"基准 {baseline_us:.1f}, 阈值 {threshold:.1f}")
    assert us_per_eval <= threshold, \
        f"小表达式性能回退: {us_per_eval:.1f} > {threshold:.1f} µs/eval " \
        f"(基准 {baseline_us:.1f})"


def test_heavy_vector_not_regression():
    """2000 元素向量统计 best-of-N 不超过基准的 1.5 倍。"""
    baseline = _load_baseline("results_native_compute.json")
    if baseline is None or "heavy_vector_2000" not in baseline:
        pytest.skip("缺少向量统计基准数据 (results_native_compute.json)")

    variables = {"v": list(range(2000))}
    evaluate_expression("stddev(v) + mean(v) + median(v)", variables)

    def one_round():
        t0 = time.perf_counter()
        evaluate_expression("stddev(v) + mean(v) + median(v)", variables)
        return (time.perf_counter() - t0) * 1000

    ms_per_eval, clean = _measure_best_of(one_round, rounds=10)
    if clean < 3:
        pytest.skip(f"清洁测量窗口不足（仅 {clean} 个），主机持续过载")

    baseline_ms = baseline["heavy_vector_2000"]["ms_per_eval"]
    threshold = baseline_ms * 1.5
    print(f"2000 元素向量统计: best-of-{clean} {ms_per_eval:.1f} ms, "
          f"基准 {baseline_ms:.1f}, 阈值 {threshold:.1f}")
    assert ms_per_eval <= threshold, \
        f"向量统计性能回退: {ms_per_eval:.1f} > {threshold:.1f} ms/eval " \
        f"(基准 {baseline_ms:.1f})"


def test_native_backend_active():
    """确认测试在原生后端上运行（否则性能断言无意义）。"""
    engine = NodeEngine()
    assert engine.backend == "native", \
        f"性能测试需要原生后端，当前为 {engine.backend}"
