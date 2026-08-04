"""
纯Python实现的UI视觉特效模块
提供毛玻璃效果、透明度控制、边框光晕等视觉特效
使用Pillow进行图像处理
"""

import math
import time
from typing import Tuple, Optional

try:
    from PIL import Image, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class GLColor:
    """颜色结构"""
    
    def __init__(self, r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0):
        self.r = max(0.0, min(1.0, r))
        self.g = max(0.0, min(1.0, g))
        self.b = max(0.0, min(1.0, b))
        self.a = max(0.0, min(1.0, a))
    
    def to_rgba(self) -> Tuple[int, int, int, int]:
        """转换为RGBA整数元组"""
        return (
            int(self.r * 255),
            int(self.g * 255),
            int(self.b * 255),
            int(self.a * 255)
        )
    
    def __repr__(self):
        return f"GLColor(r={self.r:.2f}, g={self.g:.2f}, b={self.b:.2f}, a={self.a:.2f})"


class GlassEffectParams:
    """毛玻璃效果参数"""
    
    def __init__(self):
        self.blur_radius: float = 20.0
        self.opacity: float = 0.8
        self.tint_color: GLColor = GLColor(0.1, 0.1, 0.15, 0.6)
        self.border_width: float = 1.0
        self.border_color: GLColor = GLColor(0.9, 0.9, 0.95, 0.8)
        self.enable_border_sharp: bool = True


class GlowEffectParams:
    """光晕效果参数"""
    
    def __init__(self):
        self.glow_color: GLColor = GLColor(0.2, 0.5, 1.0, 0.6)
        self.glow_intensity: float = 0.8
        self.glow_radius: float = 15.0
        self.shadow_color: GLColor = GLColor(0.0, 0.0, 0.0, 0.3)
        self.shadow_offset_x: float = 2.0
        self.shadow_offset_y: float = 4.0
        self.shadow_blur: float = 10.0


class WindowAnimationParams:
    """窗口动画参数"""
    
    def __init__(self, target_width: int = 0, target_height: int = 0, 
                 target_x: int = 0, target_y: int = 0, 
                 duration: float = 0.3, easing_type: int = 1):
        self.target_width = target_width
        self.target_height = target_height
        self.target_x = target_x
        self.target_y = target_y
        self.duration = duration
        self.easing_type = easing_type


class GLEffectsError:
    """错误码枚举"""
    SUCCESS = 0
    ERROR_INVALID_PARAM = -1
    ERROR_INIT_FAILED = -2
    ERROR_RENDER_FAILED = -3
    ERROR_MEMORY = -4
    ERROR_UNSUPPORTED = -5


class GLEffects:
    """GL视觉特效封装类 - 纯Python实现"""
    
    VERSION = "1.0.0"
    
    def __init__(self):
        self._width = 0
        self._height = 0
        self._native_window = None
        self._is_initialized = False
        
        # 效果参数
        self._transparency = 1.0
        self._glass_enabled = False
        self._glass_params = GlassEffectParams()
        self._glow_enabled = False
        self._glow_params = GlowEffectParams()
        
        # 动画状态
        self._is_animating = False
        self._anim_params = None
        self._anim_progress = 0.0
        self._anim_start_time = 0.0
        
        # 性能统计
        self._current_frame = 0
        self._last_time = 0.0
        self._frame_time_accum = 0.0
        self._fps_frame_count = 0
        self._current_fps = 0.0
        
        # 日志回调
        self._log_callback = None
    
    def _log(self, message: str):
        """输出日志"""
        if self._log_callback:
            self._log_callback(message)
        else:
            print(f"[GLEffects] {message}")
    
    def _ease_out_cubic(self, t: float) -> float:
        """缓出立方曲线"""
        return 1.0 - math.pow(1.0 - t, 3.0)
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """缓入缓出立方曲线"""
        if t < 0.5:
            return 4.0 * t * t * t
        return 1.0 - math.pow(-2.0 * t + 2.0, 3.0) / 2.0
    
    def _apply_easing(self, t: float, easing_type: int) -> float:
        """应用缓动函数"""
        if easing_type == 1:
            return self._ease_out_cubic(t)
        elif easing_type == 2:
            return self._ease_in_out_cubic(t)
        return t
    
    def _update_animation(self):
        """更新动画状态"""
        if not self._is_animating or self._anim_params is None:
            return
        
        now = time.time()
        elapsed = now - self._anim_start_time
        duration = self._anim_params.duration
        
        if elapsed >= duration:
            self._anim_progress = 1.0
            self._is_animating = False
        else:
            self._anim_progress = self._apply_easing(elapsed / duration, self._anim_params.easing_type)
    
    def get_version(self) -> str:
        """获取版本号"""
        return self.VERSION
    
    def init(self, width: int, height: int, native_window=None) -> bool:
        """初始化特效引擎"""
        if not HAS_PIL:
            self._log("警告: Pillow库未安装，某些视觉效果可能不可用")
        
        self._width = width
        self._height = height
        self._native_window = native_window
        self._last_time = time.time()
        self._is_initialized = True
        
        self._log(f"GLEffects初始化成功 (分辨率: {width}x{height})")
        return True
    
    def shutdown(self):
        """关闭特效引擎"""
        self._is_initialized = False
        self._log("GLEffects已关闭")
    
    def set_transparency(self, alpha: float) -> int:
        """设置透明度 (0.0-1.0)"""
        if not self._is_initialized:
            return GLEffectsError.ERROR_INIT_FAILED
        
        if alpha < 0.0 or alpha > 1.0:
            return GLEffectsError.ERROR_INVALID_PARAM
        
        self._transparency = alpha
        return GLEffectsError.SUCCESS
    
    def get_transparency(self) -> float:
        """获取当前透明度"""
        return self._transparency
    
    def enable_glass_effect(self, enable: bool) -> int:
        """启用/禁用毛玻璃效果"""
        if not self._is_initialized:
            return GLEffectsError.ERROR_INIT_FAILED
        
        self._glass_enabled = enable
        return GLEffectsError.SUCCESS
    
    def is_glass_enabled(self) -> bool:
        """检查毛玻璃效果是否启用"""
        return self._glass_enabled
    
    def set_glass_params(self, params: GlassEffectParams) -> int:
        """设置毛玻璃效果参数"""
        if not self._is_initialized:
            return GLEffectsError.ERROR_INIT_FAILED
        
        if params is None:
            return GLEffectsError.ERROR_INVALID_PARAM
        
        self._glass_params = params
        return GLEffectsError.SUCCESS
    
    def get_glass_params(self) -> GlassEffectParams:
        """获取毛玻璃效果参数"""
        return self._glass_params
    
    def enable_glow_effect(self, enable: bool) -> int:
        """启用/禁用边框光晕效果"""
        if not self._is_initialized:
            return GLEffectsError.ERROR_INIT_FAILED
        
        self._glow_enabled = enable
        return GLEffectsError.SUCCESS
    
    def is_glow_enabled(self) -> bool:
        """检查边框光晕效果是否启用"""
        return self._glow_enabled
    
    def set_glow_params(self, params: GlowEffectParams) -> int:
        """设置边框光晕效果参数"""
        if not self._is_initialized:
            return GLEffectsError.ERROR_INIT_FAILED
        
        if params is None:
            return GLEffectsError.ERROR_INVALID_PARAM
        
        self._glow_params = params
        return GLEffectsError.SUCCESS
    
    def get_glow_params(self) -> GlowEffectParams:
        """获取边框光晕效果参数"""
        return self._glow_params
    
    def start_window_animation(self, params: WindowAnimationParams) -> int:
        """开始窗口动画"""
        if not self._is_initialized:
            return GLEffectsError.ERROR_INIT_FAILED
        
        if params is None:
            return GLEffectsError.ERROR_INVALID_PARAM
        
        self._anim_params = params
        self._anim_progress = 0.0
        self._anim_start_time = time.time()
        self._is_animating = True
        
        return GLEffectsError.SUCCESS
    
    def is_animating(self) -> bool:
        """检查是否正在播放动画"""
        return self._is_animating
    
    def render(self) -> int:
        """执行渲染"""
        if not self._is_initialized:
            return GLEffectsError.ERROR_INIT_FAILED
        
        # 更新动画
        self._update_animation()
        
        # 更新帧率统计
        now = time.time()
        delta = now - self._last_time
        self._last_time = now
        
        self._frame_time_accum += delta
        self._fps_frame_count += 1
        if self._frame_time_accum >= 1.0:
            self._current_fps = self._fps_frame_count / self._frame_time_accum
            self._fps_frame_count = 0
            self._frame_time_accum = 0.0
        
        self._current_frame += 1
        return GLEffectsError.SUCCESS
    
    def render_glass_effect(self, image) -> Optional:
        """对图像应用毛玻璃效果"""
        if not HAS_PIL or not self._glass_enabled:
            return image
        
        try:
            img = Image.fromarray(image) if hasattr(image, 'shape') else image
            
            # 应用模糊
            blurred = img.filter(ImageFilter.GaussianBlur(radius=self._glass_params.blur_radius))
            
            # 添加色调叠加
            tint = Image.new('RGBA', img.size, self._glass_params.tint_color.to_rgba())
            result = Image.blend(blurred, tint, self._glass_params.tint_color.a * self._glass_params.opacity)
            
            # 添加边框
            if self._glass_params.enable_border_sharp and self._glass_params.border_width > 0:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(result)
                draw.rectangle(
                    [0, 0, img.width - 1, img.height - 1],
                    outline=self._glass_params.border_color.to_rgba(),
                    width=int(self._glass_params.border_width)
                )
            
            return result
        
        except Exception as e:
            self._log(f"渲染毛玻璃效果失败: {e}")
            return image
    
    def render_glow_effect(self, image) -> Optional:
        """对图像应用光晕效果"""
        if not HAS_PIL or not self._glow_enabled:
            return image
        
        try:
            img = Image.fromarray(image) if hasattr(image, 'shape') else image
            width, height = img.size
            
            # 创建光晕层
            glow_layer = Image.new('RGBA', (width + int(self._glow_params.glow_radius * 2), 
                                          height + int(self._glow_params.glow_radius * 2)), (0, 0, 0, 0))
            
            # 绘制多层光晕
            from PIL import ImageDraw
            draw = ImageDraw.Draw(glow_layer)
            
            center_x = width // 2 + int(self._glow_params.glow_radius)
            center_y = height // 2 + int(self._glow_params.glow_radius)
            
            for r in range(int(self._glow_params.glow_radius), 0, -2):
                alpha = int((1.0 - r / self._glow_params.glow_radius) * 
                           self._glow_params.glow_intensity * 76.5)  # 0.3 * 255
                color = (
                    int(self._glow_params.glow_color.r * 255),
                    int(self._glow_params.glow_color.g * 255),
                    int(self._glow_params.glow_color.b * 255),
                    alpha
                )
                draw.ellipse(
                    [center_x - r, center_y - r, center_x + r, center_y + r],
                    fill=color
                )
            
            # 裁剪到原始大小
            glow_layer = glow_layer.crop((
                int(self._glow_params.glow_radius),
                int(self._glow_params.glow_radius),
                int(self._glow_params.glow_radius) + width,
                int(self._glow_params.glow_radius) + height
            ))
            
            # 合并光晕层
            result = Image.alpha_composite(img.convert('RGBA'), glow_layer)
            
            # 添加阴影
            shadow_offset = (int(self._glow_params.shadow_offset_x), 
                            int(self._glow_params.shadow_offset_y))
            shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_layer)
            shadow_color = self._glow_params.shadow_color.to_rgba()
            shadow_draw.rectangle(
                [shadow_offset[0], shadow_offset[1], width, height],
                fill=shadow_color
            )
            
            # 合并阴影
            result = Image.alpha_composite(shadow_layer, result)
            
            return result
        
        except Exception as e:
            self._log(f"渲染光晕效果失败: {e}")
            return image
    
    def set_log_callback(self, callback):
        """设置日志回调函数"""
        self._log_callback = callback
    
    def get_error_message(self, error: int) -> str:
        """获取错误信息"""
        error_messages = {
            GLEffectsError.SUCCESS: "Success",
            GLEffectsError.ERROR_INVALID_PARAM: "Invalid parameter",
            GLEffectsError.ERROR_INIT_FAILED: "Initialization failed",
            GLEffectsError.ERROR_RENDER_FAILED: "Render failed",
            GLEffectsError.ERROR_MEMORY: "Memory allocation failed",
            GLEffectsError.ERROR_UNSUPPORTED: "Unsupported operation"
        }
        return error_messages.get(error, "Unknown error")
    
    def get_fps(self) -> float:
        """获取当前帧率"""
        return self._current_fps
    
    def get_frame_count(self) -> int:
        """获取渲染帧数"""
        return self._current_frame
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# 示例用法
if __name__ == "__main__":
    print("GLEffects Python 纯实现测试")
    
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
    
    # 渲染测试
    for i in range(10):
        effects.render()
        time.sleep(0.1)
    
    print(f"渲染帧数: {effects.get_frame_count()}")
    print(f"帧率: {effects.get_fps():.1f} FPS")
    
    # 关闭
    effects.shutdown()
    print("已关闭")