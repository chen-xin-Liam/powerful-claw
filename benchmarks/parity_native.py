"""原生 C++ 后端 vs 纯 Python 后端 功能等价性测试

在同一进程内顺序切换后端（重置 NodeEngine 单例），对覆盖全部 44 个节点类型的
表达式集合逐项比对数值结果与错误行为。

用法：python benchmarks/parity_native.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.node_engine import NodeEngine
from src.core.expression_parser import evaluate_expression
from src.utils.errors import AppError

# (表达式, 变量) —— 覆盖算术/幂指对/三角/向量/矩阵/统计/分支等全部节点
CASES = [
    # 算术 9 节点：Add Sub Mul Div Mod Negate Abs + Number Variable
    ("1 + 2 * 3 - 4 / 2", {}),
    ("17 % 5 + -3 + abs(-8)", {}),
    ("x * 2 + y", {"x": 6, "y": -1.5}),
    # 幂指对 8 节点：Pow Sqrt Cbrt Exp Log Log2 Log10
    ("2 ^ 10 + sqrt(81) + cbrt(-27)", {}),
    ("exp(0) + log(e) + log2(8) + log10(1000)", {}),
    ("log(8, 2)", {}),
    # 三角 12 节点：sin cos tan asin acos atan sinh cosh tanh
    ("sin(pi/2) + cos(0) + tan(pi/4)", {}),
    ("asin(1) + acos(1) + atan(1)", {}),
    ("sinh(0) + cosh(0) + tanh(100)", {}),
    # 向量 5 节点：VecCreate VecAdd VecDot VecNorm VecSum
    ("vec(1, 2, 3) + vec(4, 5, 6)", {}),
    ("dot(vec(1,2,3), vec(4,5,6)) + norm(vec(3,4)) + sum(vec(1,2,3,4,5,6))", {}),
    # 矩阵 5 节点：MatCreate MatMul MatTranspose MatDet MatInverse
    ("det(mat(2, 2, 1, 2, 3, 4))", {}),
    ("transpose(mat(2, 3, 1, 2, 3, 4, 5, 6))", {}),
    ("mat(2, 2, 1, 0, 0, 1) * mat(2, 2, 5, 6, 7, 8)", {}),
    ("inv(mat(2, 2, 4, 7, 2, 6))", {}),
    # 统计 6 节点：Sum Mean StdDev Min Max Median
    ("mean(vec(1,2,3,4,5)) + stddev(vec(1,2,3,4,5))", {}),
    ("min(vec(5,1,3,2,4)) + max(vec(5,1,3,2,4)) + median(vec(5,1,3,2,4))", {}),
    # 分支 3 节点：Clamp Lerp If
    ("clamp(15, 0, 10) + clamp(-5, 0, 10)", {}),
    ("lerp(0, 10, 0.25)", {}),
    ("ifelse(3 > 2, 100, 200) + ifelse(3 < 2, 100, 200)", {}),
    ("(1 > 0 && 2 > 1) ? 7 : 8", {}),
    # 变量为向量/矩阵
    ("dot(v, v)", {"v": [3, 4]}),
    ("det(m)", {"m": [[1, 2], [3, 4]]}),
    # 错误场景：两端点应都失败
    ("sqrt(-1)", {}),
    ("1 / 0", {}),
    ("undefined_var + 1", {}),
]


def _reset_backend(force_python: bool):
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


def main():
    py_engine = _reset_backend(force_python=True)
    py_results = [_run_case(e, v) for e, v in CASES]

    nv_engine = _reset_backend(force_python=False)
    nv_results = [_run_case(e, v) for e, v in CASES]

    print(f"Python 后端: {py_engine.backend}  |  原生后端: {nv_engine.backend}")
    assert nv_engine.backend == "native", "原生 DLL 未加载，无法完成等价性验证"

    failures = 0
    for (expr, _), py, nv in zip(CASES, py_results, nv_results):
        if py[0] != nv[0]:
            print(f"[行为不一致] {expr}: python={py} native={nv}")
            failures += 1
        elif py[0] == "ok" and not _values_equal(py[1], nv[1]):
            print(f"[数值不一致] {expr}: python={py[1]} native={nv[1]}")
            failures += 1
        else:
            print(f"[OK] {expr} -> {nv[1]}")

    total = len(CASES)
    print(f"\n等价性结果: {total - failures}/{total} 通过")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
