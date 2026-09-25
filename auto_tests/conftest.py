"""pytest 公共 fixture：后端切换、表达式求值辅助。

通过 NODECALC_BACKEND 环境变量控制 NodeEngine 选择的后端，
并在 fixture 作用域内重置单例，确保测试隔离。
"""
import os
import math
import json

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


# ───────── MCP 导入测试隔离 ─────────

@pytest.fixture(autouse=True)
def _reset_extension_manager():
    """每个 MCP 测试前后重置 ExtensionManager 单例与配置，避免状态泄漏。"""
    from src.services.extension_manager import ExtensionManager
    from src.services.mcp_manager import mcp_manager

    config_path = os.path.join("src", "config", "extensions.json")

    # 测试前：清空内存单例与磁盘配置
    ExtensionManager._instance = None
    mcp_manager.servers.clear()
    _write_empty_config(config_path)

    yield

    # 测试后：清理残留
    ExtensionManager._instance = None
    mcp_manager.servers.clear()
    _write_empty_config(config_path)


def _write_empty_config(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"mcp_servers": [], "enabled_extensions": []}, f)
