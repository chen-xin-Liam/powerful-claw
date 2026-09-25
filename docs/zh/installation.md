# 安装指南

## 前置要求

- Python 3.13+（3.13 最佳，3.11+ 可运行，需 tkinter）
- AI 服务 API 密钥（NVIDIA / OpenAI / Ollama 任选其一）
- Windows（推荐）/ Linux 操作系统

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 设置环境变量

```bash
# Windows (PowerShell)
$env:NVIDIA_API_KEY="your_api_key_here"

# macOS/Linux
export NVIDIA_API_KEY="your_api_key_here"
```

或者创建 `.env` 文件：

```env
NVIDIA_API_KEY=your_api_key_here
```

### 5. 启动应用程序

```bash
python src/ui/customtkinter_app.py
```

或者使用主入口：

```bash
python src/main.py
```

## 故障排除

### 缺少 NVIDIA_API_KEY

如果您看到"NVIDIA_API_KEY environment variable not set"错误信息，请确保您已正确设置环境变量或创建了 `.env` 文件。

### PyAutoGUI 问题

在某些系统上，您可能需要安装额外的依赖：

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk python3-dev

# macOS
brew install pyobjc
```

### 摄像头访问问题

请确保您的摄像头未被其他应用程序占用，并且您已授予终端/IDE 摄像头访问权限。

## 开发环境设置

```bash
pip install -e .
pip install pytest pytest-mock
```

运行测试：

```bash
pytest tests/
```

## 项目结构

```
powerful-claw/
├── src/                          # 源代码目录
│   ├── config/                   # 配置管理
│   │   ├── ai_providers.py       # AI 提供者配置
│   │   ├── providers_config.json # 提供者配置数据
│   │   └── settings.py           # 全局设置
│   ├── services/                 # 服务层
│   │   ├── ai_service.py         # AI 服务接口
│   │   ├── ai_agent.py           # AI 代理系统
│   │   ├── tool_registry.py      # 工具注册表
│   │   ├── screen_monitor.py     # 桌面监控服务
│   │   ├── video_editor.py       # 视频剪辑服务
│   │   ├── api_server.py         # API 服务器
│   │   ├── websocket_server.py   # WebSocket 服务器
│   │   ├── local_model_service.py# 本地模型服务
│   │   └── cluster/              # 集群服务模块
│   │       ├── __init__.py       # 集群管理器
│   │       ├── gpu_detector.py   # GPU 资源检测
│   │       ├── system_monitor.py # 系统资源监控
│   │       ├── lan_node.py       # 局域网节点通信
│   │       ├── task_scheduler.py # 任务调度器
│   │       ├── secure_transport.py# 加密传输
│   │       ├── cluster_monitor.py# 集群监控
│   │       ├── distributed_inference.py # 分布式推理
│   │       └── cluster_api.py    # 集群 API 服务
│   ├── system/                   # 系统控制
│   │   ├── controller.py         # 鼠标键盘控制
│   │   └── vision.py             # 视觉处理
│   ├── ui/                       # 用户界面
│   │   ├── customtkinter_app.py  # CustomTkinter 桌面界面
│   │   ├── theme_settings_panel.py # 主题设置面板
│   │   ├── splash_screen.py      # 启动画面
│   │   └── effects/              # UI 视觉特效模块
│   │       ├── __init__.py       # 模块入口
│   │       ├── py_effects.py     # 纯 Python 实现
│   │       ├── gl_effects.py     # C/C++ 实现（OpenGL 加速）
│   │       ├── gl_effects.h      # C 接口头文件
│   │       ├── CMakeLists.txt    # CMake 编译配置
│   │       └── build_effects.py  # 编译脚本
│   ├── utils/                    # 工具模块
│   │   ├── image_processor.py    # 图像处理
│   │   ├── logger.py             # 日志记录
│   │   ├── markdown_renderer.py  # Markdown 渲染
│   │   ├── parser.py             # 响应解析
│   │   ├── error_codes.py        # 错误码定义
│   │   ├── errors.py             # 统一异常体系
│   │   └── yolo_detector.py      # YOLO 检测器
│   ├── main.py                   # 主入口
│   └── __init__.py
├── docs/                         # 文档目录
├── .env.example                  # 环境变量示例
├── requirements.txt              # Python 依赖
├── start_app.ps1                 # PowerShell 一键启动脚本
├── test_main.py                  # 功能自检脚本
└── README.md                     # 项目说明
```

## 一键启动（Windows）

除手动安装外，Windows 用户可使用一键脚本：

```powershell
.\start_app.ps1
```

脚本会自动：① 检测 Python 环境 → ② 安装依赖 → ③ 启动 CustomTkinter 桌面界面。