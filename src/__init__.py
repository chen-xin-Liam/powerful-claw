"""AI电脑控制 顶层包

注意：包初始化保持轻量，禁止在此 eager import 服务/UI 等重模块（openai、
requests、pydantic、pyautogui 等会显著拖慢冷启动）。需要时请使用完整路径导入，
例如 ``from src.services.ai_service import AIService``。
"""

__all__ = [
    "settings",
    "AIService",
    "SystemController",
    "VisionCapture",
    "setup_logger",
    "ResponseParser",
]
