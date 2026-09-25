# 🛠️ 工具库、视觉与推流模块（src/utils · Web 前端）

[← 中文文档索引](INDEX.md) ｜ [← 架构总览](architecture.md)

> `src/utils/` 是跨层复用的工具库：日志、错误体系、YOLO 视觉、桌面推流、性能剖析等；Web 前端则是三套浏览器可访问的静态页面。

---

## 日志与错误

| 文件 | 关键类/函数 | 作用 |
|------|------------|------|
| `logger.py` | `setup_logger()`、`get_logger()`、`ColorFormatter` | 标准 logging 封装，控制台彩色输出 |
| `loguru_logger.py` | `LoguruLogger` | Loguru 风格的结构化分级日志 |
| `errors.py` | `AppError` 及子类 | 统一异常：`ConfigError`、`ValidationError`、`ServiceError`、`NetworkError`、`ExternalDependencyError` 等，带 `code/message/suggestion/context`；`get_suggestion()` 给出修复建议 |
| `error_codes.py` | `ErrorCode` | 错误码按千位分段：1xxx 配置 / 2xxx 服务 / 3xxx 网络 / 4xxx IO / 5xxx 校验 |
| `rich_terminal.py` | `RichTerminal` | Rich 富文本终端输出 |

---

## 视觉与图像

| 文件 | 关键类 | 作用 |
|------|--------|------|
| `yolo_detector.py` | `YOLODetector` | YOLOv8 屏幕目标检测，把截图转化为界面元素（按钮/输入框等）及坐标 |
| `image_processor.py` | `ImageProcessor` | 截图缩放、裁剪、格式转换等高 DPI 图像处理 |
| `vision.py`（位于 `src/system`） | `VisionCapture` | 屏幕捕获门面，见[系统能力模块](modules-system.md) |
| `video_analyzer.py` | `VideoAnalyzer` | 视频帧/内容分析辅助 |

---

## 桌面推流（remote_desktop_streamer.py）

类职责清晰的一条低带宽推流管线：

| 类 | 职责 |
|----|------|
| `RDConfig` | 帧率（1–30 FPS）、码率、质量等推流参数 |
| `ScreenCapturer` | 屏幕帧采集 |
| `FrameDiffer` | **帧差压缩**：只传输与上一帧不同的区域 |
| `BlockEncoder` | **分块编码**：把差异区域切块编码，降低带宽 |
| `MotionDetector` | 运动检测，静态画面时减少发送 |
| `AdaptiveQualityController` | 根据网络状况自适应调整画质 |
| `RemoteDesktopStreamer` | 总装上述组件，对外提供推流能力 |

支持 RTMP / SRT / WebRTC 协议（依赖 FFmpeg），由 `ScreenMonitor`（端口 15004）与桌面监控页面使用。

---

## 其他工具

| 文件 | 关键类 | 作用 |
|------|--------|------|
| `parser.py` | `ResponseParser` | 解析模型/服务的结构化回复 |
| `markdown_renderer.py` | `MarkdownRenderer` | 聊天消息的 Markdown 渲染（代码块、列表等） |
| `performance_profiler.py` | `PerformanceProfiler`、`get_execution_stats()` | 轻量性能计时与统计，配合基准测试 |
| `cattrs_converter.py` | `CattrsConverter` | 数据类与字典/JSON 的统一转换 |

性能优化方法学与 gprof/cProfile 的使用见 [测试指南](testing.md) 与[核心引擎文档](modules-core.md)。

---

## Web 前端

三个**纯静态** HTML/JS 页面目录，由各自的服务托管，无需独立前端构建：

| 目录 | 托管服务 | 端口 | 用途 |
|------|----------|------|------|
| `src/web/` | WebSocketServer | 15000 | 浏览器控制台：聊天、远程控制、状态查看 |
| `src/web_api/` | APIServer | 15002 | 设置页、API 调用入口 |
| `src/web_monitor/` | ScreenMonitor | 15004 | 实时桌面监控观看页 |

视频编辑器页面由 `VideoEditor`（15010）单独托管。所有 Web 服务默认绑定 `0.0.0.0`，仅建议在可信局域网内开放（见[安全策略](../../SECURITY.md)）。

---

## 模块依赖原则

- `utils/` 不依赖 `services/`、`ui/`，可被任意层引用
- 视觉链路：`ScreenCapturer → FrameDiffer/BlockEncoder → 推流协议`，各组件可单独替换
- 错误一律转换为 `AppError` 子类再向上抛，禁止在业务层裸抛 `Exception`
