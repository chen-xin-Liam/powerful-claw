# 🤖 powerful-claw
<div align="center">
<!-- TODO: 替换为真实 Logo（建议 256×256 PNG/SVG，放 docs/images/logo.png）
<img src="docs/images/logo.png" alt="powerful-claw" width="200" height="200" />
-->

#### ⚠️ **当前状态：开发中 / WIP，存在已知 Bug，请勿用于生产环境**
#### ⚠️ **GitHub为本项目唯一主仓库，其他平台均为镜像，不建议直接提交修改**

[GitHub主仓库]: https://github.com/chen-xin-Liam/powerful-claw

**让 AI 看见并操作本地电脑** —— 开源桌面自动化 Agent 控制中枢。
可以串联多模态大模型、屏幕视觉感知、键鼠自动化；附带桌面推流、简易视频剪辑、局域网算力节点调度等配套模块。

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-success.svg?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/chen-xin-Liam/powerful-claw?style=social)](https://github.com/chen-xin-Liam/powerful-claw/stargazers)
[![bilibili](https://img.shields.io/badge/bilibili-%E6%95%B0%E7%A7%91%E6%99%BA%E6%98%9F-00A1D6.svg?logo=bilibili&logoColor=white)](https://space.bilibili.com/3493111196027162)
<!-- TODO: 启用 CI 后替换为真实构建/覆盖率徽章
[![Build](https://img.shields.io/github/actions/workflow/status/chen-xin-Liam/powerful-claw/.github/workflows/ci.yml?branch=main&label=build)](...)
[![Coverage](https://img.shields.io/codecov/c/github/chen-xin-Liam/powerful-claw.svg)](...)
-->
</div>

---

> 💡 项目定位：
> 很多AI Agent项目只停留在对话。本项目尝试构建一套端侧本地Agent，**读取屏幕画面、理解界面内容，调用键鼠完成电脑上的操作任务**。
> 桌面推流、视频剪辑、局域网算力集群属于附属配套模块，部分仍在开发中。

## ✨ 项目特点
- 🧠 **端侧桌面AI Agent**：对接多模态大模型（Ollama / OpenAI兼容接口 / NVIDIA API），基于YOLO做屏幕目标检测，实现截图理解、键鼠自动化；内置四级权限模型（None/View/Limited/Full）控制Agent操作权限，降低误操作风险。
- 📺 **桌面实时推流模块**：帧率1–30FPS可调，支持RTMP/SRT/WebRTC多协议音视频推流；使用帧差压缩+分块编码降低传输带宽，浏览器可直接访问查看桌面。
- 🎬 **内置Web视频剪辑器（基础实现）**：多轨时间轴、调色滤镜、SRT/ASS字幕、语音转字幕，支持导出 MP4/MOV/GIF/WebM（1080P/2K/4K）。
- 🌐 **局域网算力调度（WIP）**：UDP自动发现内网节点，采集CPU/内存/GPU/NPU负载，支持任务调度，Fernet/RSA加密传输，可将多台闲置机器组成推理集群。
- 🎨 **可插拔桌面UI**：两套渲染实现，Python(Pillow) 轻量版本 + C++/OpenGL 高性能毛玻璃、窗口动画实现，跨平台可切换。
- 🛠️ **原生Python主体**：架构轻量化，便于阅读源码、二次开发与本地调试。

## 📚 技术栈 / Tech Stack
| 模块 | 技术 / 语言 | 说明 |
|------|------------|------|
| AI Agent | Python 3.13+ | 多模态大模型驱动，可接入 Ollama/OpenAI/NVIDIA 等模型服务 |
| 视觉感知 | Python + YOLOv8 | 屏幕截图、界面目标检测，适配高DPI显示器 |
| 桌面控制 | Python (pyautogui/keyboard) | 跨平台鼠标键盘自动化，四级权限控制 |
| 视频推流 | Python + FFmpeg | RTMP/SRT/WebRTC 多协议，帧差压缩与分块编码 |
| UI 界面 | CustomTkinter + C++/OpenGL | 毛玻璃/光晕窗口动画，双实现可插拔 |
| 集群计算 | Python + UDP/加密 | 局域网节点发现、任务调度，Fernet/RSA加密传输 |
| 日志/错误 | Loguru/Rich | 统一错误码、分级日志，全链路Debug追踪 |
| 节点化数学引擎 | C++17 + cppyy嵌入Python | 44节点运算单元（算术/三角/矩阵LU/统计），可降级到纯Python运行 |

## 🚀 已实现功能
- [x] 多AI后端接入（Ollama、OpenAI兼容API、NVIDIA），易于扩展新增服务商
- [x] 屏幕截图 + YOLO目标检测视觉识别
- [x] 鼠标、键盘自动化控制
- [x] 桌面实时推流 RTMP/SRT/WebRTC
- [x] 局域网节点发现与硬件监控
- [x] 统一日志、异常错误处理体系
- [x] 基础窗口UI管理
- [x] 问答交互入口

## 🐛 已知问题 & 未完成模块
> 这部分是重点，坦诚写出限制，会大幅增加开发者信任感
- 高DPI显示器下屏幕坐标识别存在偏差
- 切换显示器分辨率时，偶发画面闪烁
- 目前仅在 Windows10/11 完成基础验证
- 修改主题设置有概率卡死UI
- 局域网算力调度：节点调度逻辑尚未完成
- 视频剪辑模块：仅完成基础架构，功能不完善

## 🛠️ 快速开始
```bash
# 1. 克隆项目
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw
# 2. 安装依赖
pip install -r requirements.txt
# 3. 运行主程序
python src/main.py
# 4. 访问 WebUI（推流+剪辑）
# 浏览器打开：http://localhost:8080
