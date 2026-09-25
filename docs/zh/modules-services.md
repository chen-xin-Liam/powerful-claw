# 🧩 服务层模块（src/services）

[← 中文文档索引](INDEX.md) ｜ [← 架构总览](architecture.md)

> `src/services/` 包含 23 个模块，是应用的业务核心。每个网络服务运行在独立守护线程中。

---

## AI 与 Agent

### `ai_service.py` — `AIService`
统一的大模型对话入口。根据当前提供方初始化对应客户端：

- OpenAI 兼容接口 / NVIDIA API（`openai` SDK）
- Ollama 本地服务
- GitHub Copilot SDK（委托 `copilot_service.py`）

初始化时注入系统控制器、高危确认管理器与工具注册表，使模型回复可以触发实际操作。提供方配置见 `src/config/ai_providers.py`。

### `ai_agent.py` — `AIAgent` / `BaseTool` / `ToolInfo`
让 AI「知道自己有哪些工具并智能调用」的代理层：

- `ToolInfo` / `ToolParameter`：工具的名称、描述、JSON Schema 参数声明
- `BaseTool`：所有工具的基类（`run()` 执行、参数校验）
- 内置工具：`SystemInfoTool`、`FileReadTool`、`FileWriteTool`、`CommandTool`
- 工具描述会被组装进模型的 tools/function-calling 请求

### `copilot_service.py` — `CopilotService`
对 `github-copilot-sdk` 异步 API 的封装，作为一种特殊 AI 提供方接入。

### `local_model_service.py` — `LocalModelService` / `LocalModel`
本地推理模型管理（无需联网的端侧模型），支持列出、加载、卸载与调用。

### `api_connectivity.py`
API 连通性测试：验证 Key 有效性、网络可达性、Ollama 模型是否存在。

```bash
python -m src.services.api_connectivity
```

详见 README 的相关章节；设置窗口中有「🌐 测试连接」按钮。

---

## 工具系统

### `tool_registry.py` — `ToolRegistry`
**单例**工具注册表，AI 可调用工具的唯一登记处。提供 `@tool` 装饰器注册自定义工具，内置工具包括系统信息、文件读写、命令执行、数学计算、Python 库调用等。

### `tool_service.py` — `ToolService`
工具执行服务层：查找工具、参数校验、执行并统一返回结果/错误。

### `command_executor.py` — `CommandExecutor`
跨平台 shell 命令执行器（带超时、输出捕获），受四级权限与高危检测约束。

### `python_library_tool.py` — `PythonLibraryTool`
让 AI 安全地调用环境中已安装的 Python 库（分类白名单见 [AI 库使用指南](ai_library_usage.md)）。

### `math_calculator_tool.py` — `MathCalculatorTool`
数学计算工具，底层走 [核心表达式引擎](modules-core.md)，自动选择 native/cppyy/python 后端。

---

## 网络服务

### `websocket_server.py` — `WebSocketServer` / `RCONBroadcastServer`
- 默认端口 **15000**：浏览器控制端的主指令通道
- `RCONBroadcastServer`（15001）：向多个连接客户端广播状态
- 线程内运行独立 asyncio 事件循环，基于 `websockets` 库
- 初始化系统控制器、视觉捕获，并托管 `src/web` 控制台页面

### `api_server.py` — `APIServer`
- HTTP 端口 **15002**，WebSocket 端口 **15003**
- 提供设置读写、AI 对话 REST 接口、插件热加载
- 托管 `src/web_api` 设置页面；处理器为 `HTTPServerHandler`

### `screen_monitor.py` — `ScreenMonitor`
桌面实时监控服务（默认 **15004**）：高质量屏幕采集、质量/FPS/码率可配（`MonitorConfig`），托管 `src/web_monitor` 页面。推流编解码核心见 [推流模块](modules-utils-streaming.md)。

### `video_editor.py` — `VideoEditor`
Web 视频编辑器服务：

- HTTP **15010**（多轨时间轴编辑器页面）
- WebSocket **15012**（实时编辑指令）
- 支持字幕、调色、多格式导出（1080P/2K/4K）
- 目前为基础实现，功能仍在完善

---

## 监控与数据

### `system_monitor.py` — `SystemMonitor` / `SystemInfo` / `ProcessInfo`
CPU、内存、GPU、进程等硬件负载采集，供 UI 展示与集群调度使用。

### `activity_monitor.py` — `ActivityMonitor` / `MonitorEvent` / `UserAction`
用户操作活动监测，生成结构化事件用于审计与自动化触发。

### `database_service.py` — `DatabaseService` / `ConversationRecord`
SQLite 持久化（数据库位于 `userspick/`），存储对话记录与应用数据。

### `celery_service.py` — `CeleryService` / `LocalTaskQueue`
任务队列抽象：有 Redis 时走 Celery（默认 `redis://localhost:6379/0`），无 Redis 时回退到本地队列 `LocalTaskQueue`。

---

## 扩展系统

### MCP（Model Context Protocol）

| 文件 | 关键类/函数 | 作用 |
|------|------------|------|
| `mcp_manager.py` | `MCPServerManager`、`MCPServerConfig`、`MCPServer` | 以 stdio 子进程方式管理 MCP 服务器：注册、启停、重连、JSON-RPC 收发 |
| `mcp_importer.py` | `import_mcp_config()`、`add_from_template()` | 导入标准 `.mcp.json`（Claude Desktop / VS Code 格式）与 6 个预置模板 |
| `extension_manager.py` | `ExtensionManager`（单例） | 统一管理 MCP 服务器 + 插件，配置持久化到 `src/config/extensions.json` |

命令行：

```bash
python -m src.services.mcp_importer --templates
python -m src.services.mcp_importer path/to/mcp.json
```

> 仅支持 stdio 传输；sse/http 远程类型会被拒绝。MCP 子进程继承应用环境变量（含 API Key），只从可信来源导入。

### 插件系统

| 文件 | 关键类 | 作用 |
|------|--------|------|
| `plugin_manager.py` | `PluginManager`、`BasePlugin`、`PluginInterface`、`PluginInfo` | 插件生命周期（加载/启用/禁用/热重载）与状态管理（`PluginState`） |
| `../plugins/sample_plugin.py` | `Plugin` | 官方示例插件，二次开发的模板 |

插件与 MCP 都由 `ExtensionManager` 统一登记并在启动时自动加载。

---

## 服务间关系图

```
浏览器 ──WS 15000──► WebSocketServer ──► SystemController（权限/确认/高危检测）
   │                    │ AIAgent ──► ToolRegistry ──► 各内置工具
   ├─HTTP 15002──────► APIServer ──► AIService ──► OpenAI/Ollama/Copilot/本地模型
   ├─HTTP 15004──────► ScreenMonitor ──► VisionCapture / RemoteDesktopStreamer
   └─HTTP 15010──────► VideoEditor

AIService / ToolRegistry ──► ExtensionManager ──► MCPServerManager（stdio 子进程）
                                          └────► PluginManager（热加载插件）
```
