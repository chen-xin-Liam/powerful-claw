# AI Computer Control 🤖

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)[![environment](https://img.shields.io/badge/environment-venv/3.13.3-green.svg)](https://www.python.org/)
[![License: GPLv3+NonCommercial](https://img.shields.io/badge/License-GPLv3%2B%20NC-red.svg)](LICENSE)[![bilibili](https://img.shields.io/badge/bilibili-%E6%95%B0%E7%A7%91%E6%99%BA%E6%98%9F-blue.svg)](https://space.bilibili.com/3493111196027162)

一个功能强大的 AI 电脑控制应用程序，集成了**AI 智能对话**、**桌面监控**、**视频剪辑**、**RCON 广播**等多种功能，实现自动化系统操作和智能控制。

## ✨ 功能特性

### 🤖 AI 智能控制
- 🚀 **多 AI 提供者支持**: 支持 NVIDIA、OpenAI、Ollama 及自定义 AI 服务
- 🔄 **自动轮回对话**: 支持多轮自动对话，可设置每分钟调用次数限制
- 🖱️ **系统控制**: 支持鼠标移动、点击、拖拽和键盘输入操作
- 📷 **视觉捕获**: 支持屏幕截图、摄像头捕获和 YOLO 对象检测
- 🔒 **权限管理**: 四级权限控制（None/View/Limited/Full）
- 💬 **思考过程可视化**: 实时显示 AI 推理过程和流式响应

### 📺 桌面监控（端口 15004-15009）
- 🎥 **实时屏幕捕获**: 支持 1-30 FPS 可调帧率
- 🔊 **系统音频捕获**: 捕获所有应用声音（支持循环回送设备）
- 📡 **多协议视频传输**: 端口15009支持 RTMP(主)、SRT、SRTP 协议自适应
- 📡 **多协议音频传输**: 端口15008支持 WebRTC(主)、SRTP、SMPTE 2110 协议自适应
- 🎨 **多画质预设**: 流畅、标准、高清、HDR、超清、蓝光
- 🖥️ **Web 实时监控**: 浏览器访问即可查看桌面画面
- 🖥️ **远程桌面式视频流**: 帧差压缩+分块编码，大幅降低带宽占用

### 🎬 视频剪辑（端口 15010）
- 📁 **素材管理**: 支持视频、音频、图片、GIF、字幕文件导入
- ⏱️ **多轨道时间轴**: 视频轨、音频轨、字幕轨、画中画轨
- ✂️ **基础剪辑**: 切割、合并、复制、粘贴、删除、波纹删除
- 🎨 **调色与特效**: 亮度、对比度、饱和度、滤镜、转场特效
- 🎵 **音频处理**: 多音轨混音、降噪、均衡器、语音转字幕
- 📝 **字幕编辑**: 手动/自动字幕添加、样式调整、SRT/ASS 导出
- 📤 **导出渲染**: 支持 1080P/2K/4K、24/30/60fps、MP4/MOV/GIF/WebM

### 🎮 RCON 广播（端口 15001）
- 📡 **实时控制台广播**: WebSocket 方式广播 RCON 控制台信息
- 🔔 **事件推送**: 实时推送游戏服务器事件和日志

### 🌐 API 服务（端口 15002-15003）
- 📊 **Web 设置界面**: 浏览器访问配置 AI 模型和系统设置
- 💬 **AI 对话接口**: 提供 AI 模型的输入输出接口
- 🔌 **插件扩展**: 支持热加载 MCP 和插件

### 🖱️ 网页控制端（端口 15000）
- 📱 **跨平台控制**: 浏览器访问即可控制应用
- 🎛️ **功能面板**: 集成所有核心功能的控制界面

### 🖥️ 局域网算力共享（端口 15300-15304）
- 🔍 **自动节点发现**: UDP广播自动发现局域网内其他节点
- 📊 **资源监控**: 实时监控CPU、内存、GPU、NPU资源
- ⚡ **负载均衡**: 智能任务调度，根据节点资源状态分配任务
- 🔐 **加密传输**: 支持Fernet和RSA加密协议
- 🤝 **分布式推理**: 自动选择本地或集群算力进行AI推理
- ❤️ **心跳机制**: 实时监控节点状态，自动剔除离线节点

### 🎨 UI视觉特效
- 🔮 **毛玻璃效果**: 完整的Glassmorphism效果，包括背景模糊、半透明叠加层和边框锐化
- 🎭 **透明度控制**: Windows风格的0-100%透明度调节
- ✨ **边框光晕**: 蓝色发光边框与阴影的自然过渡效果
- 🎬 **窗口动画**: 平滑的最大化/最小化过渡动画
- 🎯 **跨平台支持**: 兼容Windows和Linux操作系统

### 📊 系统资源监控
- 🖥️ **CPU监控**: 型号、核心数、使用率、温度
- 💾 **内存监控**: 总量、已用、可用、使用率百分比
- 🚀 **NPU监控**: 设备信息、显存使用、利用率、温度
- 📈 **实时统计**: 每秒更新，支持历史记录查询

## 🛠️ 技术栈

### 核心依赖
| 库 | 版本 | 说明 |
|----|------|------|
| Python | 3.13+ | 核心编程语言 |
| CustomTkinter | >=5.2.0 | 现代化桌面界面框架 |
| OpenAI | >=1.0.0 | OpenAI API 客户端 |
| PyAutoGUI | >=0.9.54 | 跨平台 GUI 自动化库 |
| Pyperclip | >=1.8.2 | 跨平台剪贴板操作库 |
| Keyboard | >=0.13.5 | 键盘事件监听和模拟库 |
| Requests | >=2.31.0 | HTTP 请求库 |
| Markdown2 | >=2.4.10 | Markdown 解析和渲染库 |
| Ultralytics | >=8.0.0 | YOLOv8 对象检测框架 |
| Pillow | >=10.0.0 | Python 图像处理库 |
| OpenCV-Python | >=4.8.0 | 计算机视觉库，支持视频处理和 RTMP 流 |
| Tenacity | >=8.2.0 | 重试机制库 |
| Pydantic | >=2.0.0 | 数据验证和序列化库 |
| Pydantic-Settings | >=2.0.0 | Pydantic 配置管理扩展 |
| Python-Dotenv | >=1.0.0 | 环境变量加载库 |
| Colorama | >=0.4.6 | 跨平台终端颜色输出库 |
| PySray | >=0.19.4 | 系统托盘图标库 |
| Websockets | >=10.0 | WebSocket 通信库 |

### 多媒体处理
| 库 | 版本 | 说明 |
|----|------|------|
| ffmpeg-python | >=0.2.0 | FFmpeg 绑定库 |
| Librosa | >=0.10.1 | 音频分析和处理库 |
| MoviePy | >=1.0.3 | 视频编辑库 |
| PyDub | >=0.25.1 | 音频处理库 |
| Sounddevice | >=0.4.6 | 音频设备访问库 |
| Soundcard | - | 系统音频捕获库，支持循环回送设备 |

### 办公文档
| 库 | 版本 | 说明 |
|----|------|------|
| python-docx | >=1.1.0 | Word 文档处理库 |
| openpyxl | >=3.1.2 | Excel 文件处理库 |
| xlwings | >=0.29.1 | Excel 交互库 |
| python-pptx | >=0.6.23 | PowerPoint 演示文稿处理库 |
| PyPDF2 | >=3.0.1 | PDF 文件处理库 |
| pdfplumber | >=0.10.2 | PDF 文本提取库 |
| PyMuPDF | >=1.23.10 | PDF 渲染和处理库 |

### 科学计算
| 库 | 版本 | 说明 |
|----|------|------|
| NumPy | >=1.26.2 | 科学计算基础库 |
| SciPy | >=1.11.4 | 科学计算库 |
| SymPy | >=1.12 | 符号计算库 |

### 日志与监控
| 库 | 版本 | 说明 |
|----|------|------|
| Loguru | >=0.7.2 | 现代化日志库 |
| Rich | >=13.7.0 | 富文本终端输出库 |
| psutil | >=5.9.8 | 系统进程和资源监控库 |

### 集群计算
| 库 | 版本 | 说明 |
|----|------|------|
| cryptography | >=41.0.0 | 加密算法库（Fernet/RSA） |

### UI视觉特效
| 库 | 版本 | 说明 |
|----|------|------|
| Pillow | >=10.0.0 | 图像处理库，用于毛玻璃和光晕效果 |
| ctypes | - | Python标准库，用于调用C/C++ DLL |
| pywinstyles | >=1.8 | Windows窗口美化库，支持Aero、Acrylic、Mica等效果 |

## ⚡ 一键安装和启动

### Windows 用户（推荐）

使用 PowerShell：

```powershell
.\start_app.ps1
```

脚本将自动执行：
1. 🔍 **智能 Python 检测** - 自动查找已安装的 Python 环境
2. 🐍 **使用系统 Python 3.13** - 确保 tkinter 功能正常
3. 📦 **依赖安装** - 自动安装所有必需的 Python 包
4. 🚀 **应用启动** - 启动 CustomTkinter 桌面界面

### 启动脚本配置

`start_app.ps1` 支持自定义运行参数：

```powershell
$RUN_ARGS = @(
    "--debug",                # 调试模式
    # "--noui",               # 无GUI模式（终端模式）
    # "--noweb",              # 不启动Web服务
    # "--noeditor",           # 不启动视频剪辑服务
    # "--nomonitor",          # 不启动桌面监控服务
    "--port", "15000",        # WebSocket端口
    "--api-port", "15002",    # API端口
    "--theme", "dark",        # 界面主题
    "--log-level", "DEBUG"    # 日志级别
)
```

## 📦 手动安装步骤

### 1. 克隆项目（暂时无此功能）

```bash
git clone <repository-url>
cd ai-computer-control
```

### 2. 使用系统 Python

本项目要求使用 Python 3.11+（确保 tkinter 功能正常）：

```bash
# 检查 Python 版本
python --version

# 或使用完整路径
$env:LOCALAPPDATA\Programs\Python\Python313\python.exe --version

```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

## ⚙️ 配置方法

### .env 文件配置（推荐）

复制 `.env.example` 为 `.env` 并修改：

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

### 运行参数

应用支持以下命令行参数（优先级：命令行 > .env > 默认值）：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--debug`, `-d` | 启用调试模式 | false |
| `--noui` | 无GUI模式（终端模式） | false |
| `--noweb` | 不启动Web服务 | false |
| `--noeditor` | 不启动视频剪辑服务 | false |
| `--nomonitor` | 不启动桌面监控服务 | false |
| `--nosystray` | 不显示系统托盘 | false |
| `--autorestart` | 服务崩溃后自动重启 | false |
| `--host` | 监听地址 | 0.0.0.0 |
| `--port`, `-p` | WebSocket端口 | 15000 |
| `--api-port` | API端口 | 15002 |
| `--rcon-port` | RCON端口 | 15001 |
| `--monitor-port` | 桌面监控端口 | 15004 |
| `--editor-port` | 视频编辑端口 | 15010 |
| `--theme` | 界面主题 | dark |
| `--theme-color` | 主题颜色 | blue |
| `--log-level` | 日志级别 | INFO |
| `--help` | 显示帮助信息 | - |
| `--nocluster` | 不启动集群服务 | false |

### 控制台命令

在终端模式（`--noui`）下，支持以下控制台命令：

| 命令 | 说明 |
|------|------|
| `/stop` | 停止所有服务并退出 |
| `/help` | 显示帮助信息 |
| `/status` | 显示服务状态 |

## 🚀 启动应用

### 推荐方式：一键智能启动

```cmd
# 或使用 PowerShell
.\start_app.ps1
```

### 手动启动

```bash
# 正常启动
python src/main.py

# 调试模式
python src/main.py --debug

# 终端模式（无GUI）
python src/main.py --noui

# 指定端口
python src/main.py --port 15000 --api-port 15002

# 显示帮助
python src/main.py --help
```

## 🌐 服务端口说明

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
| 15300 | 集群发现 | udp://localhost:15300 | UDP广播节点发现 |
| 15301 | 集群主通信 | tcp://localhost:15301 | 节点间TCP通信 |
| 15302 | 集群任务 | tcp://localhost:15302 | 任务分发端口 |
| 15303 | 集群数据 | tcp://localhost:15303 | 数据传输端口 |
| 15304 | 集群监控 | udp://localhost:15304 | 状态监控端口 |

## 📖 使用说明

### 基本使用流程

1. **配置 AI 提供者**
   - 选择 AI 提供者（NVIDIA/OpenAI/Ollama/Custom）
   - 输入必要的 API 密钥和 Base URL
   - 选择默认模型

2. **设置权限级别**
   - **None**: 仅查看模式，无操作权限
   - **View**: 查看模式，可执行查询操作
   - **Limited**: 允许鼠标和键盘基本操作
   - **Full**: 完整系统控制权限

3. **选择操作模式**
   - **Chat Mode**: 普通对话模式
   - **Control Mode**: AI 可生成并执行系统操作命令

4. **开始对话**
   - 输入自然语言指令
   - AI 会解析并执行相应的系统操作

### 示例指令

```
"将鼠标移动到屏幕中央"
"截取当前屏幕并分析内容"
"打开浏览器访问百度"
"在当前位置输入'Hello World'"
"检测屏幕上的按钮对象"
```

### 局域网算力共享使用

1. **启动集群服务**
   - 在多台电脑上运行AIclaw应用
   - 确保所有电脑在同一局域网内
   - 应用会自动发现其他节点

2. **查看集群状态**
   - 通过API或控制台查看集群信息
   - 实时监控各节点资源使用情况

3. **任务调度**
   - AI推理任务会自动分配到最优节点
   - 支持任务优先级设置
   - 自动负载均衡

### UI视觉特效使用

```python
# 导入视觉特效模块
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

**视觉特效模块提供两种实现方式：**

| 实现方式 | 文件 | 说明 |
|----------|------|------|
| 纯Python | `py_effects.py` | 使用Pillow库，无需编译，跨平台 |
| C/C++ | `gl_effects.cpp` | 使用OpenGL加速，需要编译DLL |

**编译C/C++版本（可选）：**

```bash
# 进入特效模块目录
cd src/ui/effects

# 运行编译脚本
python build_effects.py

# 生成的DLL文件位于 bin/ 目录
```

## 🏗️ 项目结构

```
ai-computer-control/
├── src/                          # 源代码目录
│   ├── config/                   # 配置管理
│   │   ├── ai_providers.py       # AI 提供者配置
│   │   ├── providers_config.json # 提供者配置数据
│   │   └── settings.py           # 全局设置
│   ├── services/                 # 服务层
│   │   ├── ai_service.py         # AI 服务接口
│   │   ├── ai_agent.py           # AI代理系统
│   │   ├── tool_registry.py      # 工具注册表
│   │   ├── screen_monitor.py     # 桌面监控服务
│   │   ├── video_editor.py       # 视频剪辑服务
│   │   ├── api_server.py         # API 服务器
│   │   ├── websocket_server.py   # WebSocket 服务器
│   │   ├── local_model_service.py# 本地模型服务
│   │   └── cluster/              # 集群服务模块
│   │       ├── __init__.py       # 集群管理器
│   │       ├── gpu_detector.py   # GPU资源检测
│   │       ├── system_monitor.py # 系统资源监控(CPU/内存/NPU)
│   │       ├── lan_node.py       # 局域网节点通信
│   │       ├── task_scheduler.py # 任务调度器
│   │       ├── secure_transport.py# 加密传输
│   │       ├── cluster_monitor.py# 集群监控
│   │       ├── distributed_inference.py # 分布式推理
│   │       └── cluster_api.py    # 集群API服务
│   ├── system/                   # 系统控制
│   │   ├── controller.py         # 鼠标键盘控制
│   │   └── vision.py             # 视觉处理
│   ├── ui/                       # 用户界面
│   │   ├── customtkinter_app.py  # CustomTkinter 桌面界面
│   │   ├── theme_settings_panel.py # 主题设置面板
│   │   ├── splash_screen.py      # 启动画面
│   │   └── effects/              # UI视觉特效模块
│   │       ├── __init__.py       # 模块入口
│   │       ├── py_effects.py     # 纯Python实现（毛玻璃/光晕/动画）
│   │       ├── gl_effects.py     # C/C++实现（OpenGL加速）
│   │       ├── gl_effects.h      # C接口头文件
│   │       ├── CMakeLists.txt    # CMake编译配置
│   │       └── build_effects.py  # 编译脚本
│   ├── utils/                    # 工具模块
│   │   ├── image_processor.py    # 图像处理
│   │   ├── logger.py             # 日志记录
│   │   ├── markdown_renderer.py  # Markdown 渲染
│   │   ├── parser.py             # 响应解析
│   │   └── yolo_detector.py      # YOLO 检测器
│   ├── main.py                   # 主入口
│   └── __init__.py
├── docs/                         # 文档目录
│   └── cluster_computing.md      # 集群算力共享说明文档
├── .env.example                  # 环境变量示例
├── requirements.txt              # Python 依赖
├── start_app.bat                 # Windows 启动脚本
├── start_app.ps1                 # PowerShell 启动脚本
└── README.md                     # 项目说明
```

## 🔧 高级配置

### 自定义 AI 提供者

1. 在 `src/config/providers_config.json` 中添加新提供者配置
2. 或在运行时界面中动态添加

### 安全设置

- 使用 Limited 权限开始，逐步升级
- 鼠标移动到屏幕左上角可触发安全停止
- API 密钥不会在界面中明文显示

### 性能优化

- 调整 `MAX_CALLS_PER_MINUTE` 控制 API 调用频率
- 设置合适的 `TEMPERATURE` 和 `MAX_TOKENS` 参数
- 使用本地 Ollama 减少网络延迟

## 🧪 开发与测试

### 运行测试

```bash
pip install pytest pytest-mock
pytest tests/
```

### 代码规范检查

```bash
pip install flake8
flake8 src/
```

## 📡 流媒体传输协议说明

### 视频传输（端口 15009）

| 协议 | 主/备 | 说明 | 适用场景 |
|------|-------|------|----------|
| **RTMP** | 主 | Real-Time Messaging Protocol，实时消息传输协议 | 直播推流、传统流媒体 |
| **SRT** | 备 | Secure Reliable Transport，安全可靠传输 | 低延迟、高质量传输 |
| **SRTP** | 备 | Secure Real-time Transport Protocol，安全实时传输 | 加密传输、需要安全性 |

**配置示例**:
```env
# 使用 RTMP 作为主协议
VIDEO_PROTOCOL_PRIORITY="rtmp,srt,srtp"
RTMP_ENABLED=true
RTMP_URL="rtmp://your-server/live/stream"

# 或使用 SRT 作为主协议
VIDEO_PROTOCOL_PRIORITY="srt,rtmp,srtp"
SRT_ENABLED=true
SRT_PORT=15009
SRT_LATENCY=120
```

### 音频传输（端口 15008）

| 协议 | 主/备 | 说明 | 适用场景 |
|------|-------|------|----------|
| **WebRTC** | 主 | Web Real-Time Communication，网页实时通信 | 浏览器直连、低延迟 |
| **SRTP** | 备 | Secure RTP，安全实时传输协议 | 加密VoIP通话 |
| **SMPTE 2110** | 备 | 专业广电传输标准 | 广播级IP传输 |

**配置示例**:

```env
# 使用 WebRTC 作为主协议
AUDIO_PROTOCOL_PRIORITY="webrtc,srtp,smpte2110"
WEBRTC_ENABLED=true
WEBRTC_PORT=15008

# 或使用 SMPTE 2110 作为专业音频传输
AUDIO_PROTOCOL_PRIORITY="smpte2110,webrtc,srtp"
SMPTE2110_ENABLED=true
SMPTE2110_MULTICAST="239.255.0.1"
```

### 远程桌面式视频流

远程桌面式视频流采用类似远程桌面的压缩传输方式，大幅降低带宽占用：

| 参数 | 说明 | 默认值 | 建议值 |
|------|------|--------|--------|
| `RD_DIFF_THRESHOLD` | 帧差阈值，越大变化检测越严格 | 10 | 5-20 |
| `RD_BLOCK_SIZE` | 分块大小，越小压缩率越高 | 64 | 32-128 |
| `RD_KEYFRAME_INTERVAL` | 关键帧间隔 | 60 | 30-120 |
| `RD_MIN_QUALITY` | 最低编码质量 | 30 | 20-40 |
| `RD_MAX_QUALITY` | 最高编码质量 | 95 | 80-100 |

## ⚠️ 常见问题与故障排除

### 问题1: 端口被占用

**错误信息**: `OSError: [Errno 10048] 通常每个套接字地址只允许使用一次`

**解决方法**:
```powershell
# 查找占用端口的进程
netstat -ano | findstr "15000"

# 终止进程（将 <PID> 替换为实际进程ID）
taskkill /F /PID <PID>
```

### 问题2: tkinter 模块缺失

**错误信息**: `ModuleNotFoundError: No module named 'tkinter'`

**解决方法**:
- 确保使用 Python 3.13（嵌入式 Python 不包含 tkinter）
- 使用完整路径运行：`$env:LOCALAPPDATA\Programs\Python\Python313\python.exe`
- 使用venv环境运行：`venv\Scripts\python.exe`

### 问题3: 依赖安装失败

**错误信息**: `ERROR: Could not find a version that satisfies the requirement`

**解决方法**:

```bash
# 更新 pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

#使用已经安装的环境（无需安装）
venv\Scripts\python.exe
```

### 问题4: 音频捕获警告

**警告信息**: `SoundcardRuntimeWarning: data discontinuity in recording`

**说明**: 这是 Windows 音频捕获的正常警告，不影响功能。

### 问题5: WebSocket 连接失败

**错误信息**: `WebSocket connection failed`

**解决方法**:
- 确保防火墙允许相关端口
- 检查服务是否正常启动
- 尝试使用 `--host 0.0.0.0` 参数

## 📄 许可证

本项目采用 GNU GPL v3 许可证并附加禁止商业使用的条款。查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献者

感谢所有为本项目做出贡献的开发者！

[![Contributors](https://contrib.rocks/image?chen-xin-Liam/powerful-claw)](https://github.com/chen-xin-Liam/powerful-claw/graphs/contributors)




## 📞 支持与反馈（没有此功能）

- 📧 提交 [Issue](https://github.com/your-username/ai-computer-control/issues) 报告问题
- 💬 参与 [Discussions](https://github.com/your-username/ai-computer-control/discussions) 讨论功能

---

⭐ 如果这个项目对你有帮助，请给它一个star！
