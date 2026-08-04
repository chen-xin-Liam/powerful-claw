"""
Python封装模块 - 调用GL Effects DLL
使用ctypes实现与C/C++ DLL的交互
"""

import ctypes
import os
import platform
from ctypes import c_float, c_int, c_uint32, c_bool, c_void_p, c_char_p, POINTER, Structure


class GLColor(Structure):
    """颜色结构"""
    _fields_ = [
        ("r", c_float),
        ("g", c_float),
        ("b", c_float),
        ("a", c_float)
    ]
    
    def __init__(self, r=0.0, g=0.0, b=0.0, a=1.0):
        super().__init__(r, g, b, a)
    
    def __repr__(self):
        return f"GLColor(r={self.r:.2f}, g={self.g:.2f}, b={self.b:.2f}, a={self.a:.2f})"


class GlassEffectParams(Structure):
    """毛玻璃效果参数"""
    _fields_ = [
        ("blur_radius", c_float),
        ("opacity", c_float),
        ("tint_color", GLColor),
        ("border_width", c_float),
        ("border_color", GLColor),
        ("enable_border_sharp", c_bool)
    ]
    
    def __init__(self):
        super().__init__(
            blur_radius=20.0,
            opacity=0.8,
            tint_color=GLColor(0.1, 0.1, 0.15, 0.6),
            border_width=1.0,
            border_color=GLColor(0.9, 0.9, 0.95, 0.8),
            enable_border_sharp=True
        )


class GlowEffectParams(Structure):
    """光晕效果参数"""
    _fields_ = [
        ("glow_color", GLColor),
        ("glow_intensity", c_float),
        ("glow_radius", c_float),
        ("shadow_color", GLColor),
        ("shadow_offset_x", c_float),
        ("shadow_offset_y", c_float),
        ("shadow_blur", c_float)
    ]
    
    def __init__(self):
        super().__init__(
            glow_color=GLColor(0.2, 0.5, 1.0, 0.6),
            glow_intensity=0.8,
            glow_radius=15.0,
            shadow_color=GLColor(0.0, 0.0, 0.0, 0.3),
            shadow_offset_x=2.0,
            shadow_offset_y=4.0,
            shadow_blur=10.0
        )


class WindowAnimationParams(Structure):
    """窗口动画参数"""
    _fields_ = [
        ("target_width", c_int),
        ("target_height", c_int),
        ("target_x", c_int),
        ("target_y", c_int),
        ("duration", c_float),
        ("easing_type", c_int)
    ]
    
    def __init__(self, target_width=0, target_height=0, target_x=0, target_y=0, duration=0.3, easing_type=1):
        super().__init__(target_width, target_height, target_x, target_y, duration, easing_type)


class GLEffectsError:
    """错误码枚举"""
    SUCCESS = 0
    ERROR_INVALID_PARAM = -1
    ERROR_INIT_FAILED = -2
    ERROR_RENDER_FAILED = -3
    ERROR_MEMORY = -4
    ERROR_UNSUPPORTED = -5


class GLEffects:
    """GL视觉特效封装类"""
    
    def __init__(self):
        self._dll = None
        self._is_initialized = False
        
    def _load_dll(self):
        """加载DLL文件"""
        if self._dll is not None:
            return True
        
        system = platform.system()
        if system == "Windows":
            dll_name = "gl_effects.dll"
        elif system == "Linux":
            dll_name = "libgl_effects.so"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
        
        # 搜索DLL路径
        search_paths = [
            os.path.dirname(__file__),
            os.path.join(os.path.dirname(__file__), "..", "..", ".."),
            os.getcwd(),
            os.environ.get("PATH", "").split(os.pathsep)
        ]
        
        dll_path = None
        for path in search_paths:
            full_path = os.path.join(path, dll_name)
            if os.path.exists(full_path):
                dll_path = full_path
                break
        
        if dll_path is None:
            raise FileNotFoundError(f"无法找到 {dll_name}。请确保DLL文件已编译并放置在正确位置。")
        
        try:
            self._dll = ctypes.CDLL(dll_path)
            self._setup_functions()
            return True
        except Exception as e:
            raise RuntimeError(f"加载DLL失败: {e}")
    
    def _setup_functions(self):
        """设置DLL函数原型"""
        # gl_effects_get_version
        self._dll.gl_effects_get_version.argtypes = []
        self._dll.gl_effects_get_version.restype = c_char_p
        
        # gl_effects_init
        self._dll.gl_effects_init.argtypes = [c_uint32, c_uint32, c_void_p]
        self._dll.gl_effects_init.restype = c_int
        
        # gl_effects_shutdown
        self._dll.gl_effects_shutdown.argtypes = []
        self._dll.gl_effects_shutdown.restype = None
        
        # gl_effects_set_transparency
        self._dll.gl_effects_set_transparency.argtypes = [c_float]
        self._dll.gl_effects_set_transparency.restype = c_int
        
        # gl_effects_get_transparency
        self._dll.gl_effects_get_transparency.argtypes = []
        self._dll.gl_effects_get_transparency.restype = c_float
        
        # gl_effects_enable_glass_effect
        self._dll.gl_effects_enable_glass_effect.argtypes = [c_bool]
        self._dll.gl_effects_enable_glass_effect.restype = c_int
        
        # gl_effects_is_glass_enabled
        self._dll.gl_effects_is_glass_enabled.argtypes = []
        self._dll.gl_effects_is_glass_enabled.restype = c_bool
        
        # gl_effects_set_glass_params
        self._dll.gl_effects_set_glass_params.argtypes = [POINTER(GlassEffectParams)]
        self._dll.gl_effects_set_glass_params.restype = c_int
        
        # gl_effects_get_glass_params
        self._dll.gl_effects_get_glass_params.argtypes = [POINTER(GlassEffectParams)]
        self._dll.gl_effects_get_glass_params.restype = c_int
        
        # gl_effects_enable_glow_effect
        self._dll.gl_effects_enable_glow_effect.argtypes = [c_bool]
        self._dll.gl_effects_enable_glow_effect.restype = c_int
        
        # gl_effects_is_glow_enabled
        self._dll.gl_effects_is_glow_enabled.argtypes = []
        self._dll.gl_effects_is_glow_enabled.restype = c_bool
        
        # gl_effects_set_glow_params
        self._dll.gl_effects_set_glow_params.argtypes = [POINTER(GlowEffectParams)]
        self._dll.gl_effects_set_glow_params.restype = c_int
        
        # gl_effects_get_glow_params
        self._dll.gl_effects_get_glow_params.argtypes = [POINTER(GlowEffectParams)]
        self._dll.gl_effects_get_glow_params.restype = c_int
        
        # gl_effects_start_window_animation
        self._dll.gl_effects_start_window_animation.argtypes = [POINTER(WindowAnimationParams)]
        self._dll.gl_effects_start_window_animation.restype = c_int
        
        # gl_effects_is_animating
        self._dll.gl_effects_is_animating.argtypes = []
        self._dll.gl_effects_is_animating.restype = c_bool
        
        # gl_effects_render
        self._dll.gl_effects_render.argtypes = []
        self._dll.gl_effects_render.restype = c_int
        
        # gl_effects_set_log_callback
        self._dll.gl_effects_set_log_callback.argtypes = [ctypes.CFUNCTYPE(None, c_char_p)]
        self._dll.gl_effects_set_log_callback.restype = None
        
        # gl_effects_get_error_message
        self._dll.gl_effects_get_error_message.argtypes = [c_int]
        self._dll.gl_effects_get_error_message.restype = c_char_p
    
    def _check_error(self, result, func_name):
        """检查错误码"""
        if result != GLEffectsError.SUCCESS:
            msg = self._dll.gl_effects_get_error_message(result).decode('utf-8')
            raise RuntimeError(f"{func_name} failed: {msg}")
    
    def init(self, width, height, native_window=None):
        """初始化特效引擎"""
        self._load_dll()
        result = self._dll.gl_effects_init(width, height, native_window)
        self._check_error(result, "gl_effects_init")
        self._is_initialized = True
        
        # 设置日志回调
        def log_callback(message):
            print(f"[GLEffects] {message.decode('utf-8')}")
        
        c_log_callback = ctypes.CFUNCTYPE(None, c_char_p)(log_callback)
        self._dll.gl_effects_set_log_callback(c_log_callback)
        
        return True
    
    def shutdown(self):
        """关闭特效引擎"""
        if self._dll and self._is_initialized:
            self._dll.gl_effects_shutdown()
            self._is_initialized = False
    
    def set_transparency(self, alpha):
        """设置透明度 (0.0-1.0)"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        result = self._dll.gl_effects_set_transparency(c_float(alpha))
        self._check_error(result, "gl_effects_set_transparency")
    
    def get_transparency(self):
        """获取当前透明度"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        return self._dll.gl_effects_get_transparency()
    
    def enable_glass_effect(self, enable):
        """启用/禁用毛玻璃效果"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        result = self._dll.gl_effects_enable_glass_effect(c_bool(enable))
        self._check_error(result, "gl_effects_enable_glass_effect")
    
    def is_glass_enabled(self):
        """检查毛玻璃效果是否启用"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        return self._dll.gl_effects_is_glass_enabled()
    
    def set_glass_params(self, params):
        """设置毛玻璃效果参数"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        result = self._dll.gl_effects_set_glass_params(ctypes.byref(params))
        self._check_error(result, "gl_effects_set_glass_params")
    
    def get_glass_params(self):
        """获取毛玻璃效果参数"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        params = GlassEffectParams()
        result = self._dll.gl_effects_get_glass_params(ctypes.byref(params))
        self._check_error(result, "gl_effects_get_glass_params")
        return params
    
    def enable_glow_effect(self, enable):
        """启用/禁用边框光晕效果"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        result = self._dll.gl_effects_enable_glow_effect(c_bool(enable))
        self._check_error(result, "gl_effects_enable_glow_effect")
    
    def is_glow_enabled(self):
        """检查边框光晕效果是否启用"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        return self._dll.gl_effects_is_glow_enabled()
    
    def set_glow_params(self, params):
        """设置边框光晕效果参数"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        result = self._dll.gl_effects_set_glow_params(ctypes.byref(params))
        self._check_error(result, "gl_effects_set_glow_params")
    
    def get_glow_params(self):
        """获取边框光晕效果参数"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        params = GlowEffectParams()
        result = self._dll.gl_effects_get_glow_params(ctypes.byref(params))
        self._check_error(result, "gl_effects_get_glow_params")
        return params
    
    def start_window_animation(self, params):
        """开始窗口动画"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        result = self._dll.gl_effects_start_window_animation(ctypes.byref(params))
        self._check_error(result, "gl_effects_start_window_animation")
    
    def is_animating(self):
        """检查是否正在播放动画"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        return self._dll.gl_effects_is_animating()
    
    def render(self):
        """执行渲染"""
        if not self._is_initialized:
            raise RuntimeError("GLEffects尚未初始化")
        result = self._dll.gl_effects_render()
        self._check_error(result, "gl_effects_render")
    
    def get_version(self):
        """获取版本号"""
        self._load_dll()
        return self._dll.gl_effects_get_version().decode('utf-8')
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# 示例用法
if __name__ == "__main__":
    print("GLEffects Python 封装测试")
    
    try:
        effects = GLEffects()
        print(f"版本: {effects.get_version()}")
        
        # 初始化
        effects.init(800, 600)
        print("初始化成功")
        
        # 设置透明度
        effects.set_transparency(0.8)
        print(f"透明度: {effects.get_transparency()}")
        
        # 启用毛玻璃效果
        effects.enable_glass_effect(True)
        print(f"毛玻璃效果: {effects.is_glass_enabled()}")
        
        # 设置毛玻璃参数
        glass_params = GlassEffectParams()
        glass_params.blur_radius = 15.0
        glass_params.opacity = 0.7
        glass_params.tint_color = GLColor(0.15, 0.15, 0.2, 0.7)
        effects.set_glass_params(glass_params)
        print("毛玻璃参数已设置")
        
        # 启用光晕效果
        effects.enable_glow_effect(True)
        print(f"光晕效果: {effects.is_glow_enabled()}")
        
        # 设置光晕参数
        glow_params = GlowEffectParams()
        glow_params.glow_color = GLColor(0.3, 0.6, 1.0, 0.7)
        glow_params.glow_intensity = 0.9
        effects.set_glow_params(glow_params)
        print("光晕参数已设置")
        
        # 渲染
        effects.render()
        print("渲染成功")
        
        # 关闭
        effects.shutdown()
        print("已关闭")
        
    except Exception as e:
        print(f"错误: {e}")