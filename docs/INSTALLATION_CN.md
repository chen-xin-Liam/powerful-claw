# 安装指南

## 前置要求

- Python 3.8 或更高版本
- NVIDIA API 密钥（从 NVIDIA 开发者门户获取）
- Windows/macOS/Linux 操作系统

## 安装步骤

### 1. 克隆仓库

```bash
git clone <repository-url>
cd ai-computer-control
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