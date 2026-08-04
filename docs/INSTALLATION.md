# Installation Guide

## Prerequisites

- Python 3.8 or higher
- NVIDIA API Key (get from NVIDIA developer portal)
- Windows/macOS/Linux operating system

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ai-computer-control
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

```bash
# Windows (PowerShell)
$env:NVIDIA_API_KEY="your_api_key_here"

# macOS/Linux
export NVIDIA_API_KEY="your_api_key_here"
```

Or create a `.env` file:

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

## Troubleshooting

### Missing NVIDIA_API_KEY

If you see "NVIDIA_API_KEY environment variable not set", make sure you've set the environment variable correctly or created a `.env` file.

### PyAutoGUI Issues

On some systems, you may need to install additional dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk python3-dev

# macOS
brew install pyobjc
```

### Camera Access Issues

Ensure your camera is not being used by another application and that you've granted camera permissions to your terminal/IDE.

## Development Setup

```bash
pip install -e .
pip install pytest pytest-mock
```

Run tests:

```bash
pytest tests/
```