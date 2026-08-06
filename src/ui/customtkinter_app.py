import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, messagebox
from typing import Optional, Callable, Dict, Any
import threading
import queue
import time
import sys
import os
import time
from PIL import Image, ImageTk
import pystray

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.ai_providers import AIProviderManager
from src.config.settings import settings
from src.services.ai_service import AIService
from src.services.local_model_service import LocalModelService
from src.services.websocket_server import WebSocketServer
from src.services.api_server import APIServer
from src.services.screen_monitor import screen_monitor
from src.services.video_editor import VideoEditor
from src.system.controller import SystemController
from src.system.vision import VisionCapture
from src.utils.logger import setup_logger
from src.utils.markdown_renderer import MarkdownRenderer
from src.ui.splash_screen import SplashScreen
from src.ui.effects import GLEffects, GLColor, GlassEffectParams, GlowEffectParams

try:
    import pywinstyles
    HAS_PYWINSTYLES = True
except ImportError:
    HAS_PYWINSTYLES = False
    print("警告: pywinstyles未安装，Windows美化功能将不可用")

logger = setup_logger(__name__)


class CustomTkinterApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("AI电脑控制")
        self.root.geometry("1200x800")
        self.root.withdraw()  # 隐藏主窗口
        
        # 初始化UI视觉特效引擎
        self._init_ui_effects()
        
        # 显示启动画面
        self.splash_screen = SplashScreen(self.root, self.on_splash_close)
        
        # 初始化服务（在后台进行）
        self.ai_service = AIService()
        self.ai_provider_manager = AIProviderManager()
        self.system_controller = SystemController()
        self.vision_capture = VisionCapture()
        self.markdown_renderer = MarkdownRenderer()
        self.local_model_service = LocalModelService()
        
        # 启动WebSocket服务器（从settings读取配置）
        self.websocket_server = WebSocketServer(host=settings.host, port=settings.websocket_port)
        self.websocket_server.start()
        print(f"WebSocket服务器已启动，端口: {settings.websocket_port}")
        print(f"网页控制端地址: http://localhost:{settings.websocket_port}")
        
        # 启动API服务器（从settings读取配置）
        self.api_server = APIServer(host=settings.host, port=settings.api_port)
        self.api_server.start()
        print(f"API服务器已启动，端口: {settings.api_port}")
        print(f"API网页控制端地址: http://localhost:{settings.api_port}")
        
        # 启动桌面监控服务器
        screen_monitor.start()
        print(f"桌面监控服务器已启动，端口: {screen_monitor.port}")
        
        # 启动视频剪辑服务器
        self.video_editor = VideoEditor()
        self.video_editor.start()
        print(f"视频剪辑服务器已启动，端口: {self.video_editor.port}")
        
        self.message_queue = queue.Queue()
        self.is_running = True
        self.current_iteration = 0
        self.is_iterating = False
        
        # 系统托盘相关
        self.tray_icon = None
        self.tray_thread = None
        
        # UI特效参数
        self.glass_enabled = False
        self.glow_enabled = False
        self.window_transparency = 1.0
        
        # Windows美化参数
        self.window_style = "aero"
        self.accent_color = None
        self.border_color = None
        self.header_color = None
        self.title_color = None
        self.use_acrylic = False
        self.use_mica = False
        
    def _init_ui_effects(self):
        """初始化UI视觉特效引擎"""
        try:
            self.effects_engine = GLEffects()
            # 初始化特效引擎（使用默认窗口大小）
            self.effects_engine.init(800, 600)
            print("UI视觉特效引擎初始化成功")
            
            # 设置默认参数
            glass_params = GlassEffectParams()
            glass_params.blur_radius = 15.0
            glass_params.opacity = 0.7
            glass_params.tint_color = GLColor(0.1, 0.15, 0.25, 0.6)
            self.effects_engine.set_glass_params(glass_params)
            
            glow_params = GlowEffectParams()
            glow_params.glow_color = GLColor(0.2, 0.5, 1.0, 0.5)
            glow_params.glow_intensity = 0.6
            self.effects_engine.set_glow_params(glow_params)
            
            # 启用日志回调
            self.effects_engine.set_log_callback(self._on_effects_log)
            
        except Exception as e:
            print(f"UI视觉特效引擎初始化失败: {e}")
            self.effects_engine = None
    
    def _on_effects_log(self, message: str):
        """UI特效日志回调"""
        self.log_message(f"[特效引擎] {message}", "INFO")
    
    def _init_windows_styles(self):
        """初始化Windows美化效果"""
        if not HAS_PYWINSTYLES:
            return
        
        try:
            # 应用窗口样式
            pywinstyles.apply_style(self.root, "aero")
            self.log_message("Windows窗口样式已应用: Aero", "INFO")
            
            # 设置窗口透明度
            pywinstyles.set_opacity(self.root, value=1.0)
            
            print("Windows美化效果初始化成功")
        except Exception as e:
            print(f"Windows美化效果初始化失败: {e}")
    
    def apply_window_style(self, style: str):
        """应用Windows窗口样式
        
        可用样式: 'aero', 'acrylic', 'mica', 'mica-alt', 'dark', 'light'
        """
        if not HAS_PYWINSTYLES:
            self.log_message("pywinstyles未安装，无法应用窗口样式", "WARNING")
            return False
        
        try:
            pywinstyles.apply_style(self.root, style)
            self.window_style = style
            self.log_message(f"窗口样式已应用: {style}", "SUCCESS")
            return True
        except Exception as e:
            self.log_message(f"应用窗口样式失败: {e}", "ERROR")
            return False
    
    def set_window_opacity(self, opacity: float):
        """设置窗口不透明度 (0.0-1.0)"""
        if not HAS_PYWINSTYLES:
            return False
        
        try:
            pywinstyles.set_opacity(self.root, value=opacity)
            self.window_transparency = opacity
            self.log_message(f"窗口不透明度已设置为: {int(opacity * 100)}%", "INFO")
            return True
        except Exception as e:
            self.log_message(f"设置窗口不透明度失败: {e}", "ERROR")
            return False
    
    def change_border_color(self, color: str):
        """更改窗口边框颜色
        
        color: 十六进制颜色代码，如 "#1E90FF"
        """
        if not HAS_PYWINSTYLES:
            return False
        
        try:
            pywinstyles.change_border_color(self.root, color=color)
            self.border_color = color
            self.log_message(f"窗口边框颜色已更改: {color}", "INFO")
            return True
        except Exception as e:
            self.log_message(f"更改边框颜色失败: {e}", "ERROR")
            return False
    
    def change_header_color(self, color: str):
        """更改窗口标题栏颜色
        
        color: 十六进制颜色代码，如 "#1E90FF"
        """
        if not HAS_PYWINSTYLES:
            return False
        
        try:
            pywinstyles.change_header_color(self.root, color=color)
            self.header_color = color
            self.log_message(f"窗口标题栏颜色已更改: {color}", "INFO")
            return True
        except Exception as e:
            self.log_message(f"更改标题栏颜色失败: {e}", "ERROR")
            return False
    
    def change_title_color(self, color: str):
        """更改窗口标题文字颜色
        
        color: 十六进制颜色代码，如 "#FFFFFF"
        """
        if not HAS_PYWINSTYLES:
            return False
        
        try:
            pywinstyles.change_title_color(self.root, color=color)
            self.title_color = color
            self.log_message(f"窗口标题文字颜色已更改: {color}", "INFO")
            return True
        except Exception as e:
            self.log_message(f"更改标题文字颜色失败: {e}", "ERROR")
            return False
    
    def apply_acrylic_effect(self, enable: bool):
        """应用Acrylic毛玻璃效果（Windows 11）"""
        if not HAS_PYWINSTYLES:
            return False
        
        try:
            if enable:
                pywinstyles.apply_style(self.root, "acrylic")
                self.use_acrylic = True
                self.log_message("Acrylic毛玻璃效果已启用", "SUCCESS")
            else:
                pywinstyles.apply_style(self.root, "aero")
                self.use_acrylic = False
                self.log_message("Acrylic毛玻璃效果已禁用", "INFO")
            return True
        except Exception as e:
            self.log_message(f"应用Acrylic效果失败: {e}", "ERROR")
            return False
    
    def apply_mica_effect(self, enable: bool):
        """应用Mica材质效果（Windows 11）"""
        if not HAS_PYWINSTYLES:
            return False
        
        try:
            if enable:
                pywinstyles.apply_style(self.root, "mica")
                self.use_mica = True
                self.log_message("Mica材质效果已启用", "SUCCESS")
            else:
                pywinstyles.apply_style(self.root, "aero")
                self.use_mica = False
                self.log_message("Mica材质效果已禁用", "INFO")
            return True
        except Exception as e:
            self.log_message(f"应用Mica效果失败: {e}", "ERROR")
            return False
    
    def set_window_transparency(self, alpha: float):
        """设置窗口透明度 (0.0-1.0)"""
        if self.effects_engine:
            result = self.effects_engine.set_transparency(alpha)
            if result == 0:
                self.window_transparency = alpha
                # 应用到实际窗口
                try:
                    self.root.attributes("-alpha", alpha)
                    self.log_message(f"窗口透明度已设置为: {int(alpha * 100)}%", "INFO")
                except:
                    pass
            return result
        return -1
    
    def enable_glass_effect(self, enable: bool):
        """启用/禁用毛玻璃效果"""
        if self.effects_engine:
            result = self.effects_engine.enable_glass_effect(enable)
            if result == 0:
                self.glass_enabled = enable
                self.log_message(f"毛玻璃效果: {'启用' if enable else '禁用'}", "INFO")
            return result
        return -1
    
    def enable_glow_effect(self, enable: bool):
        """启用/禁用边框光晕效果"""
        if self.effects_engine:
            result = self.effects_engine.enable_glow_effect(enable)
            if result == 0:
                self.glow_enabled = enable
                self.log_message(f"边框光晕效果: {'启用' if enable else '禁用'}", "INFO")
            return result
        return -1
    
    def update_ui_effects(self):
        """更新UI特效状态"""
        if self.effects_engine:
            self.effects_engine.render()
            # 定期更新
            self.root.after(16, self.update_ui_effects)  # ~60fps
        
    def on_splash_close(self):
        """启动画面关闭后的回调"""
        self.setup_ui()
        self.setup_bindings()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.load_conversations_from_file()
        self.load_default_provider_config()
        
        self.root.deiconify()  # 显示主窗口
        self.root.after(100, self.process_queue)

        # 配置高危操作二次授权（GUI 模式：队列 + after 桥接 messagebox 到主线程）
        try:
            from src.system.confirmation import ConfirmationManager
            ConfirmationManager().configure_gui(self.root, timeout=settings.high_risk_timeout)
        except Exception as e:
            print(f"[警告] GUI 确认管理器配置失败，高危操作将默认拒绝: {e}")

        # 初始化Windows美化效果
        self._init_windows_styles()
        
        # 启动UI特效更新循环
        self.update_ui_effects()
        
    def setup_ui(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        self.setup_sidebar()
        self.setup_main_area()
        
    def setup_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(self.root, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(0, weight=1)
        
        self.sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="AI电脑控制",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.sidebar_title.pack(padx=20, pady=(20, 10))
        
        self.setup_conversation_section()
        self.setup_ai_provider_section()
        self.setup_permission_section()
        self.setup_mode_section()
        self.setup_iteration_section()
        self.setup_vision_section()
        self.setup_settings_button()
        
    def setup_conversation_section(self):
        conversation_frame = ctk.CTkFrame(self.sidebar)
        conversation_frame.pack(fill="x", padx=10, pady=5)
        
        conv_header_frame = ctk.CTkFrame(conversation_frame)
        conv_header_frame.pack(fill="x", padx=5, pady=5)
        conv_header_frame.grid_columnconfigure(0, weight=1)
        
        conv_label = ctk.CTkLabel(
            conv_header_frame,
            text="对话历史",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        conv_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        
        self.new_conv_btn = ctk.CTkButton(
            conv_header_frame,
            text="➕",
            command=self.new_conversation,
            width=30,
            fg_color="green"
        )
        self.new_conv_btn.grid(row=0, column=1, padx=5, pady=2)
        
        self.conversation_list = ctk.CTkScrollableFrame(conversation_frame, height=120)
        self.conversation_list.pack(fill="x", padx=5, pady=2)
        
        self.conversations = []
        self.current_conversation = 0
        
        self.conv_buttons = []
        self.load_conversations()
        
    def load_conversations(self):
        for btn in self.conv_buttons:
            btn.destroy()
        self.conv_buttons.clear()
        
        if not self.conversations:
            self.conversations.append({
                "id": 1,
                "title": "新对话",
                "messages": [],
                "timestamp": time.time()
            })
        
        for idx, conv in enumerate(self.conversations):
            btn = ctk.CTkButton(
                self.conversation_list,
                text=conv["title"],
                command=lambda idx=idx: self.switch_conversation(idx),
                width=250,
                anchor="w"
            )
            btn.pack(fill="x", padx=2, pady=1)
            if idx == self.current_conversation:
                btn.configure(fg_color="blue")
            self.conv_buttons.append(btn)
        
        self.save_conversations()
    
    def new_conversation(self):
        new_id = max([c["id"] for c in self.conversations]) + 1 if self.conversations else 1
        self.conversations.append({
            "id": new_id,
            "title": "新对话",
            "messages": [],
            "timestamp": time.time()
        })
        self.current_conversation = len(self.conversations) - 1
        self._clear_chat_text()
        self.load_conversations()
        self.append_message("新对话已创建")
        self.log_message("创建新对话", "SUCCESS")
    
    def switch_conversation(self, index):
        if index < 0 or index >= len(self.conversations):
            return
        
        if index == self.current_conversation:
            return
        
        self.conversations[self.current_conversation]["messages"] = self.get_current_messages()
        
        self.current_conversation = index
        self._clear_chat_text()
        
        messages = self.conversations[index]["messages"]
        if messages:
            for msg in messages:
                if msg.strip():
                    self.chat_text.configure(state="normal")
                    self.chat_text.insert("end", msg + "\n\n")
                    self.chat_text.configure(state="disabled")
            self.chat_text.see("end")
        
        self.load_conversations()
        self.log_message(f"切换到对话: {self.conversations[index]['title']}", "INFO")
    
    def get_current_messages(self):
        self.chat_text.configure(state="normal")
        content = self.chat_text.get("1.0", "end-1c")
        self.chat_text.configure(state="disabled")
        return content.split("\n\n") if content else []
    
    def update_conversation_title(self):
        if self.conversations:
            message = self.input_text.get().strip()
            if message:
                title = self.generate_conversation_title(message)
                self.conversations[self.current_conversation]["title"] = title[:30] + "..." if len(title) > 30 else title
                self.conversations[self.current_conversation]["timestamp"] = time.time()
                self.save_conversations()
                self.load_conversations()
    
    def generate_conversation_title(self, message: str) -> str:
        prompt = f"""根据以下用户消息，生成一个简短、清晰的对话标题（不超过20字）：

用户消息：{message}

标题："""
        
        try:
            result = self.ai_service.generate_title(prompt)
            if result and result.strip():
                return result.strip()
        except Exception as e:
            self.log_message(f"生成标题失败: {str(e)}", "ERROR")
        
        return message[:20] if len(message) > 20 else message
    
    def save_conversations(self):
        try:
            import json
            with open("conversations.json", "w", encoding="utf-8") as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"保存对话失败: {str(e)}", "ERROR")
    
    def load_conversations_from_file(self):
        try:
            import json
            with open("conversations.json", "r", encoding="utf-8") as f:
                self.conversations = json.load(f)
        except FileNotFoundError:
            self.conversations = []
        except Exception as e:
            self.log_message(f"加载对话失败: {str(e)}", "ERROR")
            self.conversations = []
    
    def setup_ai_provider_section(self):
        provider_frame = ctk.CTkFrame(self.sidebar)
        provider_frame.pack(fill="x", padx=10, pady=5)
        
        provider_label = ctk.CTkLabel(
            provider_frame,
            text="AI提供者",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        provider_label.pack(pady=5)
        
        self.provider_combobox = ctk.CTkComboBox(
            provider_frame,
            values=["NVIDIA", "OpenAI", "Ollama", "Local", "自定义"],
            command=self.on_provider_change
        )
        self.provider_combobox.pack(pady=5, padx=5)
        
        self.base_url_entry = ctk.CTkEntry(
            provider_frame,
            placeholder_text="基础URL"
        )
        self.base_url_entry.pack(pady=2, padx=5)
        
        self.api_key_entry = ctk.CTkEntry(
            provider_frame,
            placeholder_text="API密钥",
            show="*"
        )
        self.api_key_entry.pack(pady=2, padx=5)

        # Local model selection
        self.local_model_label = ctk.CTkLabel(
            provider_frame,
            text="本地模型",
            font=ctk.CTkFont(size=12)
        )

        # 预定义模型列表（带系统要求）- 必须在这里定义，因为在combobox中要用
        self.predefined_models = [
            {"name": "Qwen2-0.5B", "id": "Qwen/Qwen2-0.5B-Instruct", "size": "~1GB", "memory": "2GB", "desc": "超轻量中文对话模型"},
            {"name": "DeepSeek-V4-Pro", "id": "deepseek-ai/DeepSeek-V4-Pro", "size": "~8GB", "memory": "10GB", "desc": "DeepSeek高性能模型"},
            {"name": "Qwen2-1.5B", "id": "Qwen/Qwen2-1.5B-Instruct", "size": "~3GB", "memory": "4GB", "desc": "轻量中文对话模型"},
            {"name": "Phi-3-mini", "id": "microsoft/Phi-3-mini-4k-instruct", "size": "~8GB", "memory": "8GB", "desc": "微软轻量推理模型"},
            {"name": "Qwen2-0.5B-JPN", "id": "Qwen/Qwen2-0.5B-JPN-Instruct", "size": "~1GB", "memory": "2GB", "desc": "日语专项对话模型"},
            {"name": "Gemma-2B", "id": "google/gemma-2b-it", "size": "~5GB", "memory": "4GB", "desc": "谷歌轻量对话模型"},
        ]

        self.local_model_combobox = ctk.CTkComboBox(
            provider_frame,
            values=[m["name"] for m in self.predefined_models],
            state="disabled",
            command=self.on_local_model_select
        )
        self.local_model_label.pack(pady=2, padx=5)
        self.local_model_combobox.pack(pady=2, padx=5)

        # Model status label
        self.model_status_label = ctk.CTkLabel(
            provider_frame,
            text="",
            font=ctk.CTkFont(size=10)
        )
        self.model_status_label.pack(pady=2, padx=5)
        
        self.ollama_connect_frame = ctk.CTkFrame(provider_frame, fg_color="transparent")
        self.ollama_connect_frame.pack(pady=2, padx=5, fill="x")
        self.ollama_connect_frame.grid_columnconfigure(0, weight=1)
        
        self.ollama_model_label = ctk.CTkLabel(
            self.ollama_connect_frame,
            text="Ollama模型:"
        )
        self.ollama_model_label.grid(row=0, column=0, padx=2, sticky="w")
        
        self.ollama_model_combobox = ctk.CTkComboBox(
            self.ollama_connect_frame,
            values=["请先连接..."],
            state="readonly"
        )
        self.ollama_model_combobox.grid(row=0, column=1, padx=2, sticky="ew")
        
        self.connect_btn = ctk.CTkButton(
            provider_frame,
            text="连接",
            command=self.connect_provider,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.connect_btn.pack(pady=2, padx=5)
        
        self.model_entry = ctk.CTkEntry(
            provider_frame,
            placeholder_text="模型名称"
        )
        self.model_entry.pack(pady=2, padx=5)
        
        save_provider_btn = ctk.CTkButton(
            provider_frame,
            text="保存提供者设置",
            command=self.save_provider_settings
        )
        save_provider_btn.pack(pady=5, padx=5)
        
        self.provider_status_label = ctk.CTkLabel(
            provider_frame,
            text="状态: 未配置",
            text_color="gray"
        )
        self.provider_status_label.pack(pady=2)
        
    def setup_permission_section(self):
        permission_frame = ctk.CTkFrame(self.sidebar)
        permission_frame.pack(fill="x", padx=10, pady=5)
        
        permission_label = ctk.CTkLabel(
            permission_frame,
            text="权限级别",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        permission_label.pack(pady=5)
        
        self.permission_combobox = ctk.CTkComboBox(
            permission_frame,
            values=["无", "查看", "受限", "完整"],
            command=self.on_permission_change
        )
        self.permission_combobox.set("无")
        self.permission_combobox.pack(pady=5, padx=5)
        
    def setup_mode_section(self):
        mode_frame = ctk.CTkFrame(self.sidebar)
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        mode_label = ctk.CTkLabel(
            mode_frame,
            text="模式",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        mode_label.pack(pady=5)
        
        self.mode_combobox = ctk.CTkComboBox(
            mode_frame,
            values=["聊天模式", "控制模式"],
            command=self.on_mode_change
        )
        self.mode_combobox.set("聊天模式")
        self.mode_combobox.pack(pady=5, padx=5)
        
    def setup_iteration_section(self):
        iteration_frame = ctk.CTkFrame(self.sidebar)
        iteration_frame.pack(fill="x", padx=10, pady=5)
        
        iteration_label = ctk.CTkLabel(
            iteration_frame,
            text="自动轮回",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        iteration_label.pack(pady=5)
        
        self.max_calls_label = ctk.CTkLabel(
            iteration_frame,
            text="每分钟最大调用次数: 40"
        )
        self.max_calls_label.pack(pady=2)
        
        self.max_calls_slider = ctk.CTkSlider(
            iteration_frame,
            from_=1,
            to=120,
            number_of_steps=119,
            command=self.on_max_calls_change
        )
        self.max_calls_slider.set(40)
        self.max_calls_slider.pack(pady=2, padx=5)
        
        self.max_iterations_label = ctk.CTkLabel(
            iteration_frame,
            text="最大轮回次数: 10"
        )
        self.max_iterations_label.pack(pady=2)
        
        self.max_iterations_slider = ctk.CTkSlider(
            iteration_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            command=self.on_max_iterations_change
        )
        self.max_iterations_slider.set(10)
        self.max_iterations_slider.pack(pady=2, padx=5)
        
        self.delay_label = ctk.CTkLabel(
            iteration_frame,
            text="间隔时间(秒): 1.0"
        )
        self.delay_label.pack(pady=2)
        
        self.delay_slider = ctk.CTkSlider(
            iteration_frame,
            from_=0.1,
            to=10.0,
            number_of_steps=99,
            command=self.on_delay_change
        )
        self.delay_slider.set(1.0)
        self.delay_slider.pack(pady=2, padx=5)
        
        self.iteration_buttons_frame = ctk.CTkFrame(iteration_frame)
        self.iteration_buttons_frame.pack(pady=5)
        
        self.start_iteration_btn = ctk.CTkButton(
            self.iteration_buttons_frame,
            text="开始自动轮回",
            command=self.start_auto_iteration,
            fg_color="green"
        )
        self.start_iteration_btn.pack(side="left", padx=5)
        
        self.stop_iteration_btn = ctk.CTkButton(
            self.iteration_buttons_frame,
            text="停止轮回",
            command=self.stop_auto_iteration,
            fg_color="red",
            state="disabled"
        )
        self.stop_iteration_btn.pack(side="left", padx=5)
        
        self.iteration_status_label = ctk.CTkLabel(
            iteration_frame,
            text="轮回: 0/0 | 本分钟调用: 0",
            text_color="gray"
        )
        self.iteration_status_label.pack(pady=2)
        
    def setup_vision_section(self):
        vision_frame = ctk.CTkFrame(self.sidebar)
        vision_frame.pack(fill="x", padx=10, pady=5)
        
        vision_label = ctk.CTkLabel(
            vision_frame,
            text="视觉捕获",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        vision_label.pack(pady=5)
        
        self.vision_buttons_frame = ctk.CTkFrame(vision_frame)
        self.vision_buttons_frame.pack(pady=5)
        
        self.screenshot_btn = ctk.CTkButton(
            self.vision_buttons_frame,
            text="截图",
            command=self.take_screenshot
        )
        self.screenshot_btn.pack(side="left", padx=5)
        
        self.camera_btn = ctk.CTkButton(
            self.vision_buttons_frame,
            text="摄像头",
            command=self.open_camera
        )
        self.camera_btn.pack(side="left", padx=5)
        
    def setup_settings_button(self):
        """添加设置按钮"""
        settings_frame = ctk.CTkFrame(self.sidebar)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        self.settings_btn = ctk.CTkButton(
            settings_frame,
            text="⚙️ 设置",
            command=self.open_settings,
            width=260,
            fg_color="#4a90d9"
        )
        self.settings_btn.pack(pady=5)
        
    def open_settings(self):
        """打开设置窗口"""
        SettingsWindow(self.root)
        
    def setup_main_area(self):
        self.main_area = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)
        
        self.setup_chat_area()
        self.setup_log_area()
        self.setup_input_area()
        
    def setup_chat_area(self):
        self.chat_frame = ctk.CTkFrame(self.main_area)
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_controls_frame = ctk.CTkFrame(self.chat_frame)
        self.chat_controls_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        self.chat_controls_frame.grid_columnconfigure(0, weight=1)
        
        self.clear_history_btn = ctk.CTkButton(
            self.chat_controls_frame,
            text="清除历史",
            command=self.clear_conversation_history,
            width=100,
            fg_color="gray"
        )
        self.clear_history_btn.grid(row=0, column=1, padx=5, pady=2)
        
        self.history_status_label = ctk.CTkLabel(
            self.chat_controls_frame,
            text="历史消息: 0",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.history_status_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        
        self.chat_text = ctk.CTkTextbox(
            self.chat_frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.chat_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.chat_text.configure(state="disabled")
        
    def setup_input_area(self):
        self.input_frame = ctk.CTkFrame(self.main_area)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.input_text = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="在此输入消息...",
            font=ctk.CTkFont(size=12)
        )
        self.input_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.send_btn = ctk.CTkButton(
            self.input_frame,
            text="发送",
            command=self.send_message,
            width=100
        )
        self.send_btn.grid(row=0, column=1, padx=5, pady=5)
        
    def setup_log_area(self):
        self.log_frame = ctk.CTkFrame(self.main_area)
        self.log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_header_frame = ctk.CTkFrame(self.log_frame)
        self.log_header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        self.log_header_frame.grid_columnconfigure(0, weight=1)
        
        self.log_title_label = ctk.CTkLabel(
            self.log_header_frame,
            text="📋 调试日志",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.log_title_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        
        self.log_toggle_btn = ctk.CTkButton(
            self.log_header_frame,
            text="▼ 展开",
            command=self.toggle_log_panel,
            width=80,
            fg_color="gray"
        )
        self.log_toggle_btn.grid(row=0, column=1, padx=5, pady=2)
        
        self.clear_log_btn = ctk.CTkButton(
            self.log_header_frame,
            text="清空",
            command=self.clear_log,
            width=60,
            fg_color="gray"
        )
        self.clear_log_btn.grid(row=0, column=2, padx=5, pady=2)
        
        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=10),
            state="disabled"
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "日志窗口已就绪...\n")
        self.log_text.insert("end", "=" * 60 + "\n")
        self.log_text.configure(state="disabled")
        
        self.is_log_expanded = False
        
        self.log_frame.grid_rowconfigure(1, weight=0)
        self.log_text.grid_remove()
        
    def toggle_log_panel(self):
        if self.is_log_expanded:
            self.log_text.grid_remove()
            self.log_frame.grid_rowconfigure(1, weight=0)
            self.log_toggle_btn.configure(text="▶ 展开")
            self.is_log_expanded = False
        else:
            self.log_text.grid()
            self.log_frame.grid_rowconfigure(1, weight=1)
            self.log_toggle_btn.configure(text="▼ 收起")
            self.is_log_expanded = True
            self.log_text.see("end")
    
    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "日志已清空\n")
        self.log_text.insert("end", "=" * 60 + "\n")
        self.log_text.configure(state="disabled")
    
    def log_message(self, message: str, level: str = "INFO"):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_text.configure(state="normal")
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
        if level == "ERROR":
            self.log_text.configure(state="normal")
            self.log_text.tag_add("error", "end-2l", "end-1l")
            self.log_text.tag_config("error", foreground="red")
            self.log_text.configure(state="disabled")
        elif level == "SUCCESS":
            self.log_text.configure(state="normal")
            self.log_text.tag_add("success", "end-2l", "end-1l")
            self.log_text.tag_config("success", foreground="green")
            self.log_text.configure(state="disabled")
        elif level == "RAW":
            self.log_text.configure(state="normal")
            self.log_text.insert("end", "\n")
            self.log_text.configure(state="disabled")
        
    def log_raw(self, data: str, title: str = ""):
        self.log_text.configure(state="normal")
        if title:
            self.log_text.insert("end", f"\n{'=' * 60}\n")
            self.log_text.insert("end", f"📥 {title}\n")
            self.log_text.insert("end", f"{'=' * 60}\n")
        self.log_text.insert("end", data)
        self.log_text.insert("end", f"\n{'=' * 60}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
    def setup_bindings(self):
        self.root.bind("<Return>", lambda e: self.send_message())
        self.input_text.bind("<Return>", lambda e: self.send_message())
        
    def process_queue(self):
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self.append_message(message)
        except queue.Empty:
            pass
        
        if self.is_running:
            self.root.after(100, self.process_queue)
    
    def append_message(self, message: str, color: str = "white"):
        self.chat_text.configure(state="normal")
        
        rendered_message = self.markdown_renderer.simplify_markdown(message)
        self.chat_text.insert("end", rendered_message + "\n\n")
        
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")
        self.update_history_status()
    
    def load_default_provider_config(self):
        default_provider = "NVIDIA"
        provider = self.ai_provider_manager.get_provider(default_provider)
        if provider:
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.insert(0, provider.base_url)
            
            self.api_key_entry.delete(0, "end")
            self.api_key_entry.insert(0, provider.api_key)
            
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, provider.default_model)
            
            self.provider_combobox.set(default_provider)
            
            if provider.default_model:
                self.provider_status_label.configure(
                    text="状态: 已配置",
                    text_color="green"
                )
            else:
                self.provider_status_label.configure(
                    text="状态: 未配置",
                    text_color="gray"
                )
    
    def on_provider_change(self, value: str):
        if hasattr(self, 'ollama_connect_frame'):
            self.ollama_connect_frame.pack_forget()
        if hasattr(self, 'connect_btn'):
            self.connect_btn.pack_forget()

        # 重置所有控件状态
        self.base_url_entry.configure(state="normal")
        self.api_key_entry.configure(state="normal")
        if hasattr(self, 'local_model_label'):
            self.local_model_label.configure(state="disabled")
        if hasattr(self, 'local_model_combobox'):
            self.local_model_combobox.configure(state="disabled")
        if hasattr(self, 'model_status_label'):
            self.model_status_label.configure(text="")

        provider = self.ai_provider_manager.get_provider(value)
        if provider:
            if value == "Local":
                # Local提供者隐藏API配置，显示本地模型选择
                self.base_url_entry.delete(0, "end")
                self.base_url_entry.insert(0, "本地模型")
                self.base_url_entry.configure(state="disabled")
                self.api_key_entry.delete(0, "end")
                self.api_key_entry.configure(state="disabled")
                self.model_entry.delete(0, "end")
                self.model_entry.insert(0, provider.default_model)
                # 显示本地模型选择
                if hasattr(self, 'local_model_label'):
                    self.local_model_label.configure(state="normal")
                if hasattr(self, 'local_model_combobox'):
                    self.local_model_combobox.configure(state="normal")
                    self.local_model_combobox.set(provider.default_model)
                # 加载本地模型信息
                self.load_local_model_info()
            elif value == "Ollama":
                # Ollama需要连接操作
                self.base_url_entry.delete(0, "end")
                self.base_url_entry.insert(0, provider.base_url)
                self.api_key_entry.delete(0, "end")
                self.api_key_entry.insert(0, provider.api_key)
                self.model_entry.delete(0, "end")
                self.model_entry.insert(0, provider.default_model)
                if hasattr(self, 'ollama_connect_frame'):
                    self.connect_btn.pack(pady=2, padx=5, before=self.model_entry)
                    self.ollama_connect_frame.pack(pady=2, padx=5, fill="x")
                    self.ollama_model_combobox.set("请先连接...")
            else:
                # 其他提供者（NVIDIA, OpenAI, 自定义）
                self.base_url_entry.delete(0, "end")
                self.base_url_entry.insert(0, provider.base_url)
                self.api_key_entry.delete(0, "end")
                self.api_key_entry.insert(0, provider.api_key)
                self.model_entry.delete(0, "end")
                self.model_entry.insert(0, provider.default_model)

    def on_local_model_select(self, model_name: str):
        """下拉框选择本地模型"""
        self.log_message(f"选择本地模型: {model_name}", "INFO")
        if hasattr(self, 'model_entry'):
            model_id = model_name
            for m in self.predefined_models:
                if m["name"] == model_name:
                    model_id = m["id"]
                    break
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, model_id)

    def load_local_model_info(self):
        """加载本地模型信息"""
        if not hasattr(self, 'local_model_service'):
            return
        try:
            models = self.local_model_service.list_models()
            if models:
                model_list = [f"{m['name']} ({m['size']}) - {'已下载' if m['is_downloaded'] else '未下载'})" for m in models]
                self.log_message(f"本地模型列表: {', '.join([m['name'] for m in models])}", "INFO")
            else:
                self.log_message("未找到已下载的本地模型", "WARNING")
        except Exception as e:
            self.log_message(f"加载本地模型信息失败: {str(e)}", "ERROR")

    def on_model_load_progress(self, progress_info: Dict[str, Any]):
        """模型加载进度回调"""
        try:
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                return
                
            status = progress_info.get("status", "")
            message = progress_info.get("message", "")
            if status == "downloading":
                self.log_message(f"下载模型: {message}", "INFO")
                if hasattr(self, 'model_status_label'):
                    self.model_status_label.configure(text=f"下载中: {message}", text_color="orange")
            elif status == "loading":
                self.log_message(f"加载模型: {message}", "INFO")
                if hasattr(self, 'model_status_label'):
                    self.model_status_label.configure(text=f"加载中: {message}", text_color="orange")
            elif status == "complete":
                self.log_message(f"✓ {message}", "SUCCESS")
                if hasattr(self, 'model_status_label'):
                    self.model_status_label.configure(text="模型已就绪", text_color="green")
            elif status == "error":
                self.log_message(f"✗ {message}", "ERROR")
                if hasattr(self, 'model_status_label'):
                    self.model_status_label.configure(text=f"错误: {message}", text_color="red")
        except:
            pass

    def connect_provider(self):
        provider_name = self.provider_combobox.get()
        
        if provider_name == "Ollama":
            base_url = self.base_url_entry.get().strip()
            if not base_url:
                messagebox.showerror("错误", "请输入Ollama服务地址")
                return
            
            self.connect_btn.configure(state="disabled", text="连接中...")
            self.root.update()
            
            self.ai_service.set_provider(
                provider_name="Ollama",
                base_url=base_url,
                api_key="",
                default_model=""
            )
            
            models = self.ai_service.list_ollama_models()
            
            if models:
                self.ollama_model_combobox.configure(values=models)
                self.ollama_model_combobox.set(models[0])
                self.model_entry.delete(0, "end")
                self.model_entry.insert(0, models[0])
                self.provider_status_label.configure(text="状态: 已连接", text_color="green")
                self.log_message(f"Ollama连接成功，找到{len(models)}个模型", "SUCCESS")
            else:
                self.ollama_model_combobox.configure(values=["未找到模型"])
                self.ollama_model_combobox.set("未找到模型")
                self.provider_status_label.configure(text="状态: 未找到模型", text_color="orange")
                self.log_message("Ollama连接失败或未找到模型", "ERROR")
            
            self.connect_btn.configure(state="normal", text="连接")
        else:
            self.save_provider_settings()
    
    def save_provider_settings(self):
        provider_name = self.provider_combobox.get()
        base_url = self.base_url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        model = self.model_entry.get().strip()

        if provider_name == "Local":
            # Local提供者使用本地模型
            model = self.local_model_combobox.get().strip() if hasattr(self, 'local_model_combobox') else model
            if not model:
                messagebox.showerror("错误", "请选择或输入本地模型")
                return
            # 查找模型ID
            model_id = model
            for m in self.predefined_models:
                if m["name"] == model:
                    model_id = m["id"]
                    break
            base_url = "local"
            api_key = ""
            # 加载本地模型
            if hasattr(self, 'local_model_service'):
                result = self.local_model_service.load_model(model_id, self.on_model_load_progress)
                if result["success"]:
                    self.log_message(result["message"], "INFO")
                    # 将UI中的local_model_service传递给AIService
                    self.ai_service.set_local_model_service(self.local_model_service)
                else:
                    self.log_message(result["message"], "ERROR")
        elif provider_name == "Ollama":
            if not base_url:
                messagebox.showerror("错误", "请输入Ollama服务地址")
                return
            model = self.ollama_model_combobox.get()
            if model == "请先连接..." or model == "未找到模型":
                messagebox.showerror("错误", "请先连接Ollama并获取模型列表")
                return
            api_key = ""
        else:
            if not base_url or not model:
                messagebox.showerror("错误", "请填写所有字段")
                return

        try:
            self.ai_service.set_provider(
                provider_name=provider_name,
                base_url=base_url,
                api_key=api_key,
                model=model
            )

            self.ai_provider_manager.update_provider(
                provider_name,
                base_url=base_url,
                api_key=api_key,
                default_model=model
            )

            self.provider_status_label.configure(
                text="状态: 已连接",
                text_color="green"
            )
            self.append_message(f"✓ AI提供者 '{provider_name}' 配置成功")
            
        except Exception as e:
            messagebox.showerror("错误", f"配置提供者失败: {str(e)}")
            self.provider_status_label.configure(
                text="状态: 失败",
                text_color="red"
            )
    
    def on_permission_change(self, value: str):
        self.append_message(f"权限级别已更改为: {value}")
        self.ai_service.set_permission_level(value)
    
    def on_mode_change(self, value: str):
        self.append_message(f"模式已更改为: {value}")
    
    def on_max_calls_change(self, value: float):
        self.max_calls_label.configure(text=f"每分钟最大调用次数: {int(value)}")
    
    def on_max_iterations_change(self, value: float):
        self.max_iterations_label.configure(text=f"最大轮回次数: {int(value)}")
    
    def on_delay_change(self, value: float):
        self.delay_label.configure(text=f"间隔时间(秒): {value:.1f}")
    
    def send_message(self):
        message = self.input_text.get().strip()
        if not message:
            return
        
        self.input_text.delete(0, "end")
        
        self.append_message(f"你: {message}")
        self.log_message(f"发送消息: {message[:100]}...", "INFO")
        
        self.update_conversation_title()
        
        threading.Thread(
            target=self._process_message,
            args=(message,),
            daemon=True
        ).start()
    
    def remove_thinking_message(self):
        self.chat_text.configure(state="normal")
        content = self.chat_text.get("1.0", "end-1c")
        if content.endswith("AI: ⏳ 正在思考..."):
            self.chat_text.delete("end-20c", "end")
        elif "AI: ⏳ 正在思考..." in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip() == "AI: ⏳ 正在思考...":
                    lines[i] = ""
                    break
            self.chat_text.delete("1.0", "end")
            self.chat_text.insert("1.0", "\n".join(lines))
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")
    
    def _process_message(self, message: str):
        try:
            self.log_message("开始处理消息...", "INFO")
            
            self.message_queue.put("AI: ⏳ 正在思考...")
            
            response = ""
            reasoning = ""
            
            mode = self.mode_combobox.get()
            if mode == "控制模式":
                stream_method = lambda msg: self.ai_service.stream_chat_with_control(msg, enable_loop=True, max_loops=10)
            else:
                stream_method = self.ai_service.stream_chat
            
            full_raw_response = ""
            
            first_chunk = True
            for chunk in stream_method(message):
                if first_chunk:
                    self.remove_thinking_message()
                    first_chunk = False
                
                if "reasoning_content" in chunk:
                    reasoning += chunk["reasoning_content"]
                if "content" in chunk:
                    content = chunk["content"]
                    response += content
                    full_raw_response += content
            
            if reasoning:
                self.log_raw(reasoning, "AI 思考过程")
                self.message_queue.put(f"\033[90m{reasoning}\033[0m")
            
            if response:
                self.log_raw(response, "AI 原始响应")
                self.message_queue.put(f"AI: {response}")
                
        except Exception as e:
            self.log_message(f"处理消息错误: {str(e)}", "ERROR")
            logger.error(f"处理消息错误: {e}")
            self.message_queue.put(f"错误: {str(e)}")
    
    def start_auto_iteration(self):
        if self.is_iterating:
            return
        
        self.is_iterating = True
        self.current_iteration = 0
        self.start_iteration_btn.configure(state="disabled")
        self.stop_iteration_btn.configure(state="normal")
        
        max_iterations = int(self.max_iterations_slider.get())
        delay = self.delay_slider.get()
        
        self.append_message(f"开始自动轮回 (最大: {max_iterations}, 间隔: {delay}秒)")
        
        threading.Thread(
            target=self._run_auto_iteration,
            args=(max_iterations, delay),
            daemon=True
        ).start()
    
    def _run_auto_iteration(self, max_iterations: int, delay: float):
        while self.is_iterating and self.current_iteration < max_iterations:
            self.current_iteration += 1
            
            self.message_queue.put(f"\n--- 轮回 {self.current_iteration}/{max_iterations} ---")
            self.log_message(f"开始轮回 {self.current_iteration}/{max_iterations}", "INFO")
            
            try:
                response = ""
                reasoning = ""
                
                mode = self.mode_combobox.get()
                if mode == "控制模式":
                    stream_method = lambda msg: self.ai_service.stream_chat_with_control(msg, enable_loop=True, max_loops=10)
                else:
                    stream_method = self.ai_service.stream_chat
                
                full_raw_response = ""
                
                for chunk in stream_method("继续下一步"):
                    if "reasoning_content" in chunk:
                        reasoning += chunk["reasoning_content"]
                    if "content" in chunk:
                        content = chunk["content"]
                        response += content
                        full_raw_response += content
                
                if reasoning:
                    self.log_raw(reasoning, f"轮回 {self.current_iteration} - AI 思考过程")
                    self.message_queue.put(f"\033[90m{reasoning}\033[0m")
                
                if response:
                    self.log_raw(response, f"轮回 {self.current_iteration} - AI 响应")
                    self.message_queue.put(f"AI: {response}")
                    
            except Exception as e:
                self.log_message(f"轮回 {self.current_iteration} 错误: {str(e)}", "ERROR")
                logger.error(f"轮回 {self.current_iteration} 错误: {e}")
                self.message_queue.put(f"轮回 {self.current_iteration} 错误: {str(e)}")
                break
            
            time.sleep(delay)
        
        self.is_iterating = False
        self.start_iteration_btn.configure(state="normal")
        self.stop_iteration_btn.configure(state="disabled")
        self.message_queue.put(f"\n自动轮回完成 ({self.current_iteration}/{max_iterations})")
    
    def stop_auto_iteration(self):
        self.is_iterating = False
        self.start_iteration_btn.configure(state="normal")
        self.stop_iteration_btn.configure(state="disabled")
        self.append_message("自动轮回已停止")
    
    def clear_conversation_history(self):
        self.ai_service.clear_history()
        self._clear_chat_text()
        self.history_status_label.configure(text="历史消息: 0")
        self.append_message("对话历史已清除")
    
    def _clear_chat_text(self):
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        self.chat_text.configure(state="disabled")
    
    def update_history_status(self):
        history_length = self.ai_service.get_history_length()
        self.history_status_label.configure(text=f"历史消息: {history_length}")
    
    def take_screenshot(self):
        try:
            self.append_message("📷 正在截取并分析屏幕...")
            result = self.ai_service.system_controller.capture_and_analyze_screen(ascii_width=60)
            
            if result["success"]:
                self.append_message(f"✓ {result['message']}")
                self.append_message("\n" + result["data"]["analysis"])
            else:
                self.append_message(f"✗ {result['message']}")
        except Exception as e:
            messagebox.showerror("错误", f"截图分析失败: {str(e)}")
    
    def open_camera(self):
        try:
            self.append_message("正在打开摄像头...")
            camera_frame = self.vision_capture.capture_camera()
            self.append_message(f"✓ 摄像头画面已捕获: {camera_frame}")
        except Exception as e:
            messagebox.showerror("错误", f"打开摄像头失败: {str(e)}")
    
    def on_closing(self):
        """关闭窗口时最小化到系统托盘"""
        # 保存对话
        if self.conversations:
            self.conversations[self.current_conversation]["messages"] = self.get_current_messages()
            self.save_conversations()
        
        # 隐藏主窗口
        self.root.withdraw()
        
        # 确保托盘图标运行
        if not self.tray_icon or not self.tray_icon.visible:
            self._create_tray_icon()
        
        # 显示提示
        self.tray_icon.notify("AI电脑控制", "应用已最小化到系统托盘")
    
    def _create_tray_icon(self):
        """创建系统托盘图标"""
        try:
            # 创建图标（使用简单的文本图标）
            icon_image = self._create_simple_icon()
            
            # 创建菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self._show_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("关闭", self._quit_application)
            )
            
            # 创建托盘图标
            self.tray_icon = pystray.Icon("AI电脑控制", icon_image, "AI电脑控制", menu)
            
            # 在后台线程中运行托盘图标
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
        except Exception as e:
            logger.error(f"创建系统托盘失败: {e}")
    
    def _create_simple_icon(self):
        """创建简单的图标"""
        # 创建一个简单的256x256像素图像
        img = Image.new('RGB', (64, 64), color=(45, 45, 45))
        # 添加一些简单的图形
        for i in range(16):
            for j in range(16):
                if (i + j) % 3 == 0:
                    img.putpixel((i * 4, j * 4), (0, 255, 0))
                    img.putpixel((i * 4 + 1, j * 4), (0, 255, 0))
                    img.putpixel((i * 4, j * 4 + 1), (0, 255, 0))
                    img.putpixel((i * 4 + 1, j * 4 + 1), (0, 255, 0))
        return img
    
    def _show_window(self, icon=None, item=None):
        """显示主窗口"""
        self.root.deiconify()
        self.root.lift()
    
    def _quit_application(self, icon=None, item=None):
        """真正退出应用程序"""
        self.is_running = False
        self.is_iterating = False
        
        # 保存对话
        if self.conversations:
            self.conversations[self.current_conversation]["messages"] = self.get_current_messages()
            self.save_conversations()
        
        # 停止WebSocket服务器
        if self.websocket_server:
            self.websocket_server.stop()
            print("WebSocket服务器已停止")
        
        # 停止托盘图标
        if self.tray_icon:
            self.tray_icon.stop()
        
        # 销毁主窗口
        self.root.destroy()
        
        # 退出程序
        sys.exit(0)
    
    def run(self):
        self.root.mainloop()


class SettingsWindow:
    """设置窗口类"""
    
    def __init__(self, parent):
        self.parent = parent
        self.settings_window = ctk.CTkToplevel(parent)
        self.settings_window.title("设置")
        self.settings_window.geometry("900x700")
        self.settings_window.attributes("-topmost", True)
        
        # 居中显示
        screen_width = self.settings_window.winfo_screenwidth()
        screen_height = self.settings_window.winfo_screenheight()
        x = (screen_width - 900) // 2
        y = (screen_height - 700) // 2
        self.settings_window.geometry(f"900x700+{x}+{y}")
        
        # 创建主框架
        self.main_frame = ctk.CTkFrame(self.settings_window)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 创建标签页
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True)
        
        # 添加标签页
        self.tab_function = self.tabview.add("功能设置")
        self.tab_pc_status = self.tabview.add("电脑状态")
        self.tab_ai_mode = self.tabview.add("AI模式")
        self.tab_developer = self.tabview.add("开发者模式")
        self.tab_interface = self.tabview.add("界面设置")
        self.tab_advanced = self.tabview.add("高级设置")
        
        # 设置各标签页内容
        self.setup_function_tab()
        self.setup_pc_status_tab()
        self.setup_ai_mode_tab()
        self.setup_developer_tab()
        self.setup_interface_tab()
        self.setup_advanced_tab()
        
        # 底部按钮
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", pady=10)
        
        self.reset_btn = ctk.CTkButton(
            self.button_frame,
            text="恢复默认",
            command=self.reset_settings,
            fg_color="orange"
        )
        self.reset_btn.pack(side="left", padx=5)
        
        self.export_btn = ctk.CTkButton(
            self.button_frame,
            text="导出设置",
            command=self.export_settings
        )
        self.export_btn.pack(side="left", padx=5)
        
        self.save_btn = ctk.CTkButton(
            self.button_frame,
            text="保存设置",
            command=self.save_settings,
            fg_color="green"
        )
        self.save_btn.pack(side="right", padx=5)
        
        self.close_btn = ctk.CTkButton(
            self.button_frame,
            text="关闭",
            command=self.close_window
        )
        self.close_btn.pack(side="right", padx=5)
        
        # 加载设置
        self.load_settings()
    
    def setup_function_tab(self):
        """功能设置标签页"""
        self.tab_function.grid_columnconfigure(0, weight=1)
        self.tab_function.grid_rowconfigure(0, weight=1)
        
        # 创建滚动框架
        scroll_frame = ctk.CTkScrollableFrame(self.tab_function)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用滚动框架作为容器
        container = scroll_frame
        
        # 功能分类数据
        categories = [
            {
                "name": "核心功能",
                "functions": [
                    {"name": "自动轮回", "desc": "启用自动轮回功能", "default": True},
                    {"name": "视觉捕获", "desc": "启用截图和摄像头功能", "default": True},
                    {"name": "系统控制", "desc": "启用系统控制功能", "default": True},
                    {"name": "鼠标控制", "desc": "启用鼠标控制功能", "default": True},
                    {"name": "键盘控制", "desc": "启用键盘控制功能", "default": True},
                ]
            },
            {
                "name": "文件与数据",
                "functions": [
                    {"name": "文件操作", "desc": "启用文件读写功能", "default": True},
                    {"name": "文档处理", "desc": "启用办公文档处理功能", "default": True},
                    {"name": "数据可视化", "desc": "启用数据图表生成功能", "default": True},
                    {"name": "数据库访问", "desc": "启用数据库读写功能", "default": False},
                ]
            },
            {
                "name": "网络与通信",
                "functions": [
                    {"name": "网络请求", "desc": "启用网络请求功能", "default": True},
                    {"name": "命令执行", "desc": "启用命令行执行功能", "default": False},
                    {"name": "SSH连接", "desc": "启用SSH远程连接功能", "default": False},
                ]
            },
            {
                "name": "多媒体处理",
                "functions": [
                    {"name": "音频处理", "desc": "启用音频录制和处理功能", "default": True},
                    {"name": "视频处理", "desc": "启用视频剪辑和合成功能", "default": True},
                    {"name": "图像识别", "desc": "启用图像分析和识别功能", "default": True},
                    {"name": "语音合成", "desc": "启用文字转语音功能", "default": True},
                ]
            },
            {
                "name": "AI增强",
                "functions": [
                    {"name": "知识库检索", "desc": "启用本地知识库检索功能", "default": True},
                    {"name": "长对话记忆", "desc": "启用长对话上下文记忆", "default": True},
                    {"name": "插件扩展", "desc": "启用插件系统", "default": False},
                ]
            }
        ]
        
        self.function_vars = {}
        row = 0
        
        # 遍历分类并添加到滚动框架的内部容器
        for category in categories:
            # 分类标题
            cat_label = ctk.CTkLabel(
                container,
                text=category["name"],
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#4a90d9"
            )
            cat_label.grid(row=row, column=0, sticky="w", padx=5, pady=(10, 5))
            row += 1
            
            # 功能项
            for func in category["functions"]:
                func_frame = ctk.CTkFrame(container)
                func_frame.grid(row=row, column=0, sticky="ew", pady=2, padx=5)
                func_frame.grid_columnconfigure(0, weight=1)
                
                var = ctk.BooleanVar(value=func["default"])
                self.function_vars[func["name"]] = var
                
                label = ctk.CTkLabel(func_frame, text=func["name"], font=ctk.CTkFont(size=12))
                label.grid(row=0, column=0, sticky="w", padx=5)
                
                desc_label = ctk.CTkLabel(func_frame, text=func["desc"], text_color="gray", font=ctk.CTkFont(size=10))
                desc_label.grid(row=1, column=0, sticky="w", padx=5)
                
                switch = ctk.CTkSwitch(func_frame, variable=var)
                switch.grid(row=0, column=1, sticky="e", padx=5)
                
                row += 1

    def setup_pc_status_tab(self):
        """电脑状态标签页"""
        self.tab_pc_status.grid_columnconfigure(0, weight=1)
        self.tab_pc_status.grid_rowconfigure(0, weight=1)
        
        # 状态显示框架（滚动框架）
        scroll_frame = ctk.CTkScrollableFrame(self.tab_pc_status)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用滚动框架作为容器
        status_frame = scroll_frame
        
        # 获取系统信息
        import psutil
        
        # CPU信息
        cpu_frame = ctk.CTkFrame(status_frame)
        cpu_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(cpu_frame, text="CPU信息", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=5)
        ctk.CTkLabel(cpu_frame, text=f"CPU核心数: {psutil.cpu_count(logical=True)}").pack(pady=2)
        ctk.CTkLabel(cpu_frame, text=f"CPU使用率: {psutil.cpu_percent()}%").pack(pady=2)
        
        # 内存信息
        mem = psutil.virtual_memory()
        mem_frame = ctk.CTkFrame(status_frame)
        mem_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(mem_frame, text="内存信息", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=5)
        ctk.CTkLabel(mem_frame, text=f"总内存: {self._format_size(mem.total)}").pack(pady=2)
        ctk.CTkLabel(mem_frame, text=f"已使用: {self._format_size(mem.used)} ({mem.percent}%)").pack(pady=2)
        ctk.CTkLabel(mem_frame, text=f"可用内存: {self._format_size(mem.available)}").pack(pady=2)
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_frame = ctk.CTkFrame(status_frame)
        disk_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(disk_frame, text="磁盘信息", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=5)
        ctk.CTkLabel(disk_frame, text=f"总容量: {self._format_size(disk.total)}").pack(pady=2)
        ctk.CTkLabel(disk_frame, text=f"已使用: {self._format_size(disk.used)} ({disk.percent}%)").pack(pady=2)
        ctk.CTkLabel(disk_frame, text=f"可用空间: {self._format_size(disk.free)}").pack(pady=2)
        
        # 网络信息
        net = psutil.net_io_counters()
        net_frame = ctk.CTkFrame(status_frame)
        net_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(net_frame, text="网络信息", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=5)
        ctk.CTkLabel(net_frame, text=f"已发送: {self._format_size(net.bytes_sent)}").pack(pady=2)
        ctk.CTkLabel(net_frame, text=f"已接收: {self._format_size(net.bytes_recv)}").pack(pady=2)
        
        # 进程信息
        proc_frame = ctk.CTkFrame(status_frame)
        proc_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(proc_frame, text="进程信息", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=5)
        ctk.CTkLabel(proc_frame, text=f"当前进程数: {len(psutil.pids())}").pack(pady=2)
        
        # 更新按钮（放在滚动框架外）
        refresh_btn = ctk.CTkButton(
            self.tab_pc_status,
            text="刷新状态",
            command=self.refresh_pc_status
        )
        refresh_btn.grid(row=1, column=0, pady=5)
    
    def setup_ai_mode_tab(self):
        """AI模式设置标签页"""
        self.tab_ai_mode.grid_columnconfigure(0, weight=1)
        self.tab_ai_mode.grid_rowconfigure(0, weight=1)
        
        # 创建滚动框架
        scroll_frame = ctk.CTkScrollableFrame(self.tab_ai_mode)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用滚动框架作为容器
        container = scroll_frame
        
        # AI模式选择
        mode_frame = ctk.CTkFrame(container)
        mode_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(mode_frame, text="AI模式", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.ai_mode_var = ctk.StringVar(value="balanced")
        modes = [
            ("聊天模式", "chat", "专注于对话交互，适合日常聊天"),
            ("控制模式", "control", "专注于系统控制，适合自动化操作"),
            ("创作模式", "creative", "专注于内容创作，适合写作和创意生成"),
            ("平衡模式", "balanced", "综合模式，兼顾各种功能"),
        ]
        
        for name, value, desc in modes:
            radio = ctk.CTkRadioButton(
                mode_frame,
                text=name,
                variable=self.ai_mode_var,
                value=value
            )
            radio.pack(anchor="w", padx=10, pady=2)
            ctk.CTkLabel(mode_frame, text=desc, text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=1)
        
        # 响应速度设置
        speed_frame = ctk.CTkFrame(container)
        speed_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(speed_frame, text="响应速度", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            command=self.on_speed_change
        )
        self.speed_slider.set(5)
        self.speed_slider.pack(pady=5, padx=5)
        self.speed_label = ctk.CTkLabel(speed_frame, text="中等")
        self.speed_label.pack(pady=2)
        
        # 输出格式设置
        format_frame = ctk.CTkFrame(container)
        format_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(format_frame, text="输出格式", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.markdown_var = ctk.BooleanVar(value=True)
        markdown_switch = ctk.CTkSwitch(format_frame, text="启用Markdown格式", variable=self.markdown_var)
        markdown_switch.pack(pady=2)
        
        self.code_var = ctk.BooleanVar(value=True)
        code_switch = ctk.CTkSwitch(format_frame, text="启用代码高亮", variable=self.code_var)
        code_switch.pack(pady=2)
        
        # 对话历史设置
        history_frame = ctk.CTkFrame(container)
        history_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(history_frame, text="对话历史", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.max_history_var = ctk.IntVar(value=100)
        history_slider = ctk.CTkSlider(
            history_frame,
            from_=10,
            to=500,
            number_of_steps=49,
            variable=self.max_history_var
        )
        history_slider.pack(pady=5, padx=5)
        self.max_history_label = ctk.CTkLabel(history_frame, text="最大历史记录数: 100")
        self.max_history_label.pack(pady=2)
        history_slider.configure(command=self.on_history_change)
    
    def on_history_change(self, value):
        """历史记录数变化"""
        self.max_history_label.configure(text=f"最大历史记录数: {int(value)}")
    
    def setup_developer_tab(self):
        """开发者模式标签页"""
        self.tab_developer.grid_columnconfigure(0, weight=1)
        self.tab_developer.grid_rowconfigure(0, weight=1)
        
        # 创建滚动框架
        scroll_frame = ctk.CTkScrollableFrame(self.tab_developer)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用滚动框架作为容器
        container = scroll_frame
        
        # 开发者模式开关
        dev_mode_frame = ctk.CTkFrame(container)
        dev_mode_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(dev_mode_frame, text="开发者模式", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.dev_mode_var = ctk.BooleanVar(value=False)
        dev_switch = ctk.CTkSwitch(dev_mode_frame, text="启用开发者模式", variable=self.dev_mode_var)
        dev_switch.pack(pady=5)
        
        # 日志级别设置
        log_frame = ctk.CTkFrame(container)
        log_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(log_frame, text="日志级别", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.log_level_var = ctk.StringVar(value="INFO")
        log_levels = [
            ("DEBUG", "详细调试信息"),
            ("INFO", "一般信息"),
            ("WARNING", "警告信息"),
            ("ERROR", "错误信息"),
        ]
        
        for value, desc in log_levels:
            radio = ctk.CTkRadioButton(
                log_frame,
                text=f"{value} - {desc}",
                variable=self.log_level_var,
                value=value
            )
            radio.pack(anchor="w", padx=10, pady=2)
        
        # 控制台输出设置
        console_frame = ctk.CTkFrame(container)
        console_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(console_frame, text="控制台输出", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.console_log_var = ctk.BooleanVar(value=True)
        console_switch = ctk.CTkSwitch(console_frame, text="启用控制台日志输出", variable=self.console_log_var)
        console_switch.pack(pady=2)
        
        self.console_debug_var = ctk.BooleanVar(value=False)
        debug_switch = ctk.CTkSwitch(console_frame, text="显示调试信息", variable=self.console_debug_var)
        debug_switch.pack(pady=2)
        
        self.console_timing_var = ctk.BooleanVar(value=False)
        timing_switch = ctk.CTkSwitch(console_frame, text="显示执行时间", variable=self.console_timing_var)
        timing_switch.pack(pady=2)
        
        self.console_request_var = ctk.BooleanVar(value=False)
        request_switch = ctk.CTkSwitch(console_frame, text="显示网络请求详情", variable=self.console_request_var)
        request_switch.pack(pady=2)
        
        # API调试
        api_frame = ctk.CTkFrame(container)
        api_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(api_frame, text="API调试", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.api_debug_var = ctk.BooleanVar(value=False)
        api_switch = ctk.CTkSwitch(api_frame, text="启用API调试模式", variable=self.api_debug_var)
        api_switch.pack(pady=2)
        
        self.api_log_var = ctk.BooleanVar(value=False)
        api_log_switch = ctk.CTkSwitch(api_frame, text="记录API请求/响应", variable=self.api_log_var)
        api_log_switch.pack(pady=2)
        
        # 性能分析
        perf_frame = ctk.CTkFrame(container)
        perf_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(perf_frame, text="性能分析", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.perf_profiling_var = ctk.BooleanVar(value=False)
        perf_switch = ctk.CTkSwitch(perf_frame, text="启用性能分析", variable=self.perf_profiling_var)
        perf_switch.pack(pady=2)
        
        self.memory_log_var = ctk.BooleanVar(value=False)
        memory_switch = ctk.CTkSwitch(perf_frame, text="记录内存使用", variable=self.memory_log_var)
        memory_switch.pack(pady=2)
    
    def setup_interface_tab(self):
        """界面设置标签页"""
        self.tab_interface.grid_columnconfigure(0, weight=1)
        self.tab_interface.grid_rowconfigure(0, weight=1)
        
        # 创建滚动框架
        scroll_frame = ctk.CTkScrollableFrame(self.tab_interface)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用滚动框架作为容器
        container = scroll_frame
        
        # 主题设置
        theme_frame = ctk.CTkFrame(container)
        theme_frame.pack(fill="both", expand=True, pady=10, padx=5)
        
        # 主题选择框架
        theme_select_frame = ctk.CTkFrame(theme_frame)
        theme_select_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(theme_select_frame, text="主题设置", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5, anchor="w")
        
        # 主题列表
        from src.config import theme_manager
        theme_manager.load_all_themes()
        self.theme_names = theme_manager.get_theme_names()
        
        self.theme_combobox = ctk.CTkComboBox(
            theme_select_frame,
            values=self.theme_names,
            width=250
        )
        self.theme_combobox.pack(pady=5)
        
        # 设置当前主题
        if settings.theme_name in self.theme_names:
            self.theme_combobox.set(settings.theme_name)
        
        # 操作按钮
        theme_btn_frame = ctk.CTkFrame(theme_select_frame)
        theme_btn_frame.pack(fill="x", pady=5)
        
        self.refresh_theme_btn = ctk.CTkButton(
            theme_btn_frame,
            text="刷新主题",
            command=self.refresh_themes,
            width=100
        )
        self.refresh_theme_btn.pack(side="left", padx=5)
        
        self.apply_theme_btn = ctk.CTkButton(
            theme_btn_frame,
            text="应用主题",
            command=self.apply_theme,
            width=100
        )
        self.apply_theme_btn.pack(side="left", padx=5)
        
        # 主题预览
        preview_frame = ctk.CTkFrame(theme_select_frame)
        preview_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(preview_frame, text="主题预览", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=5, anchor="w")
        
        # 暗色模式预览
        dark_preview_frame = ctk.CTkFrame(preview_frame)
        dark_preview_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(dark_preview_frame, text="暗色模式", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=2)
        self.dark_preview_frame = ctk.CTkFrame(dark_preview_frame, height=40, corner_radius=8)
        self.dark_preview_frame.pack(fill="x", pady=2)
        
        # 亮色模式预览
        light_preview_frame = ctk.CTkFrame(preview_frame)
        light_preview_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(light_preview_frame, text="亮色模式", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=2)
        self.light_preview_frame = ctk.CTkFrame(light_preview_frame, height=40, corner_radius=8)
        self.light_preview_frame.pack(fill="x", pady=2)
        
        # 主题信息
        info_frame = ctk.CTkFrame(theme_select_frame)
        info_frame.pack(fill="x", pady=5)
        self.theme_info_label = ctk.CTkLabel(info_frame, text="作者: | 版本: | 描述:", font=ctk.CTkFont(size=11))
        self.theme_info_label.pack(pady=2, anchor="w")
        
        # 更新预览
        self.update_theme_preview()
        
        # 主题模式设置（深色/浅色/系统）
        mode_frame = ctk.CTkFrame(theme_frame)
        mode_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(mode_frame, text="界面模式", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5, anchor="w")
        
        self.theme_var = ctk.StringVar(value="dark")
        themes = [
            ("dark", "深色模式"),
            ("light", "浅色模式"),
            ("system", "跟随系统"),
        ]
        
        for value, name in themes:
            radio = ctk.CTkRadioButton(
                mode_frame,
                text=name,
                variable=self.theme_var,
                value=value
            )
            radio.pack(anchor="w", padx=10, pady=2)
        
        # 字体设置
        font_frame = ctk.CTkFrame(container)
        font_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(font_frame, text="字体设置", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.font_size_var = ctk.IntVar(value=12)
        font_slider = ctk.CTkSlider(
            font_frame,
            from_=10,
            to=18,
            number_of_steps=8,
            variable=self.font_size_var
        )
        font_slider.pack(pady=5, padx=5)
        self.font_size_label = ctk.CTkLabel(font_frame, text="字体大小: 12")
        self.font_size_label.pack(pady=2)
        font_slider.configure(command=self.on_font_size_change)
        
        # 窗口设置
        window_frame = ctk.CTkFrame(container)
        window_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(window_frame, text="窗口设置", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.always_on_top_var = ctk.BooleanVar(value=False)
        top_switch = ctk.CTkSwitch(window_frame, text="窗口置顶", variable=self.always_on_top_var)
        top_switch.pack(pady=2)
        
        self.minimize_to_tray_var = ctk.BooleanVar(value=True)
        tray_switch = ctk.CTkSwitch(window_frame, text="关闭时最小化到托盘", variable=self.minimize_to_tray_var)
        tray_switch.pack(pady=2)
        
        # 通知设置
        notify_frame = ctk.CTkFrame(container)
        notify_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(notify_frame, text="通知设置", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.sound_notify_var = ctk.BooleanVar(value=True)
        sound_switch = ctk.CTkSwitch(notify_frame, text="启用声音通知", variable=self.sound_notify_var)
        sound_switch.pack(pady=2)
        
        self.toast_notify_var = ctk.BooleanVar(value=True)
        toast_switch = ctk.CTkSwitch(notify_frame, text="启用弹窗通知", variable=self.toast_notify_var)
        toast_switch.pack(pady=2)
        
        # UI视觉特效设置
        effects_frame = ctk.CTkFrame(container)
        effects_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(effects_frame, text="UI视觉特效", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        # 毛玻璃效果
        self.glass_effect_var = ctk.BooleanVar(value=False)
        glass_switch = ctk.CTkSwitch(effects_frame, text="启用毛玻璃效果", variable=self.glass_effect_var,
                                      command=self.on_glass_effect_toggle)
        glass_switch.pack(pady=2)
        
        # 边框光晕效果
        self.glow_effect_var = ctk.BooleanVar(value=False)
        glow_switch = ctk.CTkSwitch(effects_frame, text="启用边框光晕效果", variable=self.glow_effect_var,
                                     command=self.on_glow_effect_toggle)
        glow_switch.pack(pady=2)
        
        # 窗口透明度
        transparency_frame = ctk.CTkFrame(effects_frame)
        transparency_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(transparency_frame, text="窗口透明度", font=ctk.CTkFont(size=12)).pack(pady=2)
        
        self.transparency_var = ctk.DoubleVar(value=1.0)
        transparency_slider = ctk.CTkSlider(
            transparency_frame,
            from_=0.5,
            to=1.0,
            number_of_steps=10,
            variable=self.transparency_var,
            command=self.on_transparency_change
        )
        transparency_slider.pack(pady=2, padx=5, fill="x")
        self.transparency_label = ctk.CTkLabel(transparency_frame, text="100%")
        self.transparency_label.pack(pady=1)
        
        # Windows美化效果设置
        winstyles_frame = ctk.CTkFrame(container)
        winstyles_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(winstyles_frame, text="Windows美化效果 (pywinstyles)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        # 窗口样式选择
        style_select_frame = ctk.CTkFrame(winstyles_frame)
        style_select_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(style_select_frame, text="窗口样式", font=ctk.CTkFont(size=12)).pack(pady=2)
        
        self.window_style_var = ctk.StringVar(value="aero")
        window_styles = [
            ("aero", "Aero (经典)"),
            ("acrylic", "Acrylic (毛玻璃)"),
            ("mica", "Mica (材质)"),
            ("mica-alt", "Mica Alt (材质变体)"),
            ("dark", "Dark (深色)"),
            ("light", "Light (浅色)")
        ]
        
        for value, name in window_styles:
            radio = ctk.CTkRadioButton(
                style_select_frame,
                text=name,
                variable=self.window_style_var,
                value=value,
                command=self.on_window_style_change
            )
            radio.pack(anchor="w", padx=5, pady=1)
        
        # Windows特效开关
        effects_switch_frame = ctk.CTkFrame(winstyles_frame)
        effects_switch_frame.pack(fill="x", pady=5, padx=10)
        
        self.acrylic_effect_var = ctk.BooleanVar(value=False)
        acrylic_switch = ctk.CTkSwitch(effects_switch_frame, text="Acrylic毛玻璃效果", 
                                       variable=self.acrylic_effect_var,
                                       command=self.on_acrylic_toggle)
        acrylic_switch.pack(pady=2)
        
        self.mica_effect_var = ctk.BooleanVar(value=False)
        mica_switch = ctk.CTkSwitch(effects_switch_frame, text="Mica材质效果",
                                     variable=self.mica_effect_var,
                                     command=self.on_mica_toggle)
        mica_switch.pack(pady=2)
    
    def on_glass_effect_toggle(self):
        """毛玻璃效果开关"""
        if hasattr(self.parent, 'enable_glass_effect'):
            self.parent.enable_glass_effect(self.glass_effect_var.get())
    
    def on_glow_effect_toggle(self):
        """边框光晕效果开关"""
        if hasattr(self.parent, 'enable_glow_effect'):
            self.parent.enable_glow_effect(self.glow_effect_var.get())
    
    def on_transparency_change(self, value):
        """透明度变化"""
        self.transparency_label.configure(text=f"{int(value * 100)}%")
        if hasattr(self.parent, 'set_window_transparency'):
            self.parent.set_window_transparency(value)
    
    def on_window_style_change(self):
        """窗口样式变化"""
        style = self.window_style_var.get()
        if hasattr(self.parent, 'apply_window_style'):
            self.parent.apply_window_style(style)
    
    def on_acrylic_toggle(self):
        """Acrylic效果开关"""
        if hasattr(self.parent, 'apply_acrylic_effect'):
            self.parent.apply_acrylic_effect(self.acrylic_effect_var.get())
    
    def on_mica_toggle(self):
        """Mica效果开关"""
        if hasattr(self.parent, 'apply_mica_effect'):
            self.parent.apply_mica_effect(self.mica_effect_var.get())
    
    def on_font_size_change(self, value):
        """字体大小变化"""
        self.font_size_label.configure(text=f"字体大小: {int(value)}")
    
    def setup_advanced_tab(self):
        """高级设置标签页"""
        self.tab_advanced.grid_columnconfigure(0, weight=1)
        self.tab_advanced.grid_rowconfigure(0, weight=1)
        
        # 创建滚动框架
        scroll_frame = ctk.CTkScrollableFrame(self.tab_advanced)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用滚动框架作为容器
        container = scroll_frame
        
        # 网络设置
        network_frame = ctk.CTkFrame(container)
        network_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(network_frame, text="网络设置", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.timeout_var = ctk.IntVar(value=30)
        timeout_slider = ctk.CTkSlider(
            network_frame,
            from_=10,
            to=120,
            number_of_steps=11,
            variable=self.timeout_var
        )
        timeout_slider.pack(pady=5, padx=5)
        self.timeout_label = ctk.CTkLabel(network_frame, text="请求超时时间: 30秒")
        self.timeout_label.pack(pady=2)
        timeout_slider.configure(command=self.on_timeout_change)
        
        self.max_retries_var = ctk.IntVar(value=3)
        retry_slider = ctk.CTkSlider(
            network_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            variable=self.max_retries_var
        )
        retry_slider.pack(pady=5, padx=5)
        self.max_retries_label = ctk.CTkLabel(network_frame, text="最大重试次数: 3")
        self.max_retries_label.pack(pady=2)
        retry_slider.configure(command=self.on_retries_change)
        
        # 数据存储
        storage_frame = ctk.CTkFrame(self.tab_advanced)
        storage_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(storage_frame, text="数据存储", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.auto_save_var = ctk.BooleanVar(value=True)
        auto_save_switch = ctk.CTkSwitch(storage_frame, text="自动保存对话", variable=self.auto_save_var)
        auto_save_switch.pack(pady=2)
        
        self.auto_save_interval_var = ctk.IntVar(value=30)
        interval_slider = ctk.CTkSlider(
            storage_frame,
            from_=10,
            to=300,
            number_of_steps=29,
            variable=self.auto_save_interval_var
        )
        interval_slider.pack(pady=5, padx=5)
        self.auto_save_interval_label = ctk.CTkLabel(storage_frame, text="自动保存间隔: 30秒")
        self.auto_save_interval_label.pack(pady=2)
        interval_slider.configure(command=self.on_save_interval_change)
        
        # 安全设置
        security_frame = ctk.CTkFrame(container)
        security_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(security_frame, text="安全设置", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.require_confirmation_var = ctk.BooleanVar(value=True)
        confirm_switch = ctk.CTkSwitch(security_frame, text="危险操作需要确认", variable=self.require_confirmation_var)
        confirm_switch.pack(pady=2)
        
        self.clear_cache_on_exit_var = ctk.BooleanVar(value=False)
        cache_switch = ctk.CTkSwitch(security_frame, text="退出时清除缓存", variable=self.clear_cache_on_exit_var)
        cache_switch.pack(pady=2)
        
        # 自动更新
        update_frame = ctk.CTkFrame(container)
        update_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(update_frame, text="自动更新", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.auto_check_update_var = ctk.BooleanVar(value=True)
        update_switch = ctk.CTkSwitch(update_frame, text="启动时检查更新", variable=self.auto_check_update_var)
        update_switch.pack(pady=2)
    
    def on_timeout_change(self, value):
        """超时时间变化"""
        self.timeout_label.configure(text=f"请求超时时间: {int(value)}秒")
    
    def on_retries_change(self, value):
        """重试次数变化"""
        self.max_retries_label.configure(text=f"最大重试次数: {int(value)}")
    
    def on_save_interval_change(self, value):
        """保存间隔变化"""
        self.auto_save_interval_label.configure(text=f"自动保存间隔: {int(value)}秒")
    
    def _format_size(self, size):
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    
    def on_speed_change(self, value):
        """响应速度变化"""
        if value <= 3:
            self.speed_label.configure(text="快速")
        elif value <= 7:
            self.speed_label.configure(text="中等")
        else:
            self.speed_label.configure(text="精细")
    
    def refresh_pc_status(self):
        """刷新电脑状态"""
        # 重新创建状态标签页内容
        for widget in self.tab_pc_status.winfo_children():
            widget.destroy()
        
        self.setup_pc_status_tab()
    
    def update_theme_preview(self):
        """更新主题预览 - 支持亮色和暗色模式"""
        from src.config import theme_manager
        theme_name = self.theme_combobox.get()
        theme = theme_manager.get_theme(theme_name)
        
        if theme:
            # 更新暗色模式预览框颜色
            self.dark_preview_frame.configure(fg_color=theme.dark_colors.primary)
            
            # 更新亮色模式预览框颜色
            self.light_preview_frame.configure(fg_color=theme.light_colors.primary)
            
            # 更新主题信息
            self.theme_info_label.configure(
                text=f"作者: {theme.author} | 版本: {theme.version} | 描述: {theme.description}"
            )
    
    def refresh_themes(self):
        """刷新主题列表（热加载）"""
        from src.config import theme_manager
        
        changes = theme_manager.hot_reload()
        self.theme_names = theme_manager.get_theme_names()
        self.theme_combobox.configure(values=self.theme_names)
        
        # 显示变化信息
        msg = ""
        if changes['added']:
            msg += f"新增主题: {', '.join(changes['added'])}\n"
        if changes['updated']:
            msg += f"更新主题: {', '.join(changes['updated'])}\n"
        if changes['removed']:
            msg += f"删除主题: {', '.join(changes['removed'])}\n"
        
        if msg:
            messagebox.showinfo("主题刷新", msg)
        else:
            messagebox.showinfo("主题刷新", "没有检测到变化")
        
        # 更新预览
        self.update_theme_preview()
    
    def apply_theme(self):
        """应用选中的主题"""
        from src.config import theme_manager
        
        theme_name = self.theme_combobox.get()
        if theme_manager.set_theme(theme_name):
            settings.theme_name = theme_name
            messagebox.showinfo("应用主题", f"主题 '{theme_name}' 已应用\n重启应用后生效")
            self.update_theme_preview()
        else:
            messagebox.showerror("错误", "无法应用主题")
    
    def load_settings(self):
        """加载设置"""
        try:
            import json
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                
                # 加载功能设置
                if "functions" in settings:
                    for name, value in settings["functions"].items():
                        if name in self.function_vars:
                            self.function_vars[name].set(value)
                
                # 加载AI模式
                if "ai_mode" in settings:
                    self.ai_mode_var.set(settings["ai_mode"])
                
                # 加载响应速度
                if "response_speed" in settings:
                    self.speed_slider.set(settings["response_speed"])
                
                # 加载格式设置
                if "markdown_enabled" in settings:
                    self.markdown_var.set(settings["markdown_enabled"])
                if "code_highlight_enabled" in settings:
                    self.code_var.set(settings["code_highlight_enabled"])
                
                # 加载对话历史设置
                if "max_history" in settings:
                    self.max_history_var.set(settings["max_history"])
                    self.max_history_label.configure(text=f"最大历史记录数: {settings['max_history']}")
                
                # 加载开发者模式设置
                if "developer_mode" in settings:
                    self.dev_mode_var.set(settings["developer_mode"])
                if "log_level" in settings:
                    self.log_level_var.set(settings["log_level"])
                if "console_log" in settings:
                    self.console_log_var.set(settings["console_log"])
                if "console_debug" in settings:
                    self.console_debug_var.set(settings["console_debug"])
                if "console_timing" in settings:
                    self.console_timing_var.set(settings["console_timing"])
                if "console_request" in settings:
                    self.console_request_var.set(settings["console_request"])
                if "api_debug" in settings:
                    self.api_debug_var.set(settings["api_debug"])
                if "api_log" in settings:
                    self.api_log_var.set(settings["api_log"])
                if "perf_profiling" in settings:
                    self.perf_profiling_var.set(settings["perf_profiling"])
                if "memory_log" in settings:
                    self.memory_log_var.set(settings["memory_log"])
                
                # 加载界面设置
                if "theme" in settings:
                    self.theme_var.set(settings["theme"])
                if "font_size" in settings:
                    self.font_size_var.set(settings["font_size"])
                    self.font_size_label.configure(text=f"字体大小: {settings['font_size']}")
                if "always_on_top" in settings:
                    self.always_on_top_var.set(settings["always_on_top"])
                if "minimize_to_tray" in settings:
                    self.minimize_to_tray_var.set(settings["minimize_to_tray"])
                if "sound_notify" in settings:
                    self.sound_notify_var.set(settings["sound_notify"])
                if "toast_notify" in settings:
                    self.toast_notify_var.set(settings["toast_notify"])
                
                # 加载高级设置
                if "timeout" in settings:
                    self.timeout_var.set(settings["timeout"])
                    self.timeout_label.configure(text=f"请求超时时间: {settings['timeout']}秒")
                if "max_retries" in settings:
                    self.max_retries_var.set(settings["max_retries"])
                    self.max_retries_label.configure(text=f"最大重试次数: {settings['max_retries']}")
                if "auto_save" in settings:
                    self.auto_save_var.set(settings["auto_save"])
                if "auto_save_interval" in settings:
                    self.auto_save_interval_var.set(settings["auto_save_interval"])
                    self.auto_save_interval_label.configure(text=f"自动保存间隔: {settings['auto_save_interval']}秒")
                if "require_confirmation" in settings:
                    self.require_confirmation_var.set(settings["require_confirmation"])
                if "clear_cache_on_exit" in settings:
                    self.clear_cache_on_exit_var.set(settings["clear_cache_on_exit"])
                if "auto_check_update" in settings:
                    self.auto_check_update_var.set(settings["auto_check_update"])
                    
        except FileNotFoundError:
            print("settings.json 不存在，使用默认设置")
        except Exception as e:
            print(f"加载设置失败: {e}")
    
    def save_settings(self):
        """保存设置"""
        settings = {
            "functions": {name: var.get() for name, var in self.function_vars.items()},
            "ai_mode": self.ai_mode_var.get(),
            "response_speed": self.speed_slider.get(),
            "markdown_enabled": self.markdown_var.get(),
            "code_highlight_enabled": self.code_var.get(),
            "max_history": self.max_history_var.get(),
            
            # 开发者模式设置
            "developer_mode": self.dev_mode_var.get(),
            "log_level": self.log_level_var.get(),
            "console_log": self.console_log_var.get(),
            "console_debug": self.console_debug_var.get(),
            "console_timing": self.console_timing_var.get(),
            "console_request": self.console_request_var.get(),
            "api_debug": self.api_debug_var.get(),
            "api_log": self.api_log_var.get(),
            "perf_profiling": self.perf_profiling_var.get(),
            "memory_log": self.memory_log_var.get(),
            
            # 界面设置
            "theme": self.theme_var.get(),
            "font_size": self.font_size_var.get(),
            "always_on_top": self.always_on_top_var.get(),
            "minimize_to_tray": self.minimize_to_tray_var.get(),
            "sound_notify": self.sound_notify_var.get(),
            "toast_notify": self.toast_notify_var.get(),
            
            # 高级设置
            "timeout": self.timeout_var.get(),
            "max_retries": self.max_retries_var.get(),
            "auto_save": self.auto_save_var.get(),
            "auto_save_interval": self.auto_save_interval_var.get(),
            "require_confirmation": self.require_confirmation_var.get(),
            "clear_cache_on_exit": self.clear_cache_on_exit_var.get(),
            "auto_check_update": self.auto_check_update_var.get(),
            
            # 保存时间戳
            "last_modified": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            import json
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            # 如果开启了开发者模式，在控制台输出设置信息
            if self.dev_mode_var.get():
                print("\n" + "="*60)
                print("设置已保存到 settings.json")
                print("="*60)
                print(json.dumps(settings, ensure_ascii=False, indent=2))
                print("="*60 + "\n")
            
            messagebox.showinfo("提示", "设置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {str(e)}")
    
    def reset_settings(self):
        """恢复默认设置"""
        if messagebox.askyesno("确认", "确定要恢复所有设置为默认值吗？"):
            # 重置功能设置
            for name, var in self.function_vars.items():
                var.set(True)
            
            # 重置AI模式设置
            self.ai_mode_var.set("balanced")
            self.speed_slider.set(5)
            self.speed_label.configure(text="中等")
            self.markdown_var.set(True)
            self.code_var.set(True)
            self.max_history_var.set(100)
            self.max_history_label.configure(text="最大历史记录数: 100")
            
            # 重置开发者模式设置
            self.dev_mode_var.set(False)
            self.log_level_var.set("INFO")
            self.console_log_var.set(True)
            self.console_debug_var.set(False)
            self.console_timing_var.set(False)
            self.console_request_var.set(False)
            self.api_debug_var.set(False)
            self.api_log_var.set(False)
            self.perf_profiling_var.set(False)
            self.memory_log_var.set(False)
            
            # 重置界面设置
            self.theme_var.set("dark")
            self.font_size_var.set(12)
            self.font_size_label.configure(text="字体大小: 12")
            self.always_on_top_var.set(False)
            self.minimize_to_tray_var.set(True)
            self.sound_notify_var.set(True)
            self.toast_notify_var.set(True)
            
            # 重置高级设置
            self.timeout_var.set(30)
            self.timeout_label.configure(text="请求超时时间: 30秒")
            self.max_retries_var.set(3)
            self.max_retries_label.configure(text="最大重试次数: 3")
            self.auto_save_var.set(True)
            self.auto_save_interval_var.set(30)
            self.auto_save_interval_label.configure(text="自动保存间隔: 30秒")
            self.require_confirmation_var.set(True)
            self.clear_cache_on_exit_var.set(False)
            self.auto_check_update_var.set(True)
            
            messagebox.showinfo("提示", "已恢复默认设置")
    
    def export_settings(self):
        """导出设置到文件"""
        import json
        import tkinter.filedialog
        
        settings = {
            "functions": {name: var.get() for name, var in self.function_vars.items()},
            "ai_mode": self.ai_mode_var.get(),
            "response_speed": self.speed_slider.get(),
            "markdown_enabled": self.markdown_var.get(),
            "code_highlight_enabled": self.code_var.get(),
            "max_history": self.max_history_var.get(),
            "developer_mode": self.dev_mode_var.get(),
            "log_level": self.log_level_var.get(),
            "console_log": self.console_log_var.get(),
            "console_debug": self.console_debug_var.get(),
            "console_timing": self.console_timing_var.get(),
            "console_request": self.console_request_var.get(),
            "api_debug": self.api_debug_var.get(),
            "api_log": self.api_log_var.get(),
            "perf_profiling": self.perf_profiling_var.get(),
            "memory_log": self.memory_log_var.get(),
            "theme": self.theme_var.get(),
            "font_size": self.font_size_var.get(),
            "always_on_top": self.always_on_top_var.get(),
            "minimize_to_tray": self.minimize_to_tray_var.get(),
            "sound_notify": self.sound_notify_var.get(),
            "toast_notify": self.toast_notify_var.get(),
            "timeout": self.timeout_var.get(),
            "max_retries": self.max_retries_var.get(),
            "auto_save": self.auto_save_var.get(),
            "auto_save_interval": self.auto_save_interval_var.get(),
            "require_confirmation": self.require_confirmation_var.get(),
            "clear_cache_on_exit": self.clear_cache_on_exit_var.get(),
            "auto_check_update": self.auto_check_update_var.get(),
            "exported_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        file_path = tkinter.filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="导出设置"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("提示", f"设置已导出到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def close_window(self):
        """关闭窗口"""
        self.settings_window.destroy()


def main():
    app = CustomTkinterApp()
    app.run()


if __name__ == "__main__":
    main()