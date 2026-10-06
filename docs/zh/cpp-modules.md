# powerful-claw C++ 化模块说明（pcnative）

> 本文说明本次以 C++17 重写的四组热路径模块、纯 C ABI、cffi 接入方式、Python 回退机制及性能收益。

## 一、总体设计

- **零第三方依赖**：仅使用 C++17 标准库；Windows 下静态链接运行时（`-static -static-libgcc -static-libstdc++`），目标机无需额外 DLL。
- **纯 C ABI**：所有对外函数声明在 [pcnative.h](file:///home/liam/ollama/powerful-claw/src/core/native/pcnative/pcnative.h)，实现在 [pcnative.cpp](file:///home/liam/ollama/powerful-claw/src/core/native/pcnative/pcnative.cpp)；C++ 异常全部在边界 catch，经 `thread_local` 的 `pcn_last_error()` 返回错误信息。
- **cffi ABI 模式接入**：Python 侧 [pcnative_backend.py](file:///home/liam/ollama/powerful-claw/src/core/native/pcnative_backend.py) 在运行时加载动态库，**无需编译期绑定**；加载失败时业务层自动回退纯 Python 实现。
- 数学引擎 nodecalc 此前已 C++ 化，本次不重复改造。

## 二、四组模块

### 1. 图像处理热点

- `pcn_ascii_gray`：灰度图 → ASCII/块字符画（1920×1080→200 列端到端 2.1–6.3×，映射内核本身远快于此）。
- `pcn_pixel_matrix_rgb`：整帧 RGB → 像素矩阵描述文本。
- `pcn_sampled_matrix`：**稀疏路径**，Python 侧只按网格坐标采样少量 RGB 点传入，零整帧拷贝；输出与整帧路径逐字节一致。

### 2. 帧差分块编码

- `pcn_plan_blocks`：整帧 + 掩码一次性完成块扫描与哈希（无掩码或变化密集时使用）。
- `pcn_scan_mask`：**稀疏路径**，只读取掩码、不访问 RGB，输出变化块坐标。
- `pcn_block_hash` / `pcn_adler32`：原始像素区域 / 连续字节的 adler32（与 `zlib.adler32` 一致），用作块缓存键。
- 接入点 [remote_desktop_streamer.py](file:///home/liam/ollama/powerful-claw/src/utils/remote_desktop_streamer.py)：**选中块超过半数 → 整帧 `plan_blocks`；否则 → `scan_mask` + 逐块 `adler32`**。典型远控场景（仅 2 块变化）**8.8×**（31.2ms→3.6ms）；全帧规划内核 **5.6×**。

### 3. 标量表达式解析器

- `pcn_expr_eval`：递归下降解析器，支持三目、`||`/`&&`、比较、算术、`^`（右结合）及 `abs/sqrt/cbrt/exp/log/log2/log10/三角/反三角/sign/pow/clamp/lerp/min/max/pi/e`。
- 接入点 math_calculator_tool：**无变量标量**走原生，结果附加 `"backend": "pcnative"`；**向量、含变量、未知函数自动回退**。批量标量求值 **约 76×**。

### 4. 核心计算 / 网络封包

- `pcn_pack` / `pcn_unpack`：PCN1 帧（16 字节头 `Struct("<4sBBBBII")`，魔数 `PCN1`、版本 1）打包/解包，含长度与魔数校验。
- `pcn_clamp` / `pcn_lerp` / `pcn_crc32`：标量工具；CRC32 为 slicing-by-8 实现，结果与 zlib 一致。
- Python 侧 [packet_codec.py](file:///home/liam/ollama/powerful-claw/src/core/packet_codec.py) 提供纯 Python（zlib/struct）回退。

## 三、C ABI 函数清单

| 函数 | 用途 |
|------|------|
| `pcn_version` / `pcn_last_error` / `pcn_free` | 版本、错误信息、释放库内分配的内存 |
| `pcn_ascii_gray` | 灰度图 → 字符画 |
| `pcn_pixel_matrix_rgb` / `pcn_sampled_matrix` | 整帧 / 稀疏采样 → 像素矩阵文本 |
| `pcn_plan_blocks` | 整帧 + 掩码 → 选中块（含 hash） |
| `pcn_scan_mask` | 仅掩码 → 变化块坐标 |
| `pcn_block_hash` / `pcn_adler32` | 区域像素 / 连续字节 adler32 |
| `pcn_expr_eval` | 标量表达式求值 |
| `pcn_pack` / `pcn_unpack` | PCN1 帧打包 / 解包 |
| `pcn_clamp` / `pcn_lerp` / `pcn_crc32` | 标量计算工具 |

返回约定：`PCN_OK=0`，`PCN_ERR=1`；指针类失败返回 `NULL` 并可经 `pcn_last_error` 取错误描述。

## 四、后端选择与回退

环境变量（在 [pcnative_backend.py](file:///home/liam/ollama/powerful-claw/src/core/native/pcnative_backend.py) 读取）：

| 变量 | 取值 | 说明 |
|------|------|------|
| `PCNATIVE_BACKEND` | `auto`（默认）/ `native` / `python` | auto：有库用原生、无库回退；python：强制纯 Python |
| `PCNATIVE_LIB` | 动态库绝对路径 | 显式指定库位置 |

库的候选查找路径：`src/core/native/pcnative/build/libpcnative.so`（Windows：`libpcnative.dll`/`pcnative.dll`；macOS：`.dylib`）。

**回退层次**：库加载失败 → 纯 Python 实现；业务层原生调用抛异常（如参数不支持）→ 当场回退；表达式含变量/向量/未知函数 → 回退原数学引擎。任何情况下功能不因缺少原生库而不可用。

## 五、等价性与测试

- [test_backend_parity.py](file:///home/liam/ollama/powerful-claw/auto_tests/test_backend_parity.py)：四组内核在 native / 强制 Python 两后端下对确定性输入做逐字节比对（含 10 条表达式、梯度图、参数化封包、损坏帧拒绝）。
- [test_security_gates.py](file:///home/liam/ollama/powerful-claw/auto_tests/test_security_gates.py)：持久化覆盖稀疏/密集块编码路径、帧缓存命中、封包与 AST 策略。
- 后端封装对所有返回块做画面边界校验（`_validate_block_coords`），即使 C 侧错误码与正常计数同值也不会把非法数据当块使用。`auto_tests/` 149 项全部通过。

## 六、无收益场景的诚实说明

以下场景纯 Python 路径本身已由 C 实现主导，原生版本不具优势，**保持 Python 路径更优**：

- 全帧块编码端到端（约 0.6×）：耗时主要在 JPEG 编码，原生规划省不出该成本；
- 封包 pack/unpack（0.5–0.9×）：zlib 的 CRC32 已高度优化，cffi 每次调用存在固定开销。

这些场景不影响默认行为：热路径收益集中在真实高频场景（稀疏变化、标量批量、图像映射）。
