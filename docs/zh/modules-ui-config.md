# 🎨 界面、配置与主题模块（src/ui · src/config）

[← 中文文档索引](INDEX.md) ｜ [← 架构总览](architecture.md)

> 桌面端采用「CustomTkinter 主窗口 + PySide6 设置对话框」的双 UI 方案；配置层负责设置持久化、主题热切换与多 AI 提供方管理。

---

## UI 模块（src/ui）

### `customtkinter_app.py` — `CustomTkinterApp` / `SettingsWindow`
应用主窗口与主控：

- 基于 CustomTkinter 的聊天界面、状态面板、托盘图标
- **启动性能优化**：openai/PIL/pyautogui 等重型依赖全部在函数内懒加载，冷启动控制在约 0.75 秒
- 主题热切换引擎：`sync_ctk_theme_baseline()`、`apply_theme_to_existing_widgets()`、`apply_ctk_theme_hot()`，保留被显式着色的控件
- 设置入口：优先打开 PySide6 设置窗口，失败时自动回退到内置 `SettingsWindow`

### `qt_settings.py` — `SettingsDialog` / `show_settings()`
PySide6（Qt）模态设置对话框，6 个标签页：

1. 通用　2. AI 模型　3. 网络　4. 安全　5. 界面　6. 高级

特性：

- `QDialog.exec()` 独立事件循环，与 Tkinter 主循环互不干扰
- 作为**独立窗口**打开（不把 tkinter 对象当作 Qt parent，避免类型冲突）
- 主题联动：从 `ThemeManager` 读取颜色动态生成 Qt 样式表
- 「🌐 测试连接」按钮实时调用 `api_connectivity` 验证 API
- 保存时回写 `settings` 并持久化到 `.env`

### `splash_screen.py` — `SplashScreen`
启动闪屏：在重型服务初始化**之前**显示，避免用户面对无响应窗口。

### `theme_settings_panel.py` — `ThemeSettingsPanel`
主题自定义面板：选择预设、调整配色并实时预览。

---

## 配置模块（src/config）

### `settings.py` — `Settings`
基于 pydantic-settings 的全局配置（`.env` 自动注入），关键字段：

| 字段 | 默认值 |
|------|--------|
| `host` | `0.0.0.0` |
| `websocket_port` / `rcon_port` / `api_port` | 15000 / 15001 / 15002 |
| `screen_monitor_port` / `video_editor_port` | 15004 / 15010 |
| `celery_broker_url` | `redis://localhost:6379/0` |
| `noweb` / `noeditor` / `nomonitor` / `debug` | 启动开关 |

完整字段与环境变量见 [配置指南](configuration.md)。

### `app_config.py` — `AppSettings` / `ConfigLoader`
应用级配置文件加载器（读写 ini/json 配置、提供默认值）。

### `ai_providers.py` — `AIProvider` / `AIProviderManager`
AI 提供方注册表，预置：

- **OpenAI**（兼容接口，也是大多数第三方网关的类型）
- **NVIDIA**（integrate.api.nvidia.com）
- **Ollama**（localhost:11434）
- **Local**（本地模型，免网络）
- **GitHubCopilot**（专用 SDK）

每个 `AIProvider` 含 `name / base_url / api_key / default_model`；`provider_manager` 单例负责列出与获取，连通性验证见 `services/api_connectivity.py`。

### `theme_manager.py` — `ThemeManager` / `ThemeConfig` / `ThemeColors`
主题管理器：

- 读取 ini 主题，`build_ctk_theme_dict()` 转换为 CustomTkinter JSON
- `export_ctk_theme_json()` 缓存到 `config/themes/.cache/`
- 修复了 `_clean_value()` 对十六进制颜色的解析问题（`#` 误切分）
- 预设与自定义主题写法见 [主题文档](../../config/themes/README.md)

---

## 运行时配置文件位置

| 路径 | 内容 |
|------|------|
| `.env` / `.env.example` | 环境变量与密钥（`.env` 已被 git 忽略） |
| `config/settings.ini` | 应用设置 |
| `config/themes/` | 主题文件与 `.cache/` 缓存 |
| `config/extensions.json` | MCP 服务器与插件扩展配置 |
| `userspick/` | SQLite 数据库与用户数据 |
| `conversations.json` | 本地对话历史（不入库） |

---

## UI 技术选型说明

| 场景 | 技术 | 原因 |
|------|------|------|
| 主窗口 | CustomTkinter | 轻量、与既有代码一致、打包体积小 |
| 设置对话框 | PySide6 | 原生控件更丰富（表单/标签页/按钮反馈），独立模态 |
| Web 控制台 | 静态 HTML/JS | 浏览器即可远程操作，无需桌面环境 |

PySide6 为可选依赖，缺失时设置入口自动回退 CustomTkinter，不影响主程序运行。
