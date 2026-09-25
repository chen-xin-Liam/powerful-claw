# 🏛️ 系统架构总览

[← 中文文档索引](INDEX.md)

> 本文介绍 powerful-claw 的整体分层、启动流程、端口规划与线程模型，是阅读源码前的入门地图。

---

## 1. 分层结构

```
┌─────────────────────────────────────────────────────────┐
│  用户界面层  src/ui                                       │
│  CustomTkinter 主窗口 · PySide6 设置对话框 · 闪屏/主题     │
├─────────────────────────────────────────────────────────┤
│  Web 前端层  src/web · src/web_api · src/web_monitor      │
│  浏览器控制台 · 设置页 · 实时桌面监控页（静态 HTML/JS）     │
├─────────────────────────────────────────────────────────┤
│  服务层  src/services                                     │
│  AI 服务/Agent · WebSocket · HTTP API · 屏幕监控           │
│  视频编辑器 · 工具注册表 · MCP/插件 · 本地模型 · 任务队列    │
├─────────────────────────────────────────────────────────┤
│  系统能力层  src/system                                   │
│  系统控制器 · 四级权限 · 高危检测 · 二次确认 · 视觉捕获      │
├─────────────────────────────────────────────────────────┤
│  核心计算层  src/core                                     │
│  表达式解析器 · 44 节点引擎（native C++ / cppyy / Python） │
├─────────────────────────────────────────────────────────┤
│  基础设施层  src/config · src/utils                       │
│  配置/主题/AI 提供方 · 日志 · 错误码 · YOLO · 推流 · 性能   │
└─────────────────────────────────────────────────────────┘
```

每层只依赖下层或同层，UI 与 Web 是两个并列的入口，共享同一套 services / system 能力。

---

## 2. 目录与职责

| 目录 | 职责 | 详解 |
|------|------|------|
| `src/ui/` | 桌面 GUI | [界面与主题模块](modules-ui-config.md) |
| `src/services/` | 后台服务（23 个模块） | [服务层模块](modules-services.md) |
| `src/system/` | 操作系统交互与安全 | [系统能力与权限模块](modules-system.md) |
| `src/core/` | 节点化数学引擎 | [表达式引擎与原生后端](modules-core.md) |
| `src/config/` | 配置、主题、AI 提供方 | [界面与主题模块](modules-ui-config.md) |
| `src/utils/` | 工具库（日志/错误码/YOLO/推流） | [工具库与推流模块](modules-utils-streaming.md) |
| `src/plugins/` | 插件 SDK 与示例 | [服务层模块](modules-services.md#插件系统) |
| `src/web*` | Web 前端静态页 | [工具库与推流模块](modules-utils-streaming.md#web-前端) |
| `auto_tests/` | 自动化测试 | [测试指南](testing.md) |
| `benchmarks/` | 性能基准 | [表达式引擎与原生后端](modules-core.md#性能基准) |

---

## 3. 启动流程

入口为 [src/main.py](../../src/main.py)（或根目录 `start.py`）。核心函数 `start_services(args)`：

1. 读取 `config` 配置与命令行参数（端口、模式开关）
2. 显示闪屏（GUI 模式）
3. **多线程并行启动**各后台服务（守护线程）：
   - `WebSocketServer`（15000）+ `RCONBroadcastServer`（15001）
   - `APIServer`（15002，含 WebSocket 15003）
   - `ScreenMonitor`（15004）
   - `VideoEditor`（HTTP 15010 + WS 15012）
   - `AIService` / `LocalModelService`（按配置）
4. 初始化 `CustomTkinterApp` 主窗口（GUI 模式）；`--noui` 为纯终端模式
5. 返回退出码：`0` 全部成功 / `1` 部分服务失败（非致命）/ `2` 致命错误

### 启动开关

| 参数 / 配置 | 作用 |
|-------------|------|
| `--noui` | 纯终端模式，不启动 GUI |
| `--noweb` | 不启动 WebSocket 与 API 服务 |
| `--noeditor` | 不启动视频编辑器 |
| `--nomonitor` | 不启动桌面监控 |
| `--debug` | 启用调试模式（见[调试指南](debug_mode_guide.md)） |
| `--host / --port / --api-port / --monitor-port / --editor-port` | 覆盖默认绑定地址与端口 |

---

## 4. 端口规划

| 端口 | 服务 | 说明 |
|------|------|------|
| 15000 | WebSocket 主服务 | 浏览器控制端指令通道 |
| 15001 | RCON 广播 | 服务端向多个客户端广播状态 |
| 15002 | HTTP API | 设置、AI 对话接口、静态设置页 |
| 15003 | API WebSocket | API 服务的实时通道 |
| 15004 | 桌面监控 | 屏幕采集流与监控页 |
| 15010 | 视频编辑器 HTTP | 多轨编辑器页面 |
| 15012 | 视频编辑器 WS | 编辑指令实时通道 |
| 15300–15304 | 局域网集群 | 节点发现/调度（见[集群文档](cluster_computing.md)） |
| 6379 | Redis（可选） | Celery 任务队列 broker |

> 默认绑定 `0.0.0.0`（局域网可访问）。无需远程访问时请用防火墙限制，详见[安全策略](../../SECURITY.md)。

---

## 5. 线程与并发模型

- 每个网络服务运行在独立的 **daemon 线程**中，互不阻塞 GUI
- WebSocket/视频编辑的实时通道在线程内再创建独立的 **asyncio 事件循环**
- 单例管理器（`ExtensionManager`、`NodeEngine`、`ToolRegistry` 等）通过类级 `_instance` + 锁实现
- 高危操作通过队列在**子线程 → 主线程**之间传递确认请求（见 [ConfirmationManager](modules-system.md#二次确认)）

---

## 6. 统一错误体系

- 所有自定义异常继承 `AppError`（[src/utils/errors.py](../../src/utils/errors.py)），携带统一字段：`code`、`message`、`suggestion`、`context`
- 错误码（[error_codes.py](../../src/utils/error_codes.py)）按千位分段：

| 段 | 类别 |
|----|------|
| 1xxx | 配置 |
| 2xxx | 服务（业务层） |
| 3xxx | 网络 |
| 4xxx | IO |
| 5xxx | 校验 |

排查问题时可按段位快速定位层次，配合 `logs/` 下的分级日志与 `--debug` 全链路追踪。

---

## 7. 扩展点

| 想做什么 | 入口 |
|----------|------|
| 新增 AI 可调用工具 | `ToolRegistry` 装饰器（见[服务层](modules-services.md#工具系统)） |
| 新增 AI 提供方 | `AIProviderManager`（见[配置指南](configuration.md)） |
| 接入 MCP 服务器 | `mcp_importer`（根 [README](../../README.md) 的 MCP 章节） |
| 开发插件 | `BasePlugin` / `PluginInterface`（见[服务层](modules-services.md#插件系统)） |
| 新增表达式节点 | `node_engine.py` 节点类 + C++ 镜像（见[核心计算](modules-core.md)） |
| 自定义主题 | `ThemeManager`（见[主题文档](../../config/themes/README.md)） |
