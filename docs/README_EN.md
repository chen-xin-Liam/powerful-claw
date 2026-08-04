# AI Computer Control 🤖

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)[![environment](https://img.shields.io/badge/environment-venv/3.13.3-green.svg)](https://www.python.org/)
[![License: GPLv3+NonCommercial](https://img.shields.io/badge/License-GPLv3%2B%20NC-red.svg)](LICENSE)[![bilibili](https://img.shields.io/badge/bilibili-%E6%95%B0%E7%A7%91%E6%99%BA%E6%98%9F-blue.svg)](https://space.bilibili.com/3493111196027162)

A powerful AI computer control application that integrates **AI intelligent conversation**, **desktop monitoring**, **video editing**, **RCON broadcasting**, and other features to achieve automated system operations and intelligent control.

### Star History

<a href="https://www.star-history.com/?repos=chen-xin-Liam%2Fpowerful-claw&type=date&legend=bottom-right">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=chen-xin-Liam/powerful-claw&type=date&theme=dark&legend=bottom-right&sealed_token=YFwFvLj13TKlFm-6F2v-wK3CccWetfpWS4UxnJ9D60Q1E0QUwLTvlh5FXnpfvPl1c15Ff4xjJb_GQ2wf727u_u6pbsgElr9z2q6h1_13yMPif_leAh2hOgBv-l84SdghyCcCWLzxO23V0H09ajX6NidIKg5VSovfolqbK1mZW7yRAJondULB2e_XK86L" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=chen-xin-Liam/powerful-claw&type=date&legend=bottom-right&sealed_token=YFwFvLj13TKlFm-6F2v-wK3CccWetfpWS4UxnJ9D60Q1E0QUwLTvlh5FXnpfvPl1c15Ff4xjJb_GQ2wf727u_u6pbsgElr9z2q6h1_13yMPif_leAh2hOgBv-l84SdghyCcCWLzxO23V0H09ajX6NidIKg5VSovfolqbK1mZW7yRAJondULB2e_XK86L" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=chen-xin-Liam/powerful-claw&type=date&legend=bottom-right&sealed_token=YFwFvLj13TKlFm-6F2v-wK3CccWetfpWS4UxnJ9D60Q1E0QUwLTvlh5FXnpfvPl1c15Ff4xjJb_GQ2wf727u_u6pbsgElr9z2q6h1_13yMPif_leAh2hOgBv-l84SdghyCcCWLzxO23V0H09ajX6NidIKg5VSovfolqbK1mZW7yRAJondULB2e_XK86L" />
 </picture>
</a>

## ✨ Features

### 🤖 AI Intelligent Control
- 🚀 **Multiple AI Provider Support**: Supports NVIDIA, OpenAI, Ollama, and custom AI services
- 🔄 **Automatic Cyclic Conversation**: Supports multi-turn automatic conversation with configurable calls per minute limit
- 🖱️ **System Control**: Supports mouse movement, clicking, dragging, and keyboard input operations
- 📷 **Visual Capture**: Supports screen capture, camera capture, and YOLO object detection
- 🔒 **Permission Management**: Four-level permission control (None/View/Limited/Full)
- 💬 **Thinking Process Visualization**: Real-time display of AI reasoning process and streaming response

### 📺 Desktop Monitoring (Ports 15004-15009)
- 🎥 **Real-time Screen Capture**: Supports 1-30 FPS adjustable frame rate
- 🔊 **System Audio Capture**: Captures all application sounds (supports loopback devices)
- 📡 **Multi-protocol Video Transmission**: Port 15009 supports RTMP (primary), SRT, SRTP protocol adaptation
- 📡 **Multi-protocol Audio Transmission**: Port 15008 supports WebRTC (primary), SRTP, SMPTE 2110 protocol adaptation
- 🎨 **Multiple Quality Presets**: Smooth, Standard, HD, HDR, Ultra HD, Blu-ray
- 🖥️ **Web Real-time Monitoring**: Access via browser to view desktop screen
- 🖥️ **Remote Desktop-style Video Streaming**: Frame difference compression + block encoding, significantly reducing bandwidth usage

### 🎬 Video Editing (Port 15010)
- 📁 **Media Management**: Supports importing video, audio, image, GIF, subtitle files
- ⏱️ **Multi-track Timeline**: Video track, audio track, subtitle track, picture-in-picture track
- ✂️ **Basic Editing**: Cut, merge, copy, paste, delete, ripple delete
- 🎨 **Color Grading & Effects**: Brightness, contrast, saturation, filters, transition effects
- 🎵 **Audio Processing**: Multi-track mixing, noise reduction, equalizer, speech-to-subtitle
- 📝 **Subtitle Editing**: Manual/automatic subtitle addition, style adjustment, SRT/ASS export
- 📤 **Export Rendering**: Supports 1080P/2K/4K, 24/30/60fps, MP4/MOV/GIF/WebM

### 🎮 RCON Broadcasting (Port 15001)
- 📡 **Real-time Console Broadcasting**: WebSocket-based broadcasting of RCON console information
- 🔔 **Event Push**: Real-time push of game server events and logs

### 🌐 API Services (Ports 15002-15003)
- 📊 **Web Settings Interface**: Browser access to configure AI models and system settings
- 💬 **AI Conversation Interface**: Provides input/output interface for AI models
- 🔌 **Plugin Extension**: Supports hot-loading MCP and plugins

### 🖱️ Web Control Panel (Port 15000)
- 📱 **Cross-platform Control**: Browser access to control the application
- 🎛️ **Function Panel**: Integrated control interface for all core features

### 🖥️ LAN Computing Power Sharing (Ports 15300-15304)
- 🔍 **Automatic Node Discovery**: UDP broadcast automatically discovers other nodes in LAN
- 📊 **Resource Monitoring**: Real-time monitoring of CPU, memory, GPU, NPU resources
- ⚡ **Load Balancing**: Intelligent task scheduling, assigns tasks based on node resource status
- 🔐 **Encrypted Transmission**: Supports Fernet and RSA encryption protocols
- 🤝 **Distributed Inference**: Automatically selects local or cluster computing power for AI inference
- ❤️ **Heartbeat Mechanism**: Real-time monitoring of node status, automatic removal of offline nodes

### 🎨 UI Visual Effects
- 🔮 **Glass Effect**: Complete Glassmorphism effect, including background blur, semi-transparent overlay, and border sharpening
- 🎭 **Transparency Control**: Windows-style 0-100% transparency adjustment
- ✨ **Border Glow**: Natural transition effect of blue glowing border and shadow
- 🎬 **Window Animation**: Smooth maximize/minimize transition animation
- 🎯 **Cross-platform Support**: Compatible with Windows and Linux operating systems

### 📊 System Resource Monitoring
- 🖥️ **CPU Monitoring**: Model, core count, usage, temperature
- 💾 **Memory Monitoring**: Total, used, available, usage percentage
- 🚀 **NPU Monitoring**: Device information, memory usage, utilization, temperature
- 📈 **Real-time Statistics**: Updated per second, supports historical record query


## ⚡ One-click Installation and Launch

### Windows Users (Recommended)

Using PowerShell:

```powershell
.\start_app.ps1
```

The script will automatically execute:
1. 🔍 **Intelligent Python Detection** - Automatically find installed Python environment
2. 🐍 **Use System Python 3.13** - Ensure tkinter functions properly
3. 📦 **Dependency Installation** - Automatically install all required Python packages
4. 🚀 **Application Launch** - Start CustomTkinter desktop interface

### Startup Script Configuration

`start_app.ps1` supports custom runtime parameters:

```powershell
$RUN_ARGS = @(
    "--debug",                # Debug mode
    # "--noui",               # No GUI mode (terminal mode)
    # "--noweb",              # Do not start Web service
    # "--noeditor",           # Do not start video editing service
    # "--nomonitor",          # Do not start desktop monitoring service
    "--port", "15000",        # WebSocket port
    "--api-port", "15002",    # API port
    "--theme", "dark",        # Interface theme
    "--log-level", "DEBUG"    # Log level
)
```

## 📦 Manual Installation Steps

### 1. Clone Project (Temporarily unavailable)

```bash
git clone <repository-url>
cd ai-computer-control
```

### 2. Use System Python

This project requires Python 3.11+ (ensure tkinter functions properly):

```bash
# Check Python version
python --version

# Or use full path
$env:LOCALAPPDATA\Programs\Python\Python313\python.exe --version

```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration Methods

### .env File Configuration (Recommended)

Copy `.env.example` to `.env` and modify:

```env
# ============ Runtime Mode ============
DEBUG=true
NOUI=false
NOWEB=false
NOEDITOR=false
NOMONITOR=false

# ============ Server Settings ============
HOST=0.0.0.0
PORT=15000
API_PORT=15002
RCON_PORT=15001
SCREEN_MONITOR_PORT=15004
VIDEO_EDITOR_PORT=15010

# ============ Desktop Monitoring Settings ============
SCREEN_MONITOR_QUALITY=80
SCREEN_MONITOR_FPS=15
SCREEN_MONITOR_BITRATE=2000000

# ============ Video Transmission Settings (Port 15009) ============
# Video transmission protocol priority: rtmp, srt, srtp
VIDEO_PROTOCOL_PRIORITY="rtmp,srt,srtp"
RTMP_ENABLED=false
RTMP_URL="rtmp://localhost/live/stream"
SRT_ENABLED=false
SRT_PORT=15009
SRT_LATENCY=120
SRTP_ENABLED=false
SRTP_PORT=15009
SRTP_KEY=""

# ============ Audio Transmission Settings (Port 15008) ============
# Audio transmission protocol priority: webrtc, srtp, smpte2110
AUDIO_PROTOCOL_PRIORITY="webrtc,srtp,smpte2110"
WEBRTC_ENABLED=true
WEBRTC_PORT=15008
AUDIO_SRTP_ENABLED=false
AUDIO_SRTP_PORT=15008
SMPTE2110_ENABLED=false
SMPTE2110_PORT=15008
SMPTE2110_MULTICAST="239.255.0.1"

# ============ Remote Desktop-style Video Streaming ============
REMOTE_DESKTOP_STREAM=true
RD_DIFF_THRESHOLD=10
RD_BLOCK_SIZE=64
RD_KEYFRAME_INTERVAL=60
RD_MOTION_DETECTION=true
RD_ADAPTIVE_QUALITY=true
RD_MIN_QUALITY=30
RD_MAX_QUALITY=95

# ============ AI Settings ============
AI_PROVIDER=nvidia
AI_MODEL=zephyr-7b-beta
AI_API_KEY=your_api_key_here
AI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MAX_TOKENS=4096
AI_TEMPERATURE=0.7

# ============ Interface Settings ============
THEME=dark
THEME_COLOR=blue
LANGUAGE=zh_CN

# ============ Proxy Settings ============
PROXY_ENABLED=false
PROXY_URL=http://127.0.0.1:7890

# ============ SSL Settings ============
CERT_ENABLED=false
CERT_PATH=./cert.pem
KEY_PATH=./key.pem

# ============ Cluster Settings ============
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

### Runtime Parameters

The application supports the following command-line parameters (priority: command line > .env > default values):

| Parameter | Description | Default Value |
|------|------|--------|
| `--debug`, `-d` | Enable debug mode | false |
| `--noui` | No GUI mode (terminal mode) | false |
| `--noweb` | Do not start Web service | false |
| `--noeditor` | Do not start video editing service | false |
| `--nomonitor` | Do not start desktop monitoring service | false |
| `--nosystray` | Do not display system tray | false |
| `--autorestart` | Automatically restart after service crash | false |
| `--host` | Listening address | 0.0.0.0 |
| `--port`, `-p` | WebSocket port | 15000 |
| `--api-port` | API port | 15002 |
| `--rcon-port` | RCON port | 15001 |
| `--monitor-port` | Desktop monitoring port | 15004 |
| `--editor-port` | Video editing port | 15010 |
| `--theme` | Interface theme | dark |
| `--theme-color` | Theme color | blue |
| `--log-level` | Log level | INFO |
| `--help` | Display help information | - |
| `--nocluster` | Do not start cluster service | false |

### Console Commands

In terminal mode (`--noui`), the following console commands are supported:

| Command | Description |
|------|------|
| `/stop` | Stop all services and exit |
| `/help` | Display help information |
| `/status` | Display service status |

## 🚀 Launch Application

### Recommended Method: One-click Smart Launch

```cmd
# Or use PowerShell
.\start_app.ps1
```

### Manual Launch

```bash
# Normal launch
python src/main.py

# Debug mode
python src/main.py --debug

# Terminal mode (no GUI)
python src/main.py --noui

# Specify ports
python src/main.py --port 15000 --api-port 15002

# Display help
python src/main.py --help
```

## 🌐 Service Port Description

| Port | Service | Access Address | Description |
|------|------|----------|------|
| 15000 | Web Control Panel | http://localhost:15000 | Cross-platform Web control interface |
| 15001 | RCON Broadcasting | ws://localhost:15001/rcon | RCON console information broadcasting |
| 15002 | API Service | http://localhost:15002 | AI model configuration and conversation interface |
| 15003 | API WebSocket | ws://localhost:15003/api | AI conversation WebSocket interface |
| 15004 | Desktop Monitoring | http://localhost:15004 | Real-time desktop monitoring page |
| 15006 | Monitoring WebSocket | ws://localhost:15006 | Desktop monitoring WebSocket |
| 15007 | UDP Video Stream | udp://localhost:15007 | Low-latency video transmission |
| 15010 | Video Editing | http://localhost:15010 | Web video editing editor |
| 15012 | Editing WebSocket | ws://localhost:15012 | Video editing WebSocket |
| 15300 | Cluster Discovery | udp://localhost:15300 | UDP broadcast node discovery |
| 15301 | Cluster Main Communication | tcp://localhost:15301 | Inter-node TCP communication |
| 15302 | Cluster Task | tcp://localhost:15302 | Task distribution port |
| 15303 | Cluster Data | tcp://localhost:15303 | Data transmission port |
| 15304 | Cluster Monitoring | udp://localhost:15304 | Status monitoring port |



### LAN Computing Power Sharing Usage

1. **Start Cluster Service**
   - Run AIclaw application on multiple computers
   - Ensure all computers are in the same LAN
   - Application will automatically discover other nodes

2. **View Cluster Status**
   - View cluster information through API or console
   - Real-time monitoring of resource usage on each node

3. **Task Scheduling**
   - AI inference tasks will be automatically assigned to the optimal node
   - Supports task priority settings
   - Automatic load balancing

### UI Visual Effects Usage

```python
# Import visual effects module
from src.ui.effects import GLEffects, GLColor, GlassEffectParams

# Initialize effects engine
effects = GLEffects()
effects.init(width=800, height=600)

# Set transparency (0.0-1.0)
effects.set_transparency(0.8)

# Enable glass effect
effects.enable_glass_effect(True)

# Configure glass parameters
glass_params = GlassEffectParams()
glass_params.blur_radius = 15.0
glass_params.opacity = 0.7
glass_params.tint_color = GLColor(0.15, 0.15, 0.2, 0.7)
effects.set_glass_params(glass_params)

# Enable border glow effect
effects.enable_glow_effect(True)

# Execute rendering
effects.render()

# Shutdown effects engine
effects.shutdown()
```

**Visual effects module provides two implementation methods:**

| Implementation Method | File | Description |
|----------|------|------|
| Pure Python | `py_effects.py` | Uses Pillow library, no compilation required, cross-platform |
| C/C++ | `gl_effects.cpp` | Uses OpenGL acceleration, requires DLL compilation |

**Compile C/C++ version (optional):**

```bash
# Enter effects module directory
cd src/ui/effects

# Run compilation script
python build_effects.py

# Generated DLL file is located in bin/ directory
```

## 🏗️ Project Structure

```
ai-computer-control/
├── src/                          # Source code directory
│   ├── config/                   # Configuration management
│   │   ├── ai_providers.py       # AI provider configuration
│   │   ├── providers_config.json # Provider configuration data
│   │   └── settings.py           # Global settings
│   ├── services/                 # Service layer
│   │   ├── ai_service.py         # AI service interface
│   │   ├── ai_agent.py           # AI agent system
│   │   ├── tool_registry.py      # Tool registry
│   │   ├── screen_monitor.py     # Desktop monitoring service
│   │   ├── video_editor.py       # Video editing service
│   │   ├── api_server.py         # API server
│   │   ├── websocket_server.py   # WebSocket server
│   │   ├── local_model_service.py# Local model service
│   │   └── cluster/              # Cluster service module
│   │       ├── __init__.py       # Cluster manager
│   │       ├── gpu_detector.py   # GPU resource detection
│   │       ├── system_monitor.py # System resource monitoring (CPU/Memory/NPU)
│   │       ├── lan_node.py       # LAN node communication
│   │       ├── task_scheduler.py # Task scheduler
│   │       ├── secure_transport.py# Encrypted transmission
│   │       ├── cluster_monitor.py# Cluster monitoring
│   │       ├── distributed_inference.py # Distributed inference
│   │       └── cluster_api.py    # Cluster API service
│   ├── system/                   # System control
│   │   ├── controller.py         # Mouse and keyboard control
│   │   └── vision.py             # Visual processing
│   ├── ui/                       # User interface
│   │   ├── customtkinter_app.py  # CustomTkinter desktop interface
│   │   ├── theme_settings_panel.py # Theme settings panel
│   │   ├── splash_screen.py      # Splash screen
│   │   └── effects/              # UI visual effects module
│   │       ├── __init__.py       # Module entry
│   │       ├── py_effects.py     # Pure Python implementation (glass/glow/animation)
│   │       ├── gl_effects.py     # C/C++ implementation (OpenGL acceleration)
│   │       ├── gl_effects.h      # C interface header file
│   │       ├── CMakeLists.txt    # CMake compilation configuration
│   │       └── build_effects.py  # Compilation script
│   ├── utils/                    # Utility modules
│   │   ├── image_processor.py    # Image processing
│   │   ├── logger.py             # Logging
│   │   ├── markdown_renderer.py  # Markdown rendering
│   │   ├── parser.py             # Response parsing
│   │   └── yolo_detector.py      # YOLO detector
│   ├── main.py                   # Main entry
│   └── __init__.py
├── docs/                         # Documentation directory
│   └── cluster_computing.md      # Cluster computing sharing documentation
├── .env.example                  # Environment variable example
├── requirements.txt              # Python dependencies
├── start_app.bat                 # Windows startup script
├── start_app.ps1                 # PowerShell startup script
└── README.md                     # Project description
```

## 🔧 Advanced Configuration

### Custom AI Provider

1. Add new provider configuration in `src/config/providers_config.json`
2. Or dynamically add during runtime interface

### Security Settings

- Start with Limited permission and gradually upgrade
- Moving mouse to top-left corner of screen can trigger safety stop
- API keys are not displayed in plaintext in interface

### Performance Optimization

- Adjust `MAX_CALLS_PER_MINUTE` to control API call frequency
- Set appropriate `TEMPERATURE` and `MAX_TOKENS` parameters
- Use local Ollama to reduce network latency

## 🧪 Development and Testing

### Run Tests

```bash
pip install pytest pytest-mock
pytest tests/
```

### Code Style Check

```bash
pip install flake8
flake8 src/
```



## 📄 License

This project uses GNU GPL v3 license with additional non-commercial use clause. See [LICENSE](LICENSE) file for details.

## 🤝 Contributors

Thanks to all developers who contributed to this project!

[![Contributors](https://contrib.rocks/image?chen-xin-Liam/powerful-claw)](https://github.com/chen-xin-Liam/powerful-claw/graphs/contributors)




## 📞 Support and Feedback (Feature not available)

- 📧 Submit [Issue](https://github.com/chen-xin-Liam/powerful-claw/issues) to report problems
- 💬 Participate in [Discussions](https://github.com/chen-xin-Liam/powerful-claw/discussions) to discuss features

---

⭐ If this project helps you, please give it a star!