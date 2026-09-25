# 🧮 表达式引擎与原生后端（src/core）

[← 中文文档索引](INDEX.md) ｜ [← 架构总览](architecture.md)

> 节点化数学计算引擎：44 个运算节点组成计算图，同一份节点逻辑有 C++17、cppyy、纯 Python 三种实现，运行时自动选择最快的可用后端。

---

## 文件组成

| 文件 | 作用 |
|------|------|
| `node_engine.py` | 44 个节点类 + 计算图；内嵌 C++ 源码（`EMBEDDED_CPP`）；后端选择 |
| `expression_parser.py` | 表达式字符串 → 节点计算图（词法/语法分析、变量绑定） |
| `native/nodecalc_capi.cpp` | C ABI 封装层，导出节点/图的创建、连接、执行接口 |
| `native/native_backend.py` | cffi（ABI 模式）Python↔DLL 桥接 |
| `native/build_native.py` | 免 cmake 的构建脚本：抽取内嵌 C++ → g++ 编译 DLL |

---

## 节点类型（44 类）

按类别覆盖：

- **算术**：加减乘除、取模、幂
- **函数**：指数/对数、开方、绝对值、取整
- **三角**：sin/cos/tan 及反三角
- **向量**：点积 `dot`、范数 `norm`、最大/最小、标准差 `stddev`、均值、中位数
- **矩阵**：`mat(...)` 构造、矩阵运算、LU 分解相关节点
- **统计 / 分支 / 逻辑**：聚合统计与条件分支
- **错误处理**：类型不匹配、除零等返回统一错误码而非崩溃

> 节点类型的枚举顺序（`NcKind 0–43`）必须与 `node_engine.py` 中 `_NODE_CLASS_NAMES` 严格一致，这是 C ABI 与 Python 对齐的契约。

---

## 三级后端链

启动时按顺序选择，第一个可用者生效：

```
native（编译好的 nodecalc_native.dll，cffi 调用）
   │  DLL 缺失 / 加载失败
   ▼
cppyy（JIT 调用内嵌 C++，需要 cppyy）
   │  不可用
   ▼
python（纯 Python 实现，始终可用）
```

### 环境变量

| 变量 | 作用 |
|------|------|
| `NODECALC_BACKEND=python` | 强制使用纯 Python（等价性基准/排障用） |
| `NODECALC_NO_AUTOBUILD=1` | DLL 缺失时禁止自动调用 g++ 编译 |

打包（PyInstaller）后 DLL 从 `sys._MEIPASS` 加载；DLL 由 `build/` 目录产出（已被 `.gitignore` 忽略）。

---

## 构建原生后端

需要 MinGW（gcc/g++，已在 `E:\mingw64\bin` 验证）：

```bash
# 发布构建（-O2 -DNDEBUG，静态链接）
python src/core/native/build_native.py

# 性能剖析构建（-pg，生成 gprof 数据 + chrono 阶段计时）
python src/core/native/build_native.py --profile
```

> Windows/MinGW 上 gprof 对 gmon.out 的解析可能为空（binutils 兼容问题），`build_native.py` 会以 chrono 阶段计时作为替代证据写入报告。

---

## 性能基准

基准脚本在 `benchmarks/`：

```bash
python benchmarks/perf_bench.py startup --runs 7          # 冷启动
python benchmarks/perf_bench.py compute --iters 2000      # 计算性能
python benchmarks/perf_bench.py compute --json-out benchmarks/results_native_compute.json
```

实测（同一机器、同一脚本）：

| 指标 | 纯 Python | native 后端 |
|------|-----------|-------------|
| 小表达式混合求值 | 基准 | 约 −50% 耗时 |
| 2000 元素向量统计 | 基准 | 约 15× 加速 |

小表达式场景解析器本身占主导，加速空间有限；**大数据量内核计算**才是 C++ 的决定性优势场景。两种后端校验和完全一致。

---

## 等价性与回归测试

- `auto_tests/test_backend_parity.py`：26 个用例，native ↔ python 数值（容差 1e-9）与错误码一致
- `auto_tests/test_expression_engine.py`：覆盖全部 44 个节点类型
- `auto_tests/test_performance.py`：性能回归阈值（默认 1.5× 基准）
- `benchmarks/parity_native.py`：独立等价性校验脚本

详见 [测试指南](testing.md)。

---

## 已知限制（测试中显式标注）

- 向量逐元素相加 `[1,2,3]+[4,5,6]`：当前按类型不匹配处理
- `mat()*mat()` 矩阵乘：尚未接通
- `<` / `>` 比较运算符：当前实现恒真

这些是引擎层的既有边界，不是后端差异；修复时应同步更新 C++ 与 Python 两套实现及枚举契约。

---

## 扩展新节点

1. 在 `node_engine.py` 增加节点类并登记到 `_NODE_CLASS_NAMES`（注意枚举顺序）
2. 在 `EMBEDDED_CPP` 与 `nodecalc_capi.cpp` 中添加对应 C++ 实现与 `NcKind`
3. 重新 `build_native.py` 构建 DLL
4. 在 `auto_tests/` 增加双后端用例
