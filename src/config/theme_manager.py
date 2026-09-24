import os
import json
import time
import configparser
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ThemeColors:
    """主题颜色配置"""
    primary: str = "#1E90FF"
    secondary: str = "#00BFFF"
    accent: str = "#87CEEB"
    background: str = "#0A192F"
    surface: str = "#112240"
    card: str = "#1A365D"
    border: str = "#2D4A6F"
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#94A3B8"
    text_disabled: str = "#475569"
    success: str = "#10B981"
    warning: str = "#F59E0B"
    error: str = "#EF4444"
    info: str = "#3B82F6"

@dataclass
class ThemeConfig:
    """主题配置 - 支持亮色和暗色模式"""
    name: str = "Default"
    author: str = "System"
    version: str = "1.0"
    description: str = ""
    dark_colors: ThemeColors = None    # 暗色模式颜色
    light_colors: ThemeColors = None   # 亮色模式颜色
    file_path: str = ""
    
    def __post_init__(self):
        if self.dark_colors is None:
            self.dark_colors = ThemeColors()
        if self.light_colors is None:
            self.light_colors = ThemeColors()
    
    def get_colors(self, mode: str = "dark") -> ThemeColors:
        """获取指定模式的颜色配置"""
        if mode == "light":
            return self.light_colors
        return self.dark_colors

class ThemeManager:
    """主题管理器 - 支持加载ini配置文件和拖放加载"""
    
    def __init__(self):
        self.themes: Dict[str, ThemeConfig] = {}
        self.current_theme: Optional[ThemeConfig] = None
        # 主题目录在项目根目录下的 config/themes
        self.themes_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config', 'themes'
        )
        self._create_themes_dir()
        self._last_scan_time = 0
    
    def _create_themes_dir(self):
        """创建主题目录"""
        os.makedirs(self.themes_dir, exist_ok=True)
    
    def hot_reload(self) -> List[str]:
        """热加载主题 - 重新扫描目录并返回变化的主题列表"""
        changes = {'added': [], 'removed': [], 'updated': []}
        
        current_names = set(self.themes.keys())
        new_names = set()
        
        if os.path.exists(self.themes_dir):
            for filename in os.listdir(self.themes_dir):
                if filename.endswith('.ini'):
                    filepath = os.path.join(self.themes_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    
                    # 检查是否是新文件或已更新
                    theme = self.load_theme(filepath)
                    if theme:
                        new_names.add(theme.name)
                        
                        if theme.name not in current_names:
                            self.themes[theme.name] = theme
                            changes['added'].append(theme.name)
                        elif theme.name in self.themes:
                            old_mtime = getattr(self.themes[theme.name], '_mtime', 0)
                            if mtime > old_mtime:
                                self.themes[theme.name] = theme
                                changes['updated'].append(theme.name)
                        self.themes[theme.name]._mtime = mtime
        
        # 检查已删除的主题
        for name in current_names - new_names:
            if name != getattr(self.current_theme, 'name', ''):
                del self.themes[name]
                changes['removed'].append(name)
        
        self._last_scan_time = time.time()
        return changes
    
    def has_updates(self) -> bool:
        """检查是否有新的主题文件变化"""
        if not os.path.exists(self.themes_dir):
            return False
        
        for filename in os.listdir(self.themes_dir):
            if filename.endswith('.ini'):
                filepath = os.path.join(self.themes_dir, filename)
                if os.path.getmtime(filepath) > self._last_scan_time:
                    return True
        
        return False
    
    def _clean_value(self, value: str) -> str:
        """清理配置值中的行尾注释和多余空格

        注意：仅把"空白符之后的 ; 或 #"视为注释起始，避免破坏以 # 开头的十六进制颜色值。
        """
        import re
        if not value:
            return value

        # 去除行尾注释（注释符前必须有空白，如 "100 # 说明" / "abc ; 说明"）
        value = re.split(r'\s+[;#]', value, maxsplit=1)[0]

        # 去除首尾空格
        return value.strip()
        
    def load_theme(self, file_path: str) -> Optional[ThemeConfig]:
        """加载单个主题配置文件 - 支持亮色和暗色模式"""
        if not os.path.exists(file_path):
            return None
        
        try:
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            
            if 'Theme' not in config:
                return None
            
            theme = ThemeConfig(
                name=self._clean_value(config['Theme'].get('name', 'Unnamed')),
                author=self._clean_value(config['Theme'].get('author', 'Unknown')),
                version=self._clean_value(config['Theme'].get('version', '1.0')),
                description=self._clean_value(config['Theme'].get('description', '')),
                file_path=file_path
            )
            
            # 跳过示例文件（名称包含 "example" 或 "示例"）
            if 'example' in theme.name.lower() or '示例' in theme.name:
                return None
            
            # 加载暗色模式颜色
            dark_colors = ThemeColors()
            if 'ColorsDark' in config:
                for attr in dir(dark_colors):
                    if not attr.startswith('_'):
                        value = self._clean_value(config['ColorsDark'].get(attr))
                        if value:
                            setattr(dark_colors, attr, value)
            theme.dark_colors = dark_colors
            
            # 加载亮色模式颜色
            light_colors = ThemeColors()
            if 'ColorsLight' in config:
                for attr in dir(light_colors):
                    if not attr.startswith('_'):
                        value = self._clean_value(config['ColorsLight'].get(attr))
                        if value:
                            setattr(light_colors, attr, value)
            # 如果没有亮色配置，使用暗色配置的互补色
            else:
                self._generate_light_colors(light_colors, dark_colors)
            
            theme.light_colors = light_colors
            
            return theme
        
        except Exception as e:
            print(f"Error loading theme {file_path}: {e}")
            return None
    
    def _generate_light_colors(self, light_colors: ThemeColors, dark_colors: ThemeColors):
        """从暗色颜色生成对应的亮色颜色"""
        for attr in dir(dark_colors):
            if not attr.startswith('_'):
                dark_color = getattr(dark_colors, attr)
                if dark_color.startswith('#'):
                    light_color = self._invert_color(dark_color)
                    setattr(light_colors, attr, light_color)
    
    def _invert_color(self, hex_color: str) -> str:
        """反转颜色（用于生成亮色版本）"""
        try:
            hex_color = hex_color.lstrip('#')
            r = 255 - int(hex_color[0:2], 16)
            g = 255 - int(hex_color[2:4], 16)
            b = 255 - int(hex_color[4:6], 16)
            return f'#{r:02X}{g:02X}{b:02X}'
        except:
            return hex_color
    
    def load_all_themes(self):
        """加载所有主题配置文件"""
        self.themes.clear()
        
        if not os.path.exists(self.themes_dir):
            return
        
        for filename in os.listdir(self.themes_dir):
            if filename.endswith('.ini'):
                filepath = os.path.join(self.themes_dir, filename)
                theme = self.load_theme(filepath)
                if theme:
                    self.themes[theme.name] = theme
        
        if self.themes:
            self.current_theme = list(self.themes.values())[0]
    
    def get_theme_names(self) -> List[str]:
        """获取所有主题名称"""
        return list(self.themes.keys())
    
    def get_theme(self, name: str) -> Optional[ThemeConfig]:
        """获取指定主题"""
        return self.themes.get(name)
    
    def set_theme(self, name: str) -> bool:
        """设置当前主题"""
        theme = self.themes.get(name)
        if theme:
            self.current_theme = theme
            return True
        return False
    
    def add_theme_from_file(self, file_path: str) -> Optional[str]:
        """从文件添加主题（拖放加载）"""
        if not file_path.endswith('.ini'):
            return None
        
        theme = self.load_theme(file_path)
        if theme:
            # 复制到主题目录
            dest_path = os.path.join(self.themes_dir, os.path.basename(file_path))
            if not os.path.exists(dest_path):
                import shutil
                shutil.copy(file_path, dest_path)
            
            self.themes[theme.name] = theme
            return theme.name
        return None
    
    def remove_theme(self, name: str) -> bool:
        """删除主题"""
        theme = self.themes.get(name)
        if theme:
            # 删除配置文件
            if os.path.exists(theme.file_path):
                os.remove(theme.file_path)
            
            # 从内存中移除
            del self.themes[name]
            
            # 如果删除的是当前主题，切换到第一个可用主题
            if self.current_theme and self.current_theme.name == name:
                if self.themes:
                    self.current_theme = list(self.themes.values())[0]
                else:
                    self.current_theme = None
            
            return True
        return False
    
    def create_theme(self, config: ThemeConfig) -> bool:
        """创建新主题"""
        # 检查是否已存在同名主题
        if config.name in self.themes:
            return False
        
        # 生成文件名
        filename = config.name.lower().replace(' ', '_') + '.ini'
        filepath = os.path.join(self.themes_dir, filename)
        
        # 写入配置文件
        try:
            config.file_path = filepath
            self._save_theme(config)
            self.themes[config.name] = config
            return True
        except Exception as e:
            print(f"Error creating theme: {e}")
            return False
    
    def _save_theme(self, theme: ThemeConfig):
        """保存主题到文件 - 支持亮色和暗色模式"""
        config = configparser.ConfigParser()
        
        config['Theme'] = {
            'name': theme.name,
            'author': theme.author,
            'version': theme.version,
            'description': theme.description
        }
        
        # 保存暗色模式颜色
        dark_colors_dict = {}
        for attr in dir(theme.dark_colors):
            if not attr.startswith('_'):
                dark_colors_dict[attr] = getattr(theme.dark_colors, attr)
        config['ColorsDark'] = dark_colors_dict
        
        # 保存亮色模式颜色
        light_colors_dict = {}
        for attr in dir(theme.light_colors):
            if not attr.startswith('_'):
                light_colors_dict[attr] = getattr(theme.light_colors, attr)
        config['ColorsLight'] = light_colors_dict
        
        with open(theme.file_path, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def export_theme(self, name: str, output_path: str) -> bool:
        """导出主题配置文件"""
        theme = self.themes.get(name)
        if theme:
            try:
                import shutil
                shutil.copy(theme.file_path, output_path)
                return True
            except Exception as e:
                print(f"Error exporting theme: {e}")
                return False
        return False

    # ── CustomTkinter 热加载支持 ──────────────────────────────────────

    def get_ctk_theme_cache_path(self, name: str) -> str:
        """获取 ini 主题对应的 CustomTkinter JSON 缓存路径"""
        cache_dir = os.path.join(self.themes_dir, '.cache')
        safe_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)
        return os.path.join(cache_dir, f'{safe_name}.json')

    def build_ctk_theme_dict(self, name: str) -> Optional[dict]:
        """将 ini 主题（含亮色/暗色两套颜色）转换为 CustomTkinter 主题 JSON 字典

        JSON 中双色字段统一按 [light, dark] 顺序，与官方 blue.json 保持一致。
        """
        theme = self.themes.get(name)
        if not theme:
            return None

        light = theme.light_colors
        dark = theme.dark_colors
        pair = lambda light_color, dark_color: [light_color, dark_color]

        theme_dict = {
            "CTk": {
                "fg_color": pair(light.background, dark.background)
            },
            "CTkToplevel": {
                "fg_color": pair(light.background, dark.background)
            },
            "CTkFrame": {
                "corner_radius": 6,
                "border_width": 0,
                "fg_color": pair(light.surface, dark.surface),
                "top_fg_color": pair(light.card, dark.card),
                "border_color": pair(light.border, dark.border)
            },
            "CTkButton": {
                "corner_radius": 6,
                "border_width": 0,
                "fg_color": pair(light.primary, dark.primary),
                "hover_color": pair(light.secondary, dark.secondary),
                "border_color": pair(light.border, dark.border),
                "text_color": pair(light.text_primary, dark.text_primary),
                "text_color_disabled": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkLabel": {
                "corner_radius": 0,
                "fg_color": "transparent",
                "text_color": pair(light.text_primary, dark.text_primary)
            },
            "CTkEntry": {
                "corner_radius": 6,
                "border_width": 2,
                "fg_color": pair(light.card, dark.card),
                "border_color": pair(light.border, dark.border),
                "text_color": pair(light.text_primary, dark.text_primary),
                "placeholder_text_color": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkCheckBox": {
                "corner_radius": 6,
                "border_width": 3,
                "fg_color": pair(light.primary, dark.primary),
                "border_color": pair(light.border, dark.border),
                "hover_color": pair(light.secondary, dark.secondary),
                "checkmark_color": pair(light.text_primary, dark.text_primary),
                "text_color": pair(light.text_primary, dark.text_primary),
                "text_color_disabled": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkSwitch": {
                "corner_radius": 1000,
                "border_width": 3,
                "button_length": 0,
                "fg_color": pair(light.border, dark.border),
                "progress_color": pair(light.primary, dark.primary),
                "button_color": pair(light.text_primary, dark.text_primary),
                "button_hover_color": pair(light.text_secondary, dark.text_secondary),
                "text_color": pair(light.text_primary, dark.text_primary),
                "text_color_disabled": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkRadioButton": {
                "corner_radius": 1000,
                "border_width_checked": 6,
                "border_width_unchecked": 3,
                "fg_color": pair(light.primary, dark.primary),
                "border_color": pair(light.border, dark.border),
                "hover_color": pair(light.secondary, dark.secondary),
                "text_color": pair(light.text_primary, dark.text_primary),
                "text_color_disabled": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkProgressBar": {
                "corner_radius": 1000,
                "border_width": 0,
                "fg_color": pair(light.border, dark.border),
                "progress_color": pair(light.primary, dark.primary),
                "border_color": pair(light.border, dark.border)
            },
            "CTkSlider": {
                "corner_radius": 1000,
                "button_corner_radius": 1000,
                "border_width": 6,
                "button_length": 0,
                "fg_color": pair(light.border, dark.border),
                "progress_color": pair(light.secondary, dark.secondary),
                "button_color": pair(light.primary, dark.primary),
                "button_hover_color": pair(light.secondary, dark.secondary)
            },
            "CTkOptionMenu": {
                "corner_radius": 6,
                "fg_color": pair(light.primary, dark.primary),
                "button_color": pair(light.secondary, dark.secondary),
                "button_hover_color": pair(light.accent, dark.accent),
                "text_color": pair(light.text_primary, dark.text_primary),
                "text_color_disabled": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkComboBox": {
                "corner_radius": 6,
                "border_width": 2,
                "fg_color": pair(light.card, dark.card),
                "border_color": pair(light.border, dark.border),
                "button_color": pair(light.border, dark.border),
                "button_hover_color": pair(light.text_disabled, dark.text_secondary),
                "text_color": pair(light.text_primary, dark.text_primary),
                "text_color_disabled": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkScrollbar": {
                "corner_radius": 1000,
                "border_spacing": 4,
                "fg_color": "transparent",
                "button_color": pair(light.text_disabled, dark.border),
                "button_hover_color": pair(light.text_secondary, dark.text_secondary)
            },
            "CTkSegmentedButton": {
                "corner_radius": 6,
                "border_width": 2,
                "fg_color": pair(light.border, dark.border),
                "selected_color": pair(light.primary, dark.primary),
                "selected_hover_color": pair(light.secondary, dark.secondary),
                "unselected_color": pair(light.border, dark.border),
                "unselected_hover_color": pair(light.text_disabled, dark.text_secondary),
                "text_color": pair(light.text_primary, dark.text_primary),
                "text_color_disabled": pair(light.text_disabled, dark.text_disabled)
            },
            "CTkTextbox": {
                "corner_radius": 6,
                "border_width": 0,
                "fg_color": pair(light.card, dark.card),
                "border_color": pair(light.border, dark.border),
                "text_color": pair(light.text_primary, dark.text_primary),
                "scrollbar_button_color": pair(light.text_disabled, dark.border),
                "scrollbar_button_hover_color": pair(light.text_secondary, dark.text_secondary)
            },
            "CTkScrollableFrame": {
                "label_fg_color": pair(light.card, dark.card)
            },
            "DropdownMenu": {
                "fg_color": pair(light.surface, dark.surface),
                "hover_color": pair(light.card, dark.card),
                "text_color": pair(light.text_primary, dark.text_primary)
            },
            "CTkFont": {
                "macOS": {
                    "family": "SF Display",
                    "size": 13,
                    "weight": "normal"
                },
                "Windows": {
                    "family": "Roboto",
                    "size": 13,
                    "weight": "normal"
                },
                "Linux": {
                    "family": "Roboto",
                    "size": 13,
                    "weight": "normal"
                }
            }
        }

        return theme_dict

    def export_ctk_theme_json(self, name: str, output_path: Optional[str] = None) -> Optional[str]:
        """导出主题为 CustomTkinter JSON 文件（默认写入缓存目录），返回文件路径；失败返回 None"""
        theme_dict = self.build_ctk_theme_dict(name)
        if theme_dict is None:
            return None

        target_path = output_path or self.get_ctk_theme_cache_path(name)
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(theme_dict, f, ensure_ascii=False, indent=2)
            return target_path
        except Exception as e:
            print(f"Error exporting CTk theme json for {name}: {e}")
            return None

# 全局主题管理器实例
theme_manager = ThemeManager()
