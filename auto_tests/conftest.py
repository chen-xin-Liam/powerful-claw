"""pytest 公共 fixture：后端切换、表达式求值辅助。

通过 NODECALC_BACKEND 环境变量控制 NodeEngine 选择的后端，
并在 fixture 作用域内重置单例，确保测试隔离。
"""
import os
import math

import pytest

from src.core.node_engine import NodeEngine
from src.core.expression_parser import evaluate_expression


@pytest.fixture(params=["native", "python"], ids=["backend=native", "backend=python"])
def backend(request, monkeypatch):
    """参数化后端：在 native 与 python 之间切换。

    若当前环境无法加载原生后端，native 用例会被自动跳过（不视为失败）。
    """
    backend_name = request.param
    if backend_name == "python":
        monkeypatch.setenv("NODECALC_BACKEND", "python")
    else:
        monkeypatch.delenv("NODECALC_BACKEND", raising=False)

    NodeEngine._instance = None
    engine = NodeEngine()

    if backend_name == "native" and engine.backend != "native":
        pytest.skip(f"原生后端不可用（当前为 {engine.backend}），跳过 native 用例")

    yield engine.backend


@pytest.fixture
def eval_expr():
    """返回一个带变量的表达式求值辅助函数。"""
    def _eval(expr, variables=None):
        return evaluate_expression(expr, variables)
    return _eval


def assert_close(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
    """递归比较标量/向量/矩阵的近似相等。"""
    if isinstance(actual, list) and isinstance(expected, list):
        assert len(actual) == len(expected), f"长度不一致: {len(actual)} != {len(expected)}"
        for a, b in zip(actual, expected):
            assert_close(a, b, rel_tol, abs_tol)
    else:
        assert math.isclose(float(actual), float(expected), rel_tol=rel_tol, abs_tol=abs_tol), \
            f"{actual} != {expected}"
