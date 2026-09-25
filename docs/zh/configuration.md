# 配置指南

本文档涵盖 AI Computer Control 的全部配置项：环境变量、服务端口、运行参数、AI 模型参数与权限模式。

配置优先级：**命令行参数 > `.env` 文件 > 默认值**。

## 环境变量

项目通过 `.env` 文件集中管理配置。复制 `.env.example` 为 `.env` 并按需修改：

| 变量名 | 描述 | 默认值 | 是否必需 |
|--------|------|--------|----------|
| `AI_PROVIDER` | AI 服务提供者（nvidia/openai/ollama/自定义） | nvidia | 是 |
| `AI_API_KEY` | AI 服务的 API 密钥 | - | 是 |
| `AI_BASE_URL` | AI 服务基础 URL | https://integrate.api.nvidia.com/v1 | 否 |
| `AI_MODEL` | 使用的 AI 模型 | zephyr-7b-beta | 否 |
| `AI_MAX_TOKENS` | 每次响应的最大 token 数 | 4096 | 否 |
| `AI_TEMPERATURE` | 生成随机性（0=确定, 2=随机） | 0.7 | 否 |
| `HOST` | 服务监听地址 | 0.0.0.0 | 否 |
| `PORT` | WebSocket 端口 | 15000 | 否 |
| `API_PORT` | API 端口 | 15002 | 否 |
| `THEME` | 界面主题（dark/light） | dark | 否 |
| `LANGUAGE` | 界面语言 | zh_CN | 否 |

## `.env` 完整配置示例

```env
# ============ 运行模式 ============
DEBUG=true
NOUI=false
NOWEB=false
NOEDITOR=false
NOMONITOR=false

# ============ 服务器设置 ============
HOST=0.0.0.0
PORT=15000
API_PORT=15002
RCON_PORT=15001
SCREEN_MONITOR_PORT=15004
VIDEO_EDITOR_PORT=15010

# ============ 桌面监控设置 ============
SCREEN_MONITOR_QUALITY=80
SCREEN_MONITOR_FPS=15
SCREEN_MONITOR_BITRATE=2000000

# ============ 视频传输设置 (端口15009) ============
# 视频传输协议优先级：rtmp, srt, srtp
VIDEO_PROTOCOL_PRIORITY="rtmp,srt,srtp"
RTMP_ENABLED=false
RTMP_URL="rtmp://localhost/live/stream"
SRT_ENABLED=false
SRT_PORT=15009
SRT_LATENCY=120
SRTP_ENABLED=false
SRTP_PORT=15009
SRTP_KEY=""

# ============ 音频传输设置 (端口15008) ============
# 音频传输协议优先级：webrtc, srtp, smpte2110
AUDIO_PROTOCOL_PRIORITY="webrtc,srtp,smpte2110"
WEBRTC_ENABLED=true
WEBRTC_PORT=15008
AUDIO_SRTP_ENABLED=false
AUDIO_SRTP_PORT=15008
SMPTE2110_ENABLED=false
SMPTE2110_PORT=15008
SMPTE2110_MULTICAST="239.255.0.1"

# ============ 远程桌面式视频流 ============
REMOTE_DESKTOP_STREAM=true
RD_DIFF_THRESHOLD=10
RD_BLOCK_SIZE=64
RD_KEYFRAME_INTERVAL=60
RD_MOTION_DETECTION=true
RD_ADAPTIVE_QUALITY=true
RD_MIN_QUALITY=30
RD_MAX_QUALITY=95

# ============ AI 设置 ============
AI_PROVIDER=nvidia
AI_MODEL=zephyr-7b-beta
AI_API_KEY=your_api_key_here
AI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.7

# ============ 界面设置 ============
THEME=dark
THEME_COLOR=blue
LANGUAGE=zh_CN

# ============ 代理设置 ============
PROXY_ENABLED=false
PROXY_URL=http://127.0.0.1:7890

# ============ SSL 设置 ============
CERT_ENABLED=false
CERT_PATH=./cert.pem
KEY_PATH=./key.pem

# ============ 集群设置 ============
CLUSTER_ENABLED=true
CLUSTER_DISCOVERY_PORT=15300
CLUSTER_MAIN_PORT=15301
CLUSTER_TASK_PORT=15302
CLUSTER_DATA_PORT=15303
CLUSTER_MONITOR_PORT=15304
CLUSTER_HEARTBEAT_INTERVAL=5
CLUSTER_HEARTBEAT_TIMEOUT=15
CLUSTER_MAX_TASKS_PER_NODE=10
```

## 服务端口说明

| 端口 | 服务 | 访问地址 | 说明 |
|------|------|----------|------|
| 15000 | 网页控制端 | http://localhost:15000 | 跨平台 Web 控制界面 |
| 15001 | RCON 广播 | ws://localhost:15001/rcon | RCON 控制台信息广播 |
| 15002 | API 服务 | http://localhost:15002 | AI 模型配置和对话接口 |
| 15003 | API WebSocket | ws://localhost:15003/api | AI 对话 WebSocket 接口 |
| 15004 | 桌面监控 | http://localhost:15004 | 实时桌面监控页面 |
| 15006 | 监控 WebSocket | ws://localhost:15006 | 桌面监控 WebSocket |
| 15007 | UDP 视频流 | udp://localhost:15007 | 低延迟视频传输 |
| 15010 | 视频剪辑 | http://localhost:15010 | Web 视频剪辑编辑器 |
| 15012 | 剪辑 WebSocket | ws://localhost:15012 | 视频剪辑 WebSocket |
| 15300 | 集群发现 | udp://localhost:15300 | UDP 广播节点发现 |
| 15301 | 集群主通信 | tcp://localhost:15301 | 节点间 TCP 通信 |
| 15302 | 集群任务 | tcp://localhost:15302 | 任务分发端口 |
| 15303 | 集群数据 | tcp://localhost:15303 | 数据传输端口 |
| 15304 | 集群监控 | udp://localhost:15304 | 状态监控端口 |

## 运行参数

应用支持以下命令行参数（优先级：命令行 > `.env` > 默认值）：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--debug`, `-d` | 启用调试模式 | false |
| `--noui` | 无 GUI 模式（终端模式） | false |
| `--noweb` | 不启动 Web 服务 | false |
| `--noeditor` | 不启动视频剪辑服务 | false |
| `--nomonitor` | 不启动桌面监控服务 | false |
| `--nosystray` | 不显示系统托盘 | false |
| `--autorestart` | 服务崩溃后自动重启 | false |
| `--host` | 监听地址 | 0.0.0.0 |
| `--port`, `-p` | WebSocket 端口 | 15000 |
| `--api-port` | API 端口 | 15002 |
| `--rcon-port` | RCON 端口 | 15001 |
| `--monitor-port` | 桌面监控端口 | 15004 |
| `--editor-port` | 视频编辑端口 | 15010 |
| `--theme` | 界面主题 | dark |
| `--theme-color` | 主题颜色 | blue |
| `--log-level` | 日志级别 | INFO |
| `--nocluster` | 不启动集群服务 | false |
| `--help` | 显示帮助信息 | - |

启动示例：

```bash
# 调试模式
python src/main.py --debug

# 终端模式（无 GUI）
python src/main.py --noui

# 指定端口
python src/main.py --port 15000 --api-port 15002
```

## AI 模型参数

- **temperature**: 控制随机性（0 = 确定性，2 = 非常随机）
- **top_p**: 核采样参数（0.1 = 聚焦，1.0 = 多样化）
- **max_tokens**: 响应的最大长度
- **MAX_CALLS_PER_MINUTE**: 限制每分钟 API 调用频率，防止超额

### 性能优化

- 调整 `MAX_CALLS_PER_MINUTE` 控制 API 调用频率
- 设置合适的 `AI_TEMPERATURE` 和 `AI_MAX_TOKENS` 参数
- 使用本地 Ollama 减少网络延迟

### 自定义 AI 提供者

1. 在 `src/config/providers_config.json` 中添加新提供者配置
2. 或在运行时界面中动态添加

## 权限级别

| 级别 | 描述 | 允许的操作 |
|------|------|------------|
| None | 仅查看模式 | 无 |
| View | 查看模式 | 无 |
| Limited | 基础控制 | 鼠标移动、点击、键盘输入 |
| Full | 完全控制 | 所有操作，包括热键、窗口控制 |

### 安全设置

- 使用 `Limited` 权限开始，逐步升级
- 鼠标移动到屏幕左上角可触发安全停止
- API 密钥不会在界面中明文显示

## 模式

- **Chat Mode**: 与 AI 的常规对话，无系统控制
- **Control Mode**: AI 可以生成并执行系统操作
