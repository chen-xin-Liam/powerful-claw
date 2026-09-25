# Configuration Guide

## Environment Variables

| Variable | Description | Default Value | Required |
|----------|-------------|---------------|----------|
| NVIDIA_API_KEY | Your NVIDIA API key | - | Yes |
| NVIDIA_BASE_URL | Base URL for NVIDIA API | https://integrate.api.nvidia.com/v1 | No |
| MODEL_NAME | AI model to use | z-ai/glm4.7 | No |
| TEMPERATURE | Temperature parameter for AI generation | 1.0 | No |
| TOP_P | Top-p parameter for AI generation | 1.0 | No |
| MAX_TOKENS | Maximum tokens per response | 16384 | No |

## Configuration File

You can also create a `.env` file in the project root:

```env
NVIDIA_API_KEY=your_api_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
MODEL_NAME=z-ai/glm4.7
TEMPERATURE=1.0
TOP_P=1.0
MAX_TOKENS=16384
```

## AI Model Parameters

- **temperature**: Controls randomness (0 = deterministic, 2 = very random)
- **top_p**: Nucleus sampling parameter (0.1 = focused, 1.0 = diverse)
- **max_tokens**: Maximum length of the response

## Permission Levels

| Level | Description | Allowed Operations |
|-------|-------------|-------------------|
| None | View only mode | None |
| View | View mode | None |
| Limited | Basic control | Mouse move, click, keyboard input |
| Full | Complete control | All operations including hotkeys, window control |

## Modes

- **Chat Mode**: Regular conversation with AI, no system control
- **Control Mode**: AI can generate and execute system operations