import numpy as np
from PIL import Image
from typing import Tuple, Optional, List

class ImageProcessor:
    def __init__(self):
        self.ascii_chars = '@%#*+=-:. '
        self.ascii_chars_reversed = self.ascii_chars[::-1]
    
    def image_to_ascii(self, image: Image.Image, width: int = 80, height: Optional[int] = None, 
                       invert: bool = False) -> str:
        """将图片转换为ASCII艺术"""
        img = image.convert('L')
        
        original_width, original_height = img.size
        
        if height is None:
            ratio = original_height / original_width
            height = int(width * ratio * 0.55)
        
        img = img.resize((width, height))
        
        pixels = np.array(img)
        
        ascii_result = []
        chars = self.ascii_chars_reversed if invert else self.ascii_chars
        
        for row in pixels:
            ascii_row = []
            for pixel in row:
                char_idx = int(pixel * (len(chars) - 1) / 255)
                char_idx = max(0, min(char_idx, len(chars) - 1))
                ascii_row.append(chars[char_idx])
            ascii_result.append(''.join(ascii_row))
        
        return '\n'.join(ascii_result)
    
    def image_to_pixel_matrix(self, image: Image.Image, sample_size: int = 20) -> str:
        """将图片转换为像素矩阵描述"""
        img = image.convert('RGB')
        width, height = img.size
        
        step_x = max(1, width // sample_size)
        step_y = max(1, height // sample_size)
        
        result = []
        result.append(f"图片尺寸: {width} x {height}")
        result.append(f"采样网格: {width//step_x} x {height//step_y}")
        result.append("像素矩阵:")
        result.append("-" * (width//step_x * 8))
        
        for y in range(0, height, step_y):
            row_str = "|"
            for x in range(0, width, step_x):
                pixel = img.getpixel((x, y))
                r, g, b = pixel
                brightness = int((r + g + b) / 3)
                
                if brightness < 64:
                    char = '█'
                elif brightness < 128:
                    char = '▓'
                elif brightness < 192:
                    char = '▒'
                else:
                    char = '░'
                
                row_str += f"{char}{char}"
            row_str += "|"
            result.append(row_str)
        
        result.append("-" * (width//step_x * 8))
        result.append("\nRGB采样点:")
        
        sample_points = []
        for y in range(0, height, step_y * 4):
            row_samples = []
            for x in range(0, width, step_x * 4):
                pixel = img.getpixel((x, y))
                row_samples.append(f"({pixel[0]},{pixel[1]},{pixel[2]})")
            sample_points.append(' '.join(row_samples))
        
        result.extend(sample_points)
        
        return '\n'.join(result)
    
    def analyze_image(self, image: Image.Image) -> str:
        """分析图片并生成综合描述"""
        img = image.convert('RGB')
        width, height = img.size
        
        analysis = []
        analysis.append(f"📷 图片分析报告")
        analysis.append("=" * 50)
        analysis.append(f"尺寸: {width} x {height}")
        analysis.append(f"模式: {image.mode}")
        
        pixels = np.array(img)
        
        mean_r = np.mean(pixels[:, :, 0])
        mean_g = np.mean(pixels[:, :, 1])
        mean_b = np.mean(pixels[:, :, 2])
        analysis.append(f"平均颜色: R={mean_r:.0f}, G={mean_g:.0f}, B={mean_b:.0f}")
        
        dominant_color = self._get_dominant_color(pixels)
        analysis.append(f"主色调: {dominant_color}")
        
        gray = np.mean(pixels, axis=2)
        brightness = np.mean(gray)
        brightness_level = "暗" if brightness < 85 else "中等" if brightness < 170 else "亮"
        analysis.append(f"亮度: {brightness_level} ({brightness:.0f})")
        
        contrast = np.std(gray)
        contrast_level = "低" if contrast < 30 else "中等" if contrast < 60 else "高"
        analysis.append(f"对比度: {contrast_level} ({contrast:.0f})")
        
        analysis.append("=" * 50)
        
        return '\n'.join(analysis)
    
    def _get_dominant_color(self, pixels: np.ndarray) -> str:
        """获取图片的主色调"""
        mean_r = np.mean(pixels[:, :, 0])
        mean_g = np.mean(pixels[:, :, 1])
        mean_b = np.mean(pixels[:, :, 2])
        
        if mean_r > mean_g and mean_r > mean_b:
            if mean_g > mean_b:
                return "橙色系"
            else:
                return "紫色系"
        elif mean_g > mean_r and mean_g > mean_b:
            if mean_r > mean_b:
                return "黄绿色系"
            else:
                return "青绿色系"
        else:
            if mean_r > mean_g:
                return "洋红色系"
            else:
                return "蓝紫色系"
    
    def full_analysis(self, image: Image.Image, ascii_width: int = 60) -> str:
        """完整的图片分析，包含ASCII艺术和像素矩阵"""
        result = []
        
        result.append("=" * 80)
        result.append("📷 图片完整分析")
        result.append("=" * 80)
        result.append("")
        
        result.append("1️⃣ 图片统计信息")
        result.append("-" * 80)
        result.append(self.analyze_image(image))
        result.append("")
        
        result.append("2️⃣ ASCII艺术")
        result.append("-" * 80)
        ascii_art = self.image_to_ascii(image, width=ascii_width)
        result.append(ascii_art)
        result.append("")
        
        result.append("3️⃣ 像素矩阵")
        result.append("-" * 80)
        pixel_matrix = self.image_to_pixel_matrix(image, sample_size=15)
        result.append(pixel_matrix)
        result.append("")
        
        result.append("=" * 80)
        
        return '\n'.join(result)