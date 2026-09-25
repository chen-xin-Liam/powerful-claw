# 为 powerful-claw 做贡献

[English](../../CONTRIBUTING.md) | **简体中文** | [Русский](../ru/CONTRIBUTING.md) | [Français](../fr/CONTRIBUTING.md)

感谢你对本项目的兴趣！本指南介绍如何搭建开发环境、运行测试以及提交修改。

---

## 前置要求

| 要求 | 最低版本 | 备注 |
|------|----------|------|
| Python | 3.13 | 已在 Windows 10/11 验证 |
| MinGW（gcc/g++） | 13.x | 仅编译原生 C++ 后端时需要 |
| Git | 2.40+ | 版本控制 |

---

## 开发环境搭建

```bash
# 1. 克隆仓库
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw

# 2. 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate          # Windows PowerShell

# 3. 安装依赖
pip install -r requirements.txt
pip install pytest             # 测试运行器
```

**可选 —— 构建原生 C++ 后端**（性能基准测试需要）：

```bash
python src/core/native/build_native.py
```

产物为 `src/core/native/build/nodecalc_native.dll`。DLL 缺失时后端会自动降级为纯 Python。

---

## 运行应用程序

```bash
python src/main.py
```

首次启动会创建 `config/` 和 `logs/` 目录并打开主窗口。

---

## 运行测试

### 快速冒烟测试（独立运行器，无需 pytest）

```bash
python auto_tests/run_tests.py
```

### 完整测试套件

```bash
pytest auto_tests/
```

测试覆盖：
- 表达式引擎（全部 44 个节点类型）
- 原生后端与 Python 后端等价性
- 性能回归（与 `benchmarks/results_native_compute.json` 比对）
- API 连通性检查
- MCP 配置导入

---

## 构建可执行文件

```bash
python scripts/build_exe.py
```

产物输出到 `dist/AIComputerControl/`。构建使用 PyInstaller 与 spec 文件 `AIComputerControl.spec`。

试运行（只检查打包内容，不生成文件）：

```bash
python scripts/build_exe.py --dry-run
```

---

## 代码结构

```
src/
├── core/                  # 表达式引擎（纯 Python + 原生 C++ 后端）
│   ├── node_engine.py     # 44 个节点类型实现
│   ├── expression_parser.py
│   └── native/            # C++ 源码、构建脚本、cffi 桥接
├── services/              # 后台服务（WebSocket、API、AI、MCP 等）
├── ui/                    # CustomTkinter 主窗口 + PySide6 设置对话框
├── config/                # 设置、主题、扩展配置
└── system/                # 硬件交互、确认对话框

auto_tests/                # 自动化测试套件（pytest）
benchmarks/                # 性能基准 JSON
docs/                      # 文档（en/zh/ru/fr）
scripts/                   # 构建与维护脚本
```

---

## 代码规范

- **语言**：Python 3.13（鼓励使用类型注解，但不强制）
- **UI**：主窗口使用 CustomTkinter，设置对话框使用 PySide6
- **导入**：重型第三方模块（openai、PIL、pyautogui 等）必须在函数内部懒加载，而不是模块顶层导入。这能将冷启动时间控制在 1 秒以内。
- **后端回退**：核心计算模块在原生 DLL 不可用时必须能以纯 Python 运行。
- **注释**：为与现有代码库保持一致，注释请使用中文。
- **文档字符串**：模块级 docstring 为必需；公开 API 需提供函数级 docstring。

---

## 添加新的 MCP 服务器

使用内置导入器：

```python
from src.services.mcp_importer import add_from_template
add_from_template("github", env={"GITHUB_TOKEN": "your_token"})
```

或从标准 `.mcp.json` 文件导入：

```python
from src.services.mcp_importer import import_mcp_config
report = import_mcp_config("path/to/mcp.json")
```

可用模板：`filesystem`、`github`、`fetch`、`memory`、`sqlite`、`puppeteer`。

---

## 测试 API 连通性

提交涉及 AI 提供方代码的修改前，请先验证连通性：

```bash
python -m src.services.api_connectivity
```

该命令会检查所有已配置的提供方并输出汇总报告。

---

## 提交流程

1. **Fork** 仓库并创建功能分支：
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **进行修改**，如适用请在 `auto_tests/` 中添加测试。

3. **运行完整测试套件**：
   ```bash
   pytest auto_tests/
   ```

4. **提交**，提交信息请遵循现有风格（简短的祈使句主语，正文可选）：
   ```bash
   git commit -m "Add GPU temperature monitoring to system info"
   ```

5. **推送**并向 `main` 分支发起 Pull Request。

---

## 报告问题

在 GitHub 上发起 issue，并包含：
- 问题的清晰描述
- 复现步骤
- 预期行为与实际行为
- 环境信息（操作系统、Python 版本）
- `logs/` 中的相关日志

---

## 许可证

提交贡献即表示你同意你的贡献以 [GNU General Public License v3.0](../../LICENSE) 授权。
