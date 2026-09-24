# 🧪 自动化测试指南

本项目提供两套测试体系：`auto_tests/`（自动化测试套件，针对核心表达式引擎与 C++ 原生后端）和 `tests/`（传统 pytest 单元测试）。本文档介绍 `auto_tests/` 的结构、运行方式与扩展方法。

---

## 📁 目录结构

```
auto_tests/
├── __init__.py              # 包说明
├── conftest.py              # pytest 公共 fixture（后端切换、求值辅助、近似断言）
├── test_expression_engine.py # 表达式引擎核心测试（覆盖全部 44 个节点类型）
├── test_backend_parity.py   # 多后端等价性测试（native ↔ python）
├── test_performance.py      # 性能回归测试（与基准 JSON 比对）
└── run_tests.py             # 独立运行器（不依赖 pytest）
```

---

## 🚀 运行方式

### 方式一：独立运行器（推荐，零额外依赖）

```bash
python auto_tests/run_tests.py
```

输出示例：

```
============================================================
powerful-claw 自动化测试套件
============================================================

[1/3] 表达式引擎单元测试
  后端=native  通过 16/16
  后端=python  通过 16/16

[2/3] 后端等价性测试 (native vs python)
  通过 26/26

[3/3] 性能回归测试
  小表达式: 71.5 µs (基准 88.2, 阈值 132.3) OK
  向量统计: 225.6 ms (基准 243.2, 阈值 364.8) OK

============================================================
汇总: 通过 60, 失败 0
============================================================
```

常用参数：

| 参数 | 说明 |
|------|------|
| `--backend python` | 单元测试强制使用纯 Python 后端 |
| `--skip-perf` | 跳过性能回归测试 |
| `--skip-parity` | 跳过后端等价性测试 |

### 方式二：pytest（含参数化后端）

```bash
# 运行全部测试
pytest auto_tests/

# 只跑表达式引擎测试（会在 native / python 两个后端各跑一遍）
pytest auto_tests/test_expression_engine.py -v

# 只跑性能回归
pytest auto_tests/test_performance.py -v -s
```

> 💡 `test_expression_engine.py` 通过 `conftest.py` 的 `backend` fixture 自动参数化，**每个测试用例会在 native 和 python 两个后端上各执行一次**。若原生后端不可用，native 用例会被自动跳过（不视为失败）。

---

## 🧩 测试内容说明

### 1. 表达式引擎核心测试（test_expression_engine.py）

覆盖全部 44 个节点类型，按类别分组：

| 类别 | 节点 | 测试要点 |
|------|------|----------|
| 算术 | Add / Sub / Mul / Div / Mod / Negate / Abs / Number / Variable | 基本运算、优先级、变量代入 |
| 幂指对 | Pow / Sqrt / Cbrt / Exp / Log / Log2 / Log10 | 对数底、立方根实根 |
| 三角 | Sin / Cos / Tan / Asin / Acos / Atan / Sinh / Cosh / Tanh | 弧度制、双曲函数 |
| 向量 | VecCreate / VecDot / VecNorm / VecSum | 点积、范数、求和 |
| 矩阵 | MatCreate / MatTranspose / MatDet / MatInverse | 行列式、转置、逆矩阵 |
| 统计 | Sum / Mean / StdDev / Min / Max / Median | 方差分母为 N（总体标准差） |
| 分支 | Clamp / Lerp / If | 钳制、线性插值、条件分支 |
| 错误 | — | 负数开方、除零、未定义变量均抛出 `AppError` |

> ⚠️ **已知限制（测试中已标注）**：
> - 向量逐元素加法 `vec() + vec()` 当前不被 `+` 运算符支持（类型不匹配）
> - 矩阵乘法 `mat() * mat()` 当前不被 `*` 运算符支持
> - 比较运算符 `<` / `>` 存在已知问题（恒返回真），测试中使用 `==` / `!=` 验证分支逻辑

### 2. 后端等价性测试（test_backend_parity.py）

在原生（native）与纯 Python（python）两个后端上分别运行同一批 26 个表达式，断言：
- 成功/失败行为一致
- 成功时数值在浮点容差（1e-9）内相等
- 失败时错误码一致

这是 C++ 迁移后的核心正确性保障——确保原生后端与参考实现（纯 Python）行为完全一致。

### 3. 性能回归测试（test_performance.py）

将当前性能与 `benchmarks/results_native_compute.json` 中的基准数据比对，阈值为基准的 **1.5 倍**（容差内允许机器抖动）：

| 场景 | 指标 | 基准 |
|------|------|------|
| 小表达式混合负载 | µs/eval | 88.2 |
| 2000 元素向量统计 | ms/eval | 243.2 |

若当前性能超过阈值则测试失败，提示性能回退。基准数据可通过 `python benchmarks/perf_bench.py compute --iters 2000 --json-out benchmarks/results_native_compute.json` 重新生成。

---

## 🔧 后端控制

NodeEngine 支持三级后端自动回退：**native → cppyy → python**。测试中通过环境变量控制：

| 环境变量 | 效果 |
|----------|------|
| （不设置） | 优先加载原生 C++ 后端，失败则回退 |
| `NODECALC_BACKEND=python` | 强制使用纯 Python 后端 |
| `NODECALC_NO_AUTOBUILD=1` | 禁止 DLL 缺失时自动编译 |

原生后端需先编译 DLL：

```bash
python src/core/native/build_native.py
```

---

## ➕ 编写新测试

### 添加表达式引擎测试用例

在 `test_expression_engine.py` 中按类别添加方法，使用 `eval_expr` fixture：

```python
class TestMyCategory:
    def test_my_case(self, backend, eval_expr):
        r = eval_expr("your_expression", {"var": value})
        assert_close(r["value"], expected_value)
```

`backend` fixture 会自动让该用例在两个后端各跑一遍。

### 添加等价性用例

在 `test_backend_parity.py` 的 `CASES` 列表中追加 `(表达式, 变量字典)` 即可。

### 运行单个测试

```bash
pytest auto_tests/test_expression_engine.py::TestArithmetic::test_basic_ops -v
```

---

## 📊 与基准测试的关系

`benchmarks/` 目录下有更详细的性能基准工具（启动时间、计算吞吐、大数据量场景），用于性能优化前后的定量对比。`auto_tests/test_performance.py` 是其轻量化回归版本，集成在日常测试流程中。
