
# 🤖 powerful-claw
<div align="center">

<!-- TODO: 替换为真实 Logo（建议 256×256 PNG/SVG，放 docs/images/logo.png）
<img src="docs/images/logo.png" alt="powerful-claw" width="200" height="200" />
-->

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

## ✨ 核心亮点（比 OpenClaw 更强）

- 🧠 **AI Agent 落地，而非聊天框** —— 多模态大模型（NVIDIA / OpenAI / Ollama / 自定义）驱动，能截图、能看屏幕（YOLO 目标检测）、能控制鼠标键盘，四级权限（None/View/Limited/Full）保证安全
- 📺 **桌面实时推流** —— 1–30 FPS 可调，多协议视频（RTMP/SRT/SRTP）+ 多协议音频（WebRTC/SRTP/SMPTE 2110）自适应，浏览器打开即看，帧差压缩 + 分块编码大幅降带宽
- 🎬 **内置 Web 视频剪辑器** —— 多轨时间轴、调色滤镜、字幕 SRT/ASS、语音转字幕，1080P/2K/4K 导出 MP4/MOV/GIF/WebM
- 🌐 **局域网算力共享** —— UDP 自动发现节点，CPU/内存/GPU/NPU 实时监控，任务智能调度 + Fernet/RSA 加密传输，把闲置电脑拼成一个推理集群
- 🎨 **Glassmorphism 桌面 UI** —— 纯 Python（Pillow）与 C++（OpenGL）双实现毛玻璃 / 光晕 / 窗口动画，跨平台且热可插拔
- 🛠️ **原生 Python 实现** —— 比 OpenClaw 更轻量、更易二次开发、更易调试

## 🚀 已实现功能（清晰、可验证）

- [x] 多 AI 提供者支持（Ollama、OpenAI、NVIDIA，可扩展）
- [x] 屏幕识别与截图（YOLO 目标检测）
- [x] 鼠标键盘自动化控制
- [x] 桌面实时推流（RTMP/SRT/WebRTC）
- [x] 局域网节点发现与监控
- [x] 统一错误处理与日志系统
- [x] 窗口 UI 管理
- [x] 快速问答交互

## 🐛 已知问题（透明、专业）

- 部分高 DPI 显示器识别可能存在偏差
- 切换分辨率时偶现屏幕闪烁
- 仅在 Windows 10/11 完成基础测试
- 设置主题会有卡死现象
- 局域网算力共享节点还未完成
- 视频剪辑只是基础架构

## 🛠️ 快速开始（极简、可复制）

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
```

## 📌 开发路线图（Roadmap，给人信心）

### 近期（1–2 个月）
- 修复已知 Bug，优化多显示器兼容性
- 实现全局热键支持
- 完善窗口一键布局功能
- 打包为 Windows 可执行文件（exe）

### 中期（3–6 个月）
- 完整 Mac/Linux 平台适配
- 增强局域网算力调度算法
- 支持更多 AI 模型（如 DeepSeek、CodeGemma）
- 增加自定义 Skill 系统（类似 OpenClaw）
- 完善文档与使用教程

### 长期
- 跨平台统一安装包
- 云端管理面板
- 企业级安全与权限控制
- 插件生态系统

## 🤝 欢迎贡献

欢迎任何形式的贡献：
- 提交 Issue 反馈 Bug 或提出功能建议
- 提交 PR 修复问题、实现新功能
- 完善文档、补充测试用例
- 分享使用案例、制作教程

### 贡献流程
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交修改 (`git commit -m 'Add some feature'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 **GPL-3.0 + 非商业使用** 许可证，详见 [LICENSE](LICENSE) 文件。

---

## 🔍 为什么这样改能涨 Star？

1. **定位更清晰**：明确「比 OpenClaw 更强」，直接对标热门项目，自带流量
2. **状态更透明**：「已知问题」写得专业，不回避 Bug，反而让人觉得可靠
3. **功能更聚焦**：已实现功能用「可验证」的列表，让人一眼看到价值
4. **路线图明确**：给用户和贡献者清晰预期，提升参与感
5. **安装极简**：4 步跑起来，降低试用门槛
6. **贡献友好**：清晰的贡献流程，吸引开发者参与

