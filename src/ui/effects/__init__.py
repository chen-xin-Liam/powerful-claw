"""
AIclaw UI视觉特效模块
提供毛玻璃效果、透明度控制、边框光晕等视觉特效

本模块提供两种实现方式：
1. py_effects.py - 纯Python实现，使用Pillow进行图像处理，无需编译
2. gl_effects_python.py + gl_effects.cpp - C/C++实现，使用OpenGL加速，需要编译DLL

默认使用纯Python实现，如需更高性能可编译C/C++版本
"""

# 使用纯Python实现（无需编译）
from .py_effects import GLEffects, GLColor, GlassEffectParams, GlowEffectParams, WindowAnimationParams

__all__ = [
    "GLEffects",
    "GLColor",
    "GlassEffectParams",
    "GlowEffectParams",
    "WindowAnimationParams"
]