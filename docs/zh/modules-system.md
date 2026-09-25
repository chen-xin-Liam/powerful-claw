# 🛡️ 系统能力与权限模块（src/system）

[← 中文文档索引](INDEX.md) ｜ [← 架构总览](architecture.md)

> `src/system/` 负责与操作系统交互，并为 AI 的每一步操作提供安全闸门：**权限判定 → 高危检测 → 二次确认 → 执行**。

---

## 安全闸门链路

```
AI/工具 请求操作
     │
     ▼
SystemController（查 PermissionLevel 是否允许该操作）
     │ 允许
     ▼
HighRiskDetector（命中黑名单关键词 / 敏感路径？）
     │ 命中
     ▼
ConfirmationManager（弹窗二次授权，子线程→主线程）
     │ 用户确认
     ▼
实际执行（键鼠 / 命令 / 文件 / 提权）
```

---

## `controller.py` — 系统控制器

关键类型：`PermissionLevel`、`OperationPermission`、`SystemController`。

系统控制的统一门面，封装：

- 鼠标移动/点击/拖拽、键盘输入、快捷键（底层 pyautogui/keyboard）
- 屏幕信息、窗口枚举、剪贴板等
- 每个操作前对照当前 `PermissionLevel` 校验

### 四级权限模型

| 级别 | 能力 |
|------|------|
| `NONE` | 无屏幕访问、无输入模拟（**默认**） |
| `VIEW` | 仅屏幕捕获，只读 |
| `LIMITED` | 截图 + 受限键鼠（排除系统关键区域，如任务栏、UAC 弹窗区域） |
| `FULL` | 完整屏幕访问 + 无限制键鼠 |

默认从最低权限起步，必须由用户显式提升。

---

## `high_risk_detector.py` — `HighRiskDetector`

**平台感知**的高危操作检测器：

- 根据当前操作系统（Windows / Linux）加载对应的黑名单关键词
- 敏感路径规则（系统目录、启动项、注册表关键位置等）
- 对命令文本、文件路径、操作类型做模式匹配
- 命中即转入二次确认流程

---

## `confirmation.py` — `ConfirmationManager`

线程安全的「二次授权确认」管理器，支持两种模式：

- **GUI 模式**：子线程（服务线程）发起确认请求 → 通过队列传递到主线程 → 弹出确认对话框 → 结果回传阻塞的调用方
- **无 GUI 模式**（`--noui`）：回退为终端确认或按配置策略自动拒绝/允许

这保证了网络服务线程永远不会直接操作界面，避免跨线程 Tkinter 错误。

---

## `privilege_manager.py` — `PrivilegeManager`

提权管理器：让 AI 可以请求以**管理员 / root** 权限运行单条命令。提权操作属于最高风险类别，必然经过高危检测与显式确认，并在日志中留痕。

---

## `vision.py` — `VisionCapture`

屏幕视觉捕获门面：

- 屏幕截图（适配高 DPI 多显示器）
- 与 `src/utils/yolo_detector.py`（YOLOv8 目标检测）协作，把「画面」变成「界面元素坐标」
- 供 `VIEW/LIMITED/FULL` 权限下的 AI 视觉理解使用

截图只在用户触发 AI 请求时发送给已配置的提供方（见[安全策略](../../SECURITY.md)）。

---

## 与其他模块的协作

| 协作方 | 方式 |
|--------|------|
| `services/ai_agent.py` | `CommandTool` 等通过 SystemController 落地操作 |
| `services/websocket_server.py` | 浏览器端远程指令同样经过完整安全闸门 |
| `services/ai_service.py` | 初始化时注入确认管理器与控制器 |
| `utils/yolo_detector.py` | VisionCapture 提供画面，YOLO 提供目标识别 |
| `utils/error_codes.py` | 权限不足/确认超时/高危拒绝均返回统一错误码 |

---

## 安全使用建议

1. 日常使用保持 `VIEW` 或 `LIMITED`
2. 不要为方便长期开启 `FULL`
3. 提权命令务必逐条确认，避免批准批处理脚本
4. 在虚拟机中首次试用，鼠标移到屏幕左上角可触发安全停止（默认 `LIMITED` 起步）
