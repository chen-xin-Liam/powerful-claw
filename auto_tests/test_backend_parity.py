"""多后端等价性测试

在原生(native)与纯 Python(python)两个后端上分别运行同一批表达式，
断言：
  - 成功/失败行为一致
  - 成功时数值在浮点容差内相等
  - 失败时错误码一致

本测试对后端选择做显式控制，不依赖 conftest 的参数化 fixture。
"""
import os
import math

import pytest

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
