# 配置指南

## 环境变量 

| 变量名 | 描述 | 默认值 | 是否必需 |
|----------|-------------|---------------|----------|
| NVIDIA_API_KEY | 你的 NVIDIA API 密钥 | - | 是 |
| NVIDIA_BASE_URL | NVIDIA API 基础 URL | https://integrate.api.nvidia.com/v1 | 否 |
| MODEL_NAME | 使用的 AI 模型 | z-ai/glm4.7 | 否 |
| TEMPERATURE | AI 生成的 temperature 参数 | 1.0 | 否 |
| TOP_P | AI 生成的 top_p 参数 | 1.0 | 否 |
| MAX_TOKENS | 每次响应的最大 token 数 | 16384 | 否 |

## 配置文件

你也可以在项目根目录创建 `.env` 文件：

```env
NVIDIA_API_KEY=your_api_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
MODEL_NAME=z-ai/glm4.7
TEMPERATURE=1.0
TOP_P=1.0
MAX_TOKENS=16384
```

## AI 模型参数

- **temperature**: 控制随机性（0 = 确定性，2 = 非常随机）
- **top_p**: 核采样参数（0.1 = 聚焦，1.0 = 多样化）
- **max_tokens**: 响应的最大长度

## 权限级别

| 级别 | 描述 | 允许的操作 |
|-------|-------------|-------------------|
| None | 仅查看模式 | 无 |
| View | 查看模式 | 无 |
| Limited | 基础控制 | 鼠标移动、点击、键盘输入 |
| Full | 完全控制 | 所有操作，包括热键、窗口控制 |

## 模式

- **Chat Mode**: 与 AI 的常规对话，无系统控制
- **Control Mode**: AI 可以生成并执行系统操作