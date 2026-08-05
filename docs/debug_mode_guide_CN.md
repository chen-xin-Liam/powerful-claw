# Debug 模式使用指南

## 📋 概述

Debug 模式提供了完整的 AI 对话日志输出功能，可以在终端中看到所有原始回答和输出结果。

## 🎯 功能特性

### 1. 用户消息显示
在 debug 模式下，所有用户发送的消息都会在终端中显示：
```
================================================================================
[DEBUG] 👤 用户消息:
帮我计算 1+1 等于多少
================================================================================
```

### 2. AI 推理过程显示
如果 AI 模型支持推理功能，会实时显示推理内容：
```
[DEBUG] 🧠 AI 推理：用户想要一个简单的数学计算...
```

### 3. AI 实时回答显示
AI 的回答会实时逐字显示在终端中：
```
[DEBUG] 🤖 AI: 1+1 等于 2
[DEBUG] 🤖 AI: 。
```

### 4. 对话循环信息
显示当前对话的轮次和循环状态：
```
[DEBUG] 🔄 开始对话循环，最大循环次数：5

[DEBUG] 📍 第 1 轮对话
```

### 5. 命令解析和执行
显示 AI 生成命令的解析和执行过程：
```
[DEBUG] 🔍 解析并执行命令...

[DEBUG] 📋 命令执行结果:
✓ 执行成功：execute_command
  结果：{"output": "2"}

执行了 1 个命令，成功 1 个，失败 0 个
```

### 6. 循环状态跟踪
显示对话循环的进行状态和结束原因：
```
[DEBUG] ✅ 对话循环结束
```
或
```
[DEBUG] ⚠️ 已达到最大循环次数 5，停止
```

## 🔧 启用方法

### 方法 1: 在 .env 文件中配置

编辑 `.env` 文件，添加或修改以下配置：
```ini
# 启用 Debug 模式
DEBUG_MODE=true
```

### 方法 2: 在命令行参数中指定

运行程序时添加 `--debug` 参数：
```bash
python src/main.py --debug
```

### 方法 3: 在 PowerShell 脚本中配置

编辑 `start_app.ps1` 文件，在运行参数中添加：
```powershell
$env:DEBUG_MODE = "true"
```

## 📊 输出示例

### 完整对话流程

```
[DEBUG] 🔄 开始对话循环，最大循环次数：5

[DEBUG] 📍 第 1 轮对话

================================================================================
[DEBUG] 👤 用户消息:
打开浏览器并访问百度
================================================================================

[DEBUG] 🧠 AI 推理：用户想要打开浏览器并访问百度，我需要先检查系统权限...
[DEBUG] 🤖 AI: 好的，我来帮你打开浏览器并访问百度。
[DEBUG] 🤖 AI: 首先让我检查一下系统权限。
[DEBUG] 🤖 AI: <control>{"type": "get_system_info"}</control>

[DEBUG] 🔍 解析并执行命令...

[DEBUG] 📋 命令执行结果:
✓ 执行成功：get_system_info
  结果：{"screen_width": 1920, "screen_height": 1080, "permission": "full"}

执行了 1 个命令，成功 1 个，失败 0 个

[DEBUG] 📍 第 2 轮对话

[DEBUG] 🧠 AI 推理：权限检查通过，现在执行打开浏览器的操作...
[DEBUG] 🤖 AI: 现在我来打开浏览器。
[DEBUG] 🤖 AI: <control>{"type": "execute_command", "command": "start msedge https://www.baidu.com"}</control>

[DEBUG] 🔍 解析并执行命令...

[DEBUG] 📋 命令执行结果:
✓ 执行成功：execute_command
  结果：{"output": ""}

执行了 1 个命令，成功 1 个，失败 0 个

[DEBUG] ✅ 对话循环结束
```

## 🎨 颜色说明

Debug 输出使用了不同的颜色来区分不同类型的信息：

| 颜色 | 说明 | 内容 |
|------|------|------|
| 🟢 绿色 | 用户消息 | 用户发送的原始消息 |
| ⚪ 灰色 | AI 推理 | AI 的思考过程（如果模型支持） |
| 🔵 蓝色 | AI 回答 | AI 的实时回答内容 |
| 🟡 黄色 | 系统信息 | 循环状态、命令执行结果等 |

## ⚙️ 配置选项

### DEBUG_MODE
- **类型**: Boolean
- **默认值**: false
- **说明**: 是否启用 debug 模式
- **可选值**: true, false

### 相关配置
- **NO_COLOR**: 设置为任何值将禁用颜色输出
- **LOG_LEVEL**: 日志级别（如果同时启用了日志功能）

## 📝 注意事项

1. **性能影响**: Debug 模式会增加终端输出，可能略微影响性能
2. **日志文件**: Debug 模式下建议同时启用日志保存功能（-nolog 参数会禁用）
3. **生产环境**: 生产环境中建议关闭 debug 模式以减少日志输出
4. **颜色支持**: 如果终端不支持颜色，输出会自动禁用颜色格式

## 🔍 故障排除

### 问题：看不到颜色输出
**解决方案**: 
- 检查终端是否支持 ANSI 颜色
- 确保没有设置 `NO_COLOR` 环境变量

### 问题：看不到 debug 输出
**解决方案**:
- 确认 `DEBUG_MODE=true` 已正确设置
- 检查 `.env` 文件是否被正确加载
- 确认程序启动时使用了 `--debug` 参数

### 问题：输出太多难以查看
**解决方案**:
- 使用终端的滚动功能查看历史输出
- 将输出重定向到文件：`python src/main.py --debug > debug.log 2>&1`
- 使用日志文件保存功能（debug 模式默认开启）

## 💡 最佳实践

1. **开发调试**: 开发时启用 debug 模式，便于查看 AI 行为
2. **问题诊断**: 遇到问题时启用 debug 模式，分析 AI 决策过程
3. **性能测试**: 性能测试时关闭 debug 模式，减少输出影响
4. **日志分析**: 结合日志文件分析，debug 输出 + 日志文件双重记录

---

## 🛡️ 统一错误处理与错误码

本项目采用统一的异常体系与错误码分段，便于在 Debug 模式下按错误码快速定位问题。

### 1. 异常体系概览

所有自定义异常继承自 `AppError`（位于 `src/utils/errors.py`），统一携带 5 个字段：

| 字段 | 类型 | 用途 |
|------|------|------|
| `code` | `ErrorCode` | 错误码枚举，用于程序判断与日志检索 |
| `message` | `str` | 面向用户的简明消息（中文） |
| `details` | `dict` | 结构化上下文，如 `{"host":..., "port":...}` |
| `cause` | `BaseException` | 原始异常（保留异常链） |
| `module` | `str` | 抛出异常的模块名（自动从调用栈推断） |

分领域子类：`ConfigError`(1xxx)、`ValidationError`(5xxx)、`ServiceError`(2xxx)、`NetworkError`(3xxx)、`IOError_`(4xxx)、`ExternalDependencyError`(6xxx)、`SubprocessError_`(7xxx)。

输出格式：`[E{code:04d}][{module}] {message}`，例如 `[E2001][src.services.websocket_server] WebSocket 服务启动失败`。

### 2. 错误码分段表

错误码定义在 `src/utils/error_codes.py`，按千位分段：

| 段位 | 类别 | 代表错误码 |
|------|------|-----------|
| `1xxx` | 配置 | `E_CONFIG_LOAD_FAILED=1001` / `E_CONFIG_FILE_NOT_FOUND=1003` |
| `2xxx` | 服务 | `E_SERVICE_START_FAILED=2001` / `E_SERVICE_DEPENDENCY_MISSING=2004` |
| `3xxx` | 网络 | `E_NET_SOCKET_BIND=3001` / `E_CRYPTO_DECRYPT=3401` |
| `4xxx` | IO | `E_IO_FILE_NOT_FOUND=4001` / `E_IO_PERMISSION_DENIED=4002` |
| `5xxx` | 校验 | `E_VAL_INVALID_ARG=5001` / `E_VAL_MISSING_REQUIRED=5002` |
| `6xxx` | 外部依赖 | `E_EXT_PSUTIL=6001` / `E_EXT_NVIDIA_SMI=6002` / `E_EXT_OPENCV=6003` |
| `7xxx` | 子进程 | `E_SUBPROCESS_TIMEOUT=7001` / `E_SUBPROCESS_NOT_FOUND=7002` |
| `9xxx` | 致命 | `E_FATAL_UNEXPECTED=9000` |

按段位范围过滤日志：
```powershell
# 查看所有网络类错误（3xxx）
Select-String -Path "logs\*.log" -Pattern "E3\d{3}"
```

### 3. 在 Debug 模式下定位错误

```bash
python src/main.py --debug
```

日志文件位于 `logs/src.main_YYYYMMDD.log`。按错误码检索：
```powershell
Select-String -Path "logs\*.log" -Pattern "E2001"
```

### 4. 退出码语义

| 退出码 | 含义 | 触发条件 |
|--------|------|----------|
| `0` | 全部服务启动成功 | 无失败服务 |
| `1` | 部分服务启动失败 | 1 个或多个服务失败 |
| `2` | 致命错误 | 配置加载失败 / 所有服务失败 |

### 5. 常见错误码故障排查

| 错误码 | 含义 | 排查建议 |
|--------|------|----------|
| `E1001` | 配置加载失败 | 检查 `.env` 文件格式，参考 `.env.example` |
| `E2004` | 必备依赖缺失 | 运行 `pip install -r requirements.txt` |
| `E3001` | 端口被占用 | 使用 `--port` / `--api-port` 指定其他端口 |
| `E4002` | 权限不足 | 以管理员身份运行 |
| `E6002` | nvidia-smi 不可用 | 未检测到 NVIDIA 驱动（GPU 功能不可用，可忽略） |
| `E7002` | 命令不存在 | 确认目标命令已加入 PATH（如 ffmpeg、tesseract） |

---

## 🎨 UI 视觉特效使用

项目提供 Glassmorphism（毛玻璃）视觉特效，包含纯 Python 与 C++ 双实现。

### 双实现对比

| 实现方式 | 文件 | 说明 |
|----------|------|------|
| 纯 Python | `src/ui/effects/py_effects.py` | 使用 Pillow 库，无需编译，跨平台 |
| C/C++ | `src/ui/effects/gl_effects.cpp` | 使用 OpenGL 加速，需要编译 DLL |

### Python 调用示例

```python
from src.ui.effects import GLEffects, GLColor, GlassEffectParams

# 初始化特效引擎
effects = GLEffects()
effects.init(width=800, height=600)

# 设置透明度 (0.0-1.0)
effects.set_transparency(0.8)

# 启用毛玻璃效果
effects.enable_glass_effect(True)

# 配置毛玻璃参数
glass_params = GlassEffectParams()
glass_params.blur_radius = 15.0
glass_params.opacity = 0.7
glass_params.tint_color = GLColor(0.15, 0.15, 0.2, 0.7)
effects.set_glass_params(glass_params)

# 启用边框光晕效果
effects.enable_glow_effect(True)

# 执行渲染
effects.render()

# 关闭特效引擎
effects.shutdown()
```

### 编译 C/C++ 加速版本（可选）

```bash
# 进入特效模块目录
cd src/ui/effects

# 运行编译脚本
python build_effects.py

# 生成的 DLL 文件位于 bin/ 目录
```

### 提供的特效能力

- 🔮 **毛玻璃效果**：背景模糊、半透明叠加层、边框锐化
- 🎭 **透明度控制**：Windows 风格的 0-100% 透明度调节
- ✨ **边框光晕**：蓝色发光边框与阴影的自然过渡
- 🎬 **窗口动画**：平滑的最大化/最小化过渡动画
- 🎯 **跨平台**：兼容 Windows 和 Linux
