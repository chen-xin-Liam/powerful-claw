# 🏗️ EXE 构建指南（Windows）

本文档介绍如何将项目打包为单文件 Windows 可执行程序（`.exe`），以及自动构建脚本的完整流水线、参数说明与常见问题。

---

## 🚀 一键构建（推荐）

```powershell
python scripts/build_exe.py
```

脚本会依次执行 5 个步骤：

| 步骤 | 内容 | 失败处理 |
|------|------|----------|
| 1. 环境检查 | Python ≥ 3.13、入口文件、spec；PyInstaller 缺失时自动 pip 安装 | 退出码 1 |
| 2. C++ 原生后端 | 检测 MinGW g++，编译 `nodecalc_native.dll` | 无 g++ 时跳过（运行时自动回退纯 Python） |
| 3. 自动化测试 | 运行 `auto_tests/run_tests.py`（60 项） | 失败则中止（退出码 2），防止带病打包 |
| 4. 清理 + 打包 | 清理旧 `build/`、`dist/`，调用 PyInstaller + spec | 退出码 1 |
| 5. 产物校验 | 确认 exe 真实存在，输出绝对路径与体积 | — |

成功输出示例：

```
[√] 构建成功！
[√] 产物: D:\powerful-claw\dist\AIComputerControl.exe
[√] 大小: 85.32 MB
   原生后端: 已包含 (nodecalc_native.dll)
```

退出码：`0` 成功；`1` 环境/构建失败；`2` 测试失败。

---

## ⚙️ 参数说明

| 参数 | 作用 |
|------|------|
| `--skip-tests` | 跳过自动化测试（不建议，仅用于快速验证打包流程） |
| `--skip-native` | 不编译 C++ 原生后端（产物仍可运行，节点计算使用纯 Python，大数据量场景慢约 10 倍） |
| `--windowed` | 生成**无控制台黑窗**的 GUI 程序（默认保留控制台，便于查看日志与排错） |
| `--no-upx` | 关闭 UPX 压缩（杀软误报、压缩异常或调试时使用；产物体积更大但启动略快） |
| `--no-clean` | 保留旧 `build/`、`dist/`，增量构建 |
| `--name MyApp` | 自定义 exe 文件名（生成 `dist/MyApp.exe`） |
| `--no-install-pyinstaller` | PyInstaller 缺失时不自动安装、直接报错 |

示例：

```powershell
# 正式发布：无控制台 + 自定义名称
python scripts/build_exe.py --windowed --name AIComputerControl-Setup

# 快速验证打包链路（跳过测试与原生编译）
python scripts/build_exe.py --skip-tests --skip-native
```

---

## 📦 打包内容（AIComputerControl.spec）

脚本基于根目录的 `AIComputerControl.spec` 打包（**单一配置源**，勿再向命令行重复传参）：

- **入口**：`src/main.py`，单文件（onefile）模式
- **静态资源**（保持 `src/<dir>` 目录结构，供代码按 `__file__` 相对路径定位）：
  `src/web`、`src/web_api`、`src/web_monitor`、`src/video_editor`
- **原生后端**：`src/core/native/nodecalc_native.dll`（存在时自动纳入，缺失不阻断）
- **hiddenimports**：websockets、soundcard、cv2、pyautogui、keyboard、customtkinter、pydantic、pydantic_settings、dotenv、cffi
- **excludes**：PyQt5/PyQt6/PySide2/PySide6/matplotlib（本项目使用 CustomTkinter/tkinter，Qt 绑定仅为间接依赖；排除可避免"multiple Qt bindings"冲突并大幅减小体积）

spec 支持以下环境变量覆盖（脚本已自动处理，一般无需手动设置）：

| 环境变量 | 作用 |
|----------|------|
| `AIAPP_CONSOLE=0` | 等同 `--windowed` |
| `AIAPP_UPX=0` | 等同 `--no-upx` |
| `AIAPP_NAME=xxx` | 等同 `--name` |

---

## 🔧 手动构建（等价命令）

```powershell
# 1.（可选）编译原生加速 DLL
python src/core/native/build_native.py

# 2. 直接调用 PyInstaller
python -m PyInstaller AIComputerControl.spec --noconfirm
```

产物位于 `dist/AIComputerControl.exe`。

---

## 🧪 构建后验证

```powershell
# 启动（默认控制台模式）
.\dist\AIComputerControl.exe

# 启动后自检（开发环境源码方式）
python test_main.py
```

建议首次运行新版本时观察控制台：

- 出现 `C++ 原生后端已加载 (cffi/nodecalc_native.dll)` → 原生加速生效
- 出现 `回退纯 Python 实现` → DLL 未打入或加载失败，功能不受影响

---

## ❓ 常见问题

### 1. `Aborting build ... multiple Qt bindings packages`

环境同时安装了 PyQt5 与 PyQt6（常见于装过 matplotlib 的开发环境）。spec 已在 `excludes` 中排除全部 Qt 绑定；若仍出现，检查是否有代码直接 import Qt。

### 2. 杀毒软件报毒 / exe 被删

onefile + UPX 压缩的 exe 易被启发式查杀。改用 `--no-upx`，或将产物目录加入杀软白名单。

### 3. exe 双击闪退

默认使用控制台模式便于排错；若用了 `--windowed`，先重新打一个控制台版本查看报错日志。常见原因：`.env` 未随程序分发、端口被占用。

### 4. 找不到 g++ / 想加速计算

安装 [MinGW-w64](https://www.mingw-w64.org/) 并将 `g++` 加入 PATH，重新运行构建脚本即可；也可单独执行 `python src/core/native/build_native.py`。

### 5. 修改了资源或新增 hidden import

直接编辑 `AIComputerControl.spec` 的 `datas` / `hiddenimports`，不要在脚本命令行重复添加——spec 是唯一配置源。

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `scripts/build_exe.py` | 一键自动构建脚本 |
| `AIComputerControl.spec` | PyInstaller 打包配置（单一配置源） |
| `src/core/native/build_native.py` | C++ 原生 DLL 构建脚本 |
| `auto_tests/run_tests.py` | 构建前自动运行的测试套件 |
