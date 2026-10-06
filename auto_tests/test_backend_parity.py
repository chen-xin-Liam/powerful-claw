"""多后端等价性测试

在原生(native)与纯 Python(python)两个后端上分别运行同一批表达式，
断言：
  - 成功/失败行为一致
  - 成功时数值在浮点容差内相等
  - 失败时错误码一致

本测试对后端选择做显式控制，不依赖 conftest 的参数化 fixture。
"""
import contextlib
import os
import math

import numpy as np
import pytest
from PIL import Image

from src.core.node_engine import NodeEngine
from src.core.expression_parser import evaluate_expression
from src.utils.errors import AppError


# 覆盖全部节点类型的表达式集合（与 benchmarks/parity_native.py 同源）
CASES = [
    ("1 + 2 * 3 - 4 / 2", {}),
    ("17 % 5 + -3 + abs(-8)", {}),
    ("x * 2 + y", {"x": 6, "y": -1.5}),
    ("2 ^ 10 + sqrt(81) + cbrt(-27)", {}),
    ("exp(0) + log(e) + log2(8) + log10(1000)", {}),
    ("log(8, 2)", {}),
    ("sin(pi/2) + cos(0) + tan(pi/4)", {}),
    ("asin(1) + acos(1) + atan(1)", {}),
    ("sinh(0) + cosh(0) + tanh(100)", {}),
    ("vec(1, 2, 3) + vec(4, 5, 6)", {}),
    ("dot(vec(1,2,3), vec(4,5,6)) + norm(vec(3,4)) + sum(vec(1,2,3,4,5,6))", {}),
    ("det(mat(2, 2, 1, 2, 3, 4))", {}),
    ("transpose(mat(2, 3, 1, 2, 3, 4, 5, 6))", {}),
    ("mat(2, 2, 1, 0, 0, 1) * mat(2, 2, 5, 6, 7, 8)", {}),
    ("inv(mat(2, 2, 4, 7, 2, 6))", {}),
    ("mean(vec(1,2,3,4,5)) + stddev(vec(1,2,3,4,5))", {}),
    ("min(vec(5,1,3,2,4)) + max(vec(5,1,3,2,4)) + median(vec(5,1,3,2,4))", {}),
    ("clamp(15, 0, 10) + clamp(-5, 0, 10)", {}),
    ("lerp(0, 10, 0.25)", {}),
    ("ifelse(3 > 2, 100, 200) + ifelse(3 < 2, 100, 200)", {}),
    ("(1 > 0 && 2 > 1) ? 7 : 8", {}),
    ("dot(v, v)", {"v": [3, 4]}),
    ("det(m)", {"m": [[1, 2], [3, 4]]}),
    ("sqrt(-1)", {}),
    ("1 / 0", {}),
    ("undefined_var + 1", {}),
]


def _reset_engine(force_python: bool):
    NodeEngine._instance = None
    if force_python:
        os.environ["NODECALC_BACKEND"] = "python"
    else:
        os.environ.pop("NODECALC_BACKEND", None)
    return NodeEngine()


def _run_case(expr, variables):
    try:
        r = evaluate_expression(expr, variables)
        return ("ok", r["value"])
    except AppError as e:
        return ("error", str(e.code))


def _values_equal(a, b):
    if isinstance(a, list) or isinstance(b, list):
        if not isinstance(a, list) or not isinstance(b, list):
            return False
        if len(a) != len(b):
            return False
        return all(_values_equal(x, y) for x, y in zip(a, b))
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)


def test_native_backend_available():
    """确认原生后端在当前环境可加载（否则整个 parity 测试无意义）。"""
    engine = _reset_engine(force_python=False)
    assert engine.backend == "native", \
        f"原生后端未加载（当前 {engine.backend}），请先运行 build_native.py 编译 DLL"


@pytest.mark.parametrize("expr,variables", CASES)
def test_backend_parity(expr, variables):
    """每个用例在两个后端上行为与数值一致。"""
    py_engine = _reset_engine(force_python=True)
    py_result = _run_case(expr, variables)

    nv_engine = _reset_engine(force_python=False)
    nv_result = _run_case(expr, variables)

    # 行为一致
    assert py_result[0] == nv_result[0], \
        f"行为不一致: {expr} -> python={py_result[0]} native={nv_result[0]}"

    if py_result[0] == "ok":
        assert _values_equal(py_result[1], nv_result[1]), \
            f"数值不一致: {expr} -> python={py_result[1]} native={nv_result[1]}"
    else:
        # 错误场景：错误码一致
        assert py_result[1] == nv_result[1], \
            f"错误码不一致: {expr} -> python={py_result[1]} native={nv_result[1]}"


# ======================================================================
# pcnative 四组 C++ 内核的 native / python-fallback 等价性
# ======================================================================

from src.core.native import pcnative_backend as nb
from src.core import packet_codec


@contextlib.contextmanager
def _force_python_pcn():
    """强制 pcnative 走纯 Python 回退路径。"""
    nb.NATIVE_AVAILABLE = False
    old_packet = packet_codec._NATIVE
    packet_codec._NATIVE = False
    try:
        yield
    finally:
        nb.NATIVE_AVAILABLE = True
        packet_codec._NATIVE = old_packet


def _gradient_image(width=160, height=100):
    """确定性 RGB 梯度图（不依赖随机数）。"""
    gx = np.tile(np.linspace(0, 255, width, dtype=np.uint8), (height, 1))
    gy = np.tile(np.linspace(0, 255, height, dtype=np.uint8)[:, None],
                 (1, width))
    arr = np.stack(
        [gx, gy, (gx.astype(int) + gy.astype(int)).clip(0, 255)],
        axis=2).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


# pcnative 标量表达式子集 ↔ 节点图 Python 引擎
PCN_EXPR_CASES = [
    "1 + 2 * 3 - 4 / 2",
    "17 % 5 + -3 + abs(-8)",
    "2 ^ 10",
    "sin(pi/2) + cos(0)",
    "exp(0) + log(e) + log2(8) + log10(1000)",
    "sqrt(81) + cbrt(-27)",
    "clamp(15, 0, 10) + clamp(-5, 0, 10)",
    "lerp(0, 10, 0.25)",
    "(1 > 0 && 2 > 1) ? 7 : 8",
    "3 > 2 ? 100 : 200",
]


def test_pcnative_library_available():
    if not nb.NATIVE_AVAILABLE:
        pytest.skip("pcnative 未编译（make native）")


def test_pcn_ascii_parity():
    if not nb.NATIVE_AVAILABLE:
        pytest.skip("pcnative 未编译")
    from src.utils.image_processor import ImageProcessor
    proc = ImageProcessor()
    img = _gradient_image()
    for width, invert in [(60, False), (40, True), (80, False)]:
        native = proc.image_to_ascii(img, width=width, invert=invert)
        with _force_python_pcn():
            python = proc.image_to_ascii(img, width=width, invert=invert)
        assert native == python, f"ASCII 不一致 width={width} invert={invert}"


def test_pcn_pixel_matrix_parity():
    if not nb.NATIVE_AVAILABLE:
        pytest.skip("pcnative 未编译")
    from src.utils.image_processor import ImageProcessor
    proc = ImageProcessor()
    img = _gradient_image()
    native = proc.image_to_pixel_matrix(img, sample_size=20)
    with _force_python_pcn():
        python = proc.image_to_pixel_matrix(img, sample_size=20)
    assert native == python


def test_pcn_blocks_parity():
    if not nb.NATIVE_AVAILABLE:
        pytest.skip("pcnative 未编译")
    from src.utils.remote_desktop_streamer import RDConfig, BlockEncoder
    frame = _gradient_image(128, 96)
    mask = np.zeros((96, 128), np.uint8)
    mask[10:60, 20:90] = 255

    cfg = RDConfig()
    cfg.compress_blocks = True
    cfg.block_size = 32
    cfg.block_cache_size = 1000

    rn = BlockEncoder(cfg).encode_blocks(frame, diff_mask=mask, quality=70)
    with _force_python_pcn():
        rp = BlockEncoder(cfg).encode_blocks(frame, diff_mask=mask, quality=70)

    assert [(b["x"], b["y"], b["w"], b["h"]) for b in rn["data"]] == \
        [(b["x"], b["y"], b["w"], b["h"]) for b in rp["data"]]
    assert rn["changed"] == rp["changed"]
    assert [b["data"] for b in rn["data"]] == \
        [b["data"] for b in rp["data"]]


def test_pcn_expr_parity():
    if not nb.NATIVE_AVAILABLE:
        pytest.skip("pcnative 未编译")
    for expr in PCN_EXPR_CASES:
        nv = nb.expr_eval(expr)
        py = evaluate_expression(expr)["value"]
        assert math.isclose(float(nv), float(py), rel_tol=1e-9, abs_tol=1e-9), \
            f"表达式不一致: {expr} native={nv} python={py}"
    # 非法/除零：原生抛 ValueError
    with pytest.raises(ValueError):
        nb.expr_eval("1 / 0")


@pytest.mark.parametrize("payload", [b"", b"x", bytes(range(256)),
                                     os.urandom(500) if hasattr(os, "urandom")
                                     else b"a" * 500])
def test_pcn_pack_unpack_parity(payload):
    if not nb.NATIVE_AVAILABLE:
        pytest.skip("pcnative 未编译")
    f_native = packet_codec.pack_message(9, 42, payload)
    with _force_python_pcn():
        f_python = packet_codec.pack_message(9, 42, payload)
    assert f_native == f_python
    assert packet_codec.unpack_message(f_native) == (9, 42, payload)
    with _force_python_pcn():
        assert packet_codec.unpack_message(f_python) == (9, 42, payload)


def test_pcn_corrupt_frame_rejected():
    if not nb.NATIVE_AVAILABLE:
        pytest.skip("pcnative 未编译")
    frame = bytearray(packet_codec.pack_message(1, 1, b"abc"))
    frame[10] ^= 0xFF
    with pytest.raises(ValueError):
        packet_codec.unpack_message(bytes(frame))
    with _force_python_pcn():
        with pytest.raises(ValueError):
            packet_codec.unpack_message(bytes(frame))


def run_pcnative_kernel_parity():
    """供 auto_tests/run_tests.py 无 pytest 调用：返回 (passed, failed)。"""
    checks = [
        ("ascii 映射", test_pcn_ascii_parity),
        ("像素矩阵", test_pcn_pixel_matrix_parity),
        ("块规划/哈希", test_pcn_blocks_parity),
        ("标量表达式", test_pcn_expr_parity),
        ("封包 pack/unpack", lambda: test_pcn_pack_unpack_parity(b"abc123")),
        ("损坏帧拒绝", test_pcn_corrupt_frame_rejected),
    ]
    passed = failed = 0
    for name, fn in checks:
        try:
            fn()
            passed += 1
            print(f"  [OK] pcnative {name}")
        except Exception as e:  # noqa: BLE001 - 运行器需汇总
            failed += 1
            print(f"  [FAIL] pcnative {name}: {e}")
    return passed, failed
