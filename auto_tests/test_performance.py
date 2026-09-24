"""性能回归测试

用 Python 基准数据（来自 benchmarks/results_*.json）作为阈值，
断言当前原生后端不发生严重回退。

阈值采用相对宽松的容差（1.5x），避免因机器抖动导致的误报。
若基准文件缺失则仅打印当前数据，不阻断测试。
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
    """小表达式混合负载不超过基准的 1.5 倍。"""
    baseline = _load_baseline("results_native_compute.json")
    if baseline is None or "small_expressions" not in baseline:
        pytest.skip("缺少小表达式基准数据 (results_native_compute.json)")

    # 预热
    for expr in SMALL_EXPRS:
        evaluate_expression(expr)

    iters = 500
    t0 = time.perf_counter()
    for _ in range(iters):
        for expr in SMALL_EXPRS:
            evaluate_expression(expr)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    us_per_eval = elapsed_ms * 1000 / (iters * len(SMALL_EXPRS))

    baseline_us = baseline["small_expressions"]["us_per_eval"]
    threshold = baseline_us * 1.5
    print(f"小表达式: 当前 {us_per_eval:.1f} µs/eval, 基准 {baseline_us:.1f}, 阈值 {threshold:.1f}")
    assert us_per_eval <= threshold, \
        f"小表达式性能回退: {us_per_eval:.1f} > {threshold:.1f} µs/eval (基准 {baseline_us:.1f})"


def test_heavy_vector_not_regression():
    """2000 元素向量统计不超过基准的 1.5 倍（C++ 价值场景）。"""
    baseline = _load_baseline("results_native_compute.json")
    if baseline is None or "heavy_vector_2000" not in baseline:
        pytest.skip("缺少向量统计基准数据 (results_native_compute.json)")

    variables = {"v": list(range(2000))}
    evaluate_expression("stddev(v) + mean(v) + median(v)", variables)  # 预热

    iters = 5
    t0 = time.perf_counter()
    for _ in range(iters):
        evaluate_expression("stddev(v) + mean(v) + median(v)", variables)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    ms_per_eval = elapsed_ms / iters

    baseline_ms = baseline["heavy_vector_2000"]["ms_per_eval"]
    threshold = baseline_ms * 1.5
    print(f"2000 元素向量统计: 当前 {ms_per_eval:.1f} ms, 基准 {baseline_ms:.1f}, 阈值 {threshold:.1f}")
    assert ms_per_eval <= threshold, \
        f"向量统计性能回退: {ms_per_eval:.1f} > {threshold:.1f} ms/eval (基准 {baseline_ms:.1f})"


def test_native_backend_active():
    """确认测试在原生后端上运行（否则性能断言无意义）。"""
    engine = NodeEngine()
    assert engine.backend == "native", \
        f"性能测试需要原生后端，当前为 {engine.backend}"
