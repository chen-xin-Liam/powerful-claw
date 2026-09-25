# 🤖 powerful-claw

<div align="center">

**English** | [简体中文](docs/zh/README.md) | [Русский](docs/ru/README.md) | [Français](docs/fr/README.md)

<!-- TODO: Replace with real logo (256×256 PNG/SVG, docs/images/logo.png)
<img src="docs/images/logo.png" alt="powerful-claw" width="200" height="200" />
-->

#### ⚠️ **Current Status: Under Development / WIP, known bugs exist — not production-ready**
#### ⚠️ **GitHub is the only primary repository; other platforms are mirrors**

**Let AI see and operate your local computer** — an open-source desktop automation agent control hub.
Chains multimodal LLMs, screen vision perception, and keyboard/mouse automation; includes desktop streaming, a simple video editor, and LAN compute node scheduling.

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-success.svg?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/chen-xin-Liam/powerful-claw?style=social)](https://github.com/chen-xin-Liam/powerful-claw/stargazers)
[![bilibili](https://img.shields.io/badge/bilibili-%E6%95%B0%E7%A7%91%E6%99%BA%E6%98%9F-00A1D6.svg?logo=bilibili&logoColor=white)](https://space.bilibili.com/3493111196027162)
</div>

---

> 💡 **Project Vision**
> Most AI agent projects stop at conversation. This project builds a local end-side agent that **reads the screen, understands UI content, and operates the keyboard/mouse to complete tasks**.
> Desktop streaming, video editing, and LAN compute clustering are supporting modules — some still in development.

## ✨ Key Features

- 🧠 **End-side Desktop AI Agent**: Connects to multimodal LLMs (Ollama / OpenAI-compatible / NVIDIA API), uses YOLO for screen object detection, enables screenshot understanding and keyboard/mouse automation. Built-in 4-level permission model (None/View/Limited/Full) to reduce misoperation risk.
- 📺 **Desktop Real-time Streaming**: Adjustable 1–30 FPS, supports RTMP/SRT/WebRTC protocols. Frame-difference compression + chunked encoding reduces bandwidth. Viewable directly in browser.
- 🎬 **Built-in Web Video Editor (Basic)**: Multi-track timeline, color grading filters, SRT/ASS subtitles, speech-to-text. Export to MP4/MOV/GIF/WebM (1080P/2K/4K).
- 🌐 **LAN Compute Scheduling (WIP)**: UDP auto-discovery of intranet nodes, CPU/Memory/GPU/NPU load collection, task scheduling, Fernet/RSA encrypted transmission. Combine idle machines into an inference cluster.
- 🎨 **Pluggable Desktop UI**: Two rendering implementations — Python (Pillow) lightweight version + C++/OpenGL high-performance frosted glass and window animations. Cross-platform switchable.
- 🛠️ **Native Python Core**: Lightweight architecture for easy source reading, secondary development, and local debugging.

## 📚 Tech Stack

| Module | Technology | Notes |
|--------|-----------|-------|
| AI Agent | Python 3.13+ | Multimodal LLM driven, supports Ollama/OpenAI/NVIDIA |
| Vision | Python + YOLOv8 | Screen capture, UI object detection, high-DPI support |
| Desktop Control | Python (pyautogui/keyboard) | Cross-platform mouse/keyboard automation, 4-level permissions |
| Video Streaming | Python + FFmpeg | RTMP/SRT/WebRTC, frame-difference compression |
| UI | CustomTkinter + C++/OpenGL | Frosted glass/glow animations, dual implementations |
| Cluster Computing | Python + UDP/Encryption | LAN node discovery, task scheduling, Fernet/RSA encryption |
| Logging/Errors | Loguru/Rich | Unified error codes, tiered logging, full-link debug tracing |
| Math Engine | C++17 + cppyy embedded Python | 44 node types (arithmetic/trig/matrix LU/statistics), pure-Python fallback |

## 🚀 Implemented

- [x] Multi-AI backend (Ollama, OpenAI-compatible API, NVIDIA), easy to extend
- [x] Screen capture + YOLO object detection
- [x] Mouse and keyboard automation
- [x] Desktop real-time streaming (RTMP/SRT/WebRTC)
- [x] LAN node discovery and hardware monitoring
- [x] Unified logging and error handling
- [x] Basic window UI management
- [x] Q&A interaction entry

## 🐛 Known Issues & Incomplete Modules

- Screen coordinate recognition deviation on high-DPI displays
- Occasional screen flicker when switching display resolution
- Only basic validation on Windows 10/11
- Theme switching may occasionally freeze the UI
- LAN compute scheduling: node scheduling logic incomplete
- Video editor: basic architecture only, features incomplete

## 🛠️ Quick Start

```bash
# 1. Clone
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python src/main.py

# 4. Access WebUI (streaming + editing)
# Open in browser: http://localhost:8080
```

## 📖 Documentation

**Languages**: [English](docs/README.md) · [简体中文](docs/zh/INDEX.md) · [Русский](docs/ru/INDEX.md) · [Français](docs/fr/INDEX.md)

| Document | English | 中文 |
|----------|---------|------|
| Getting Started | [Installation](docs/en/installation.md) | [安装指南](docs/zh/installation.md) |
| Configuration | [Configuration](docs/en/configuration.md) | [配置指南](docs/zh/configuration.md) |
| User Manual | [User Manual](docs/en/user_manual.md) | [用户手册](docs/zh/user_manual.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) | — |
| Security | [SECURITY.md](SECURITY.md) | [安全策略](docs/zh/SECURITY.md) |

## 🧪 Testing

```bash
# Full test suite
pytest auto_tests/

# Standalone runner (no pytest required)
python auto_tests/run_tests.py

# Performance benchmarks
python benchmarks/perf_bench.py compute --iters 2000
python benchmarks/perf_bench.py startup --runs 7
```

See [docs/zh/testing.md](docs/zh/testing.md) for details.

## 🔌 MCP Server Import

Import standard MCP configurations (`.mcp.json`, Claude Desktop, VS Code):

```bash
# List available templates
python -m src.services.mcp_importer --templates

# Import from config file
python -m src.services.mcp_importer path/to/mcp.json
```

## 📦 Build Executable

```bash
python scripts/build_exe.py
```

Output goes to `dist/AIComputerControl/`. See [docs/zh/build.md](docs/zh/build.md) for details.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding conventions, and how to submit changes.

## 📄 License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
