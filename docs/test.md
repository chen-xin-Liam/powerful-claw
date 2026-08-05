<div align="center">

<!-- TODO: 替换为真实 Logo（建议 256×256 PNG/SVG，放 docs/images/logo.png）
<img src="docs/images/logo.png" alt="AI Computer Control" width="200" height="200" />
-->

# 🤖 powerful-claw  
#### ⚠️ **当前状态：开发中 / WIP / 存在已知 Bug，请勿用于生产环境**

**让 AI 真正"看见并操作"你的电脑** —— 一个把多模态大模型变成桌面自动化 Agent 的开源控制中枢，开箱即用地串联起 **AI 对话 → 视觉感知 → 鼠键控制 → 桌面推流 → 视频剪辑 → 局域网算力共享**。

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-success.svg?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-GPL--3.0%20%2B%20NonCommercial-red.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/chen-xin-Liam/powerful-claw?style=social)](https://github.com/chen-xin-Liam/powerful-claw/stargazers)
[![bilibili](https://img.shields.io/badge/bilibili-%E6%95%B0%E7%A7%91%E6%99%BA%E6%98%9F-00A1D6.svg?logo=bilibili&logoColor=white)](https://space.bilibili.com/3493111196027162)

<!-- TODO: 启用 CI 后替换为真实构建/覆盖率徽章
[![Build](https://img.shields.io/github/actions/workflow/status/chen-xin-Liam/powerful-claw/.github/workflows/ci.yml?branch=main&label=build)](...)
[![Coverage](https://img.shields.io/codecov/c/github/chen-xin-Liam/powerful-claw.svg)](...)
-->

</div>

---

> 💡 **一句话定位**：如果你想要一个不只是聊天、而是能**真的帮你在电脑上干活**的 AI 助手 —— 截屏看屏幕、移动鼠标点击、推流远程监控、剪辑录屏、还能把闲置的局域网电脑凑成算力池 —— 那它就是了。

## ✨ 核心亮点

- 🧠 **AI Agent 落地，而非聊天框** —— 多模态大模型（NVIDIA / OpenAI / Ollama / 自定义）驱动，能截图、能看屏幕（YOLO 目标检测）、能控制鼠标键盘，四级权限（None/View/Limited/Full）保证安全
- 📺 **桌面实时推流** —— 1–30 FPS 可调，多协议视频（RTMP/SRT/SRTP）+ 多协议音频（WebRTC/SRTP/SMPTE 2110）自适应，浏览器打开即看，帧差压缩 + 分块编码大幅降带宽
- 🎬 **内置 Web 视频剪辑器** —— 多轨时间轴、调色滤镜、字幕 SRT/ASS、语音转字幕，1080P/2K/4K 导出 MP4/MOV/GIF/WebM
- 🌐 **局域网算力共享** —— UDP 自动发现节点，CPU/内存/GPU/NPU 实时监控，任务智能调度 + Fernet/RSA 加密传输，把闲置电脑拼成一个推理集群
- 🎨 **Glassmorphism 桌面 UI** —— 纯 Python（Pillow）与 C++（OpenGL）双实现毛玻璃 / 光晕 / 窗口动画，跨平台且热可插拔

## 🚀 已实现功能
- [x] 自定义 AI 提供者（已经实现ollama、openai、nvidia，后续继续开发其他ai支持）
- [x] 核心功能
- [x] 适配屏幕识别
- [x] 快速问答
- [x] 窗口ui管理
- [x] 统一错误处理与日志系统
- [ ] 窗口一键布局（开发中）
- [ ] 全局热键支持（开发中）
- [ ] 开机自启（开发中）
- [ ] 集群管理器（开发中）
- [ ] UI视觉特效（开发中）
- [ ] 视频剪辑器（开发中）
- [ ] 语音转字幕（规划中）
- [ ] 光标插入（规划中）
- [ ] Mac/Linux 平台适配（规划中）


## 🚀 2 分钟快速上手

### Windows 一键启动（推荐）

```powershell
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw
.\start_app.ps1          # 自动检测 Python → 装依赖 → 启动桌面界面
```

### 通用方式（Windows / Linux）

```bash
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw
pip install -r requirements.txt
python src/main.py        # 启动；加 --debug 看详细日志，--noui 走终端模式
```

> 📋 **环境要求**：Python 3.13+（需 tkinter）。首次启动前复制 `.env.example` 为 `.env` 并填入你的 AI API Key。完整安装/配置见 [📦 安装文档](docs/INSTALLATION_CN.md) 与 [⚙️ 配置文档](docs/CONFIGURATION_CN.md)。

### 一键自检

```bash
python test_main.py       # 9 项核心测试 + pip 依赖检查（缺包会给出 pip install 命令）
```

## 🎬 Demo

<!-- TODO: 录制核心操作流程的 GIF/视频后替换下方占位
建议内容：① AI 对话触发截屏+点击 ② 浏览器远程看桌面 ③ 视频剪辑导出 ④ 集群节点加入
<p align="center">
  <img src="docs/images/demo.gif" alt="Demo: AI 控制电脑全流程" width="80%" />
</p>
-->

> 🖥️ **在线 Demo**：本项目是 **桌面 GUI 应用**（CustomTkinter），需本地运行，暂无托管在线 Demo。若只想体验 Web 控制端，启动后浏览器访问 `http://localhost:15000` 即可看到控制面板与远程桌面画面。

## 🧩 功能矩阵

| 模块 | 默认端口 | 一句话 | 文档 |
|------|----------|--------|------|
| 🤖 AI 智能控制 | — | 多提供者对话 + 视觉感知 + 鼠键控制 | [AI 库使用指南](docs/ai_library_usage_ZH.md) |
| 📺 桌面监控 | 15004 | 实时屏幕/音频捕获 + 多协议推流 | [用户手册](docs/USER_MANUAL_CN.md) |
| 🎬 视频剪辑 | 15010 | Web 多轨编辑器，导出 4K | [用户手册](docs/USER_MANUAL_CN.md) |
| 🌐 API 服务 | 15002 | Web 设置 + AI 对话接口 + 插件热加载 | [配置文档](docs/CONFIGURATION_CN.md) |
| 🖱️ 网页控制端 | 15000 | 浏览器即控制台 | [用户手册](docs/USER_MANUAL_CN.md) |
| 🖥️ 局域网算力共享 | 15300-15304 | 自动发现 + 任务调度 + 加密传输 | [集群计算文档](docs/cluster_computing_ZH.md) |
| 🎨 UI 视觉特效 | — | 毛玻璃/光晕/动画（Py + C++ 双实现） | [调试与特效指南](docs/debug_mode_guide_CN.md) |

> 完整端口表、运行参数、控制台命令等详见 [⚙️ 配置文档](docs/CONFIGURATION_CN.md)。

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 语言 | Python 3.13+（核心）、C++/OpenGL（特效加速） |
| AI | OpenAI SDK、Ultralytics(YOLO)、transformers、Whisper |
| 桌面 UI | CustomTkinter、pystray、pywinstyles |
| 推流/媒体 | OpenCV、FFmpeg、WebRTC、RTMP/SRT/SRTP |
| 通信 | WebSocket、aiohttp、pexpect、plumbum |
| 数据/配置 | SQLAlchemy、Pydantic v2、pydantic-settings、PyYAML |
| 集群 | Fernet/RSA 加密、UDP 发现、psutil 资源监控 |

## 📚 文档导航

所有文档均在 [`docs/`](docs) 目录，并配有 [📄 导览索引](docs/导览.md)。快速入口：

- 📦 [安装文档](docs/INSTALLATION_CN.md) ｜ ⚙️ [配置文档](docs/CONFIGURATION_CN.md) ｜ 📖 [用户手册](docs/USER_MANUAL_CN.md)
- 🤖 [AI 库使用](docs/ai_library_usage_ZH.md) ｜ 🖥️ [集群计算](docs/cluster_computing_ZH.md) ｜ 🐛 [调试与错误码指南](docs/debug_mode_guide_CN.md)
- 🌍 English: [README](docs/README_EN.md) ｜ [Installation](docs/INSTALLATION.md) ｜ [User Manual](docs/USER_MANUAL.md)

## ❓ FAQ

<details>
<summary><b>必须用 Python 3.13 吗？</b></summary>
建议 3.11+，3.13 最佳（tkinter 行为最稳定，开发环境）。低于 3.11 不保证。
</details>

<details>
<summary><b>支持 Docker 部署吗？</b></summary>

本项目是 **桌面 GUI 应用**，主交互依赖 CustomTkinter 窗口与系统托盘，不适合整体容器化。如需在服务器上跑无界面服务，可用 `python src/main.py --noui` 终端模式 + Web 控制端（浏览器访问 15000 端口）。官方 Dockerfile 暂未提供（TODO）。
</details>

<details>
<summary><b>没有 NVIDIA 显卡能用吗？</b></summary>

可以。AI 推理默认走云端 API（NVIDIA / OpenAI），或本地 Ollama；集群 GPU 检测失败时自动降级为 CPU，仅影响本地模型推理性能。
</details>

<details>
<summary><b>AI 会乱动我的电脑吗？</b></summary>

默认 `Limited` 权限起步，鼠标移到屏幕左上角即触发安全停止。建议在虚拟机或非生产环境首次试用。详见 [配置文档](docs/CONFIGURATION_CN.md)。
</details>

<details>
<summary><b>启动报依赖缺失怎么办？</b></summary>

运行 `python test_main.py` 会自动检测 `requirements.txt` 中所有包，缺失的会直接给出 `pip install ...` 命令。
</details>

## 🤝 贡献

欢迎提 [Issue](https://github.com/chen-xin-Liam/powerful-claw/issues) 反馈问题或 [Discussions](https://github.com/chen-xin-Liam/powerful-claw/discussions) 讨论功能。

开发前请阅读 [调试与错误码指南](docs/debug_mode_guide_CN.md)（项目已统一异常体系与错误码分段，便于定位问题）。

```bash
# 代码规范检查
pip install flake8 && flake8 src/

# 运行测试
python test_main.py
```

感谢所有贡献者：

[![Contributors](https://contrib.rocks/image?repo=chen-xin-Liam/powerful-claw)](https://github.com/chen-xin-Liam/powerful-claw/graphs/contributors)

## 📄 License

本项目采用 **GPL-3.0 + 附加禁止商业使用条款**。详见 [LICENSE](LICENSE)。

## 🌟 Star History

<a href="https://www.star-history.com/?repos=chen-xin-Liam%2Fpowerful-claw&type=date&legend=bottom-right">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=chen-xin-Liam/powerful-claw&type=date&theme=dark&legend=bottom-right&sealed_token=YFwFvLj13TKlFm-6F2v-wK3CccWetfpWS4UxnJ9D60Q1E0QUwLTvlh5FXnpfvPl1c15Ff4xjJb_GQ2wf727u_u6pbsgElr9z2q6h1_13yMPif_leAh2hOgBv-l84SdghyCcCWLzxO23V0H09ajX6NidIKg5VSovfolqbK1mZW7yRAJondULB2e_XK86L" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=chen-xin-Liam/powerful-claw&type=date&legend=bottom-right&sealed_token=YFwFvLj13TKlFm-6F2v-wK3CccWetfpWS4UxnJ9D60Q1E0QUwLTvlh5FXnpfvPl1c15Ff4xjJb_GQ2wf727u_u6pbsgElr9z2q6h1_13yMPif_leAh2hOgBv-l84SdghyCcCWLzxO23V0H09ajX6NidIKg5VSovfolqbK1mZW7yRAJondULB2e_XK86L" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=chen-xin-Liam/powerful-claw&type=date&legend=bottom-right&sealed_token=YFwFvLj13TKlFm-6F2v-wK3CccWetfpWS4UxnJ9D60Q1E0QUwLTvlh5FXnpfvPl1c15Ff4xjJb_GQ2wf727u_u6pbsgElr9z2q6h1_13yMPif_leAh2hOgBv-l84SdghyCcCWLzxO23V0H09ajX6NidIKg5VSovfolqbK1mZW7yRAJondULB2e_XK86L" />
 </picture>
</a>

---

<!-- 📌 仓库 SEO 建议（需在 GitHub 仓库 Web 界面手动设置，README 无法直接配置）:
- About Description: "让 AI 真正看见并操作你的电脑 —— 多模态大模型驱动的桌面自动化 Agent，集成屏幕推流、视频剪辑、局域网算力共享"
- Topics 标签（3-5 个）: python  ai-agent  desktop-automation  llm  computer-vision
- Releases: 发布首个 Release 以获得更好的曝光
-->

⭐ 如果这个项目对你有帮助，请给它一个 Star！
