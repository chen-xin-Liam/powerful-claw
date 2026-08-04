# ASCII Art for splash screen
SPLASH_ASCII = """                                                                                                                               
  @@@@@@@@@@@           @@@@@@@@@@                     @@@@@@@@@@@@                                                            
  +@@@@@@@@@@@         @@@@@@@@@@@                     @@@@@@@@@@@@@@@@@                                                       
  +@@@@@@@@@@@        @@@@@@@@@@@@                     @@@@@@@@@@@@@@@@@@@                                                     
  +@@@@@@@@@@@@      @@@@@@@@@@@@@                     @@@@@@       @@@@@@                                                     
  +@@@@@@@@@@@@@    @@@@@@@@@@@@@@                     @@@@@@       @@@@@@:                                                    
  +@@@@@@@@@@@@@@  @@@@@@@@@@@@@@@                     @@@@@@       @@@@@@                                                     
  +@@@@@@@ @@@@@@@@@@@@@ @@@@@@@@@                     @@@@@@    *@@@@@@@                                                      
  +@@@@@@@@ @@@@@@@@@@@@ @@@@@@@@@                     @@@@@@@@@@@@@@@@@                                                       
  +@@@@@@@@  @@@@@@@@@@  @@@@@@@@@                     @@@@@@@@@@@@@                                                         
  +@@@@@@@@   @@@@@@@@   @@@@@@@@@                     @@@@@@                                                                
  +@@@@@@@@    @@@@@@    @@@@@@@@@                     @@@@@@      @ @                                                       
  +@@@@@@@@              @@@@@@@@@   @ @ %@ @          @@@@@@      @@                                                        
  @@@@@@@@@              @@@@@@@@@  @@ @ @ .@          @@@@@@     @@                                                         
   -     .               @      .                                                                                             
                                                                                                                               
                                                                                                                               
                                                                                                                               
                                                                                                                               
               @@@@@@@@@@@@@@@@@@@@@@@@   @@@@@@                 @@@@@@@@@@@@@@@@@@@@@@@    @@@@@        @@@@@#        @@@@@  
               %@@@@@@@@@@@@@@@@@@@@@@@   +@@@@.                 @@@@@@@@@@@@@@@@@@@@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@@@@@@@@@@@@@@@@@@@@   =@@@@                  @@@@@@@@@@@@@@@@@@@@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@                      =@@@@                  @@@@@             @@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@-                     =@@@@                  @@@@@             @@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@-                     =@@@@                  @@@@@@@@@@@@@@@@@@@@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@-                     =@@@@                  @@@@@@@@@@@@@@@@@@@@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@-                     =@@@@                  @@@@@@@@@@@@@@@@@@@@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@-                     =@@@@                  @@@@@             @@@@@    @@@@@        @@@@@         @@@@@  
               #@@@@                      =@@@@                  @@@@@             @@@@@    @@@@@        -@@@@         @@@@@  
               #@@@@@@@@@@@@@@@@@@@@@@@   =@@@@@@@@@@@@@@@@@@    @@@@@             @@@@@    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  
               #@@@@@@@@@@@@@@@@@@@@@@@   =@@@@@@@@@@@@@@@@@@    @@@@@             @@@@@    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  
               @@@@@@@@@@@@@@@@@@@@@@@@   @@@@@@@@@@@@@@@@@@@    @@@@@             @@@@@    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  
                                                                                                                               
"""

# 预定义的本地模型列表
PREDEFINED_MODELS = [
    {"name": "Qwen2-0.5B", "id": "Qwen/Qwen2-0.5B-Instruct", "size": "~1GB"},
    {"name": "DeepSeek-V4-Pro", "id": "deepseek-ai/DeepSeek-V4-Pro", "size": "~8GB"},
    {"name": "Qwen2-1.5B", "id": "Qwen/Qwen2-1.5B-Instruct", "size": "~3GB"},
    {"name": "Phi-3-mini", "id": "microsoft/Phi-3-mini-4k-instruct", "size": "~8GB"},
    {"name": "Qwen2-0.5B-JPN", "id": "Qwen/Qwen2-0.5B-JPN-Instruct", "size": "~1GB"},
    {"name": "Gemma-2B", "id": "google/gemma-2b-it", "size": "~5GB"},
]

import customtkinter as ctk
import threading
import time
import sys

def _splash_error_handler(exctype, value, tb):
    """自定义错误处理器 - 忽略窗口销毁后的Tkinter错误"""
    if "invalid command name" in str(value):
        # 这是窗口销毁后Tkinter回调尝试访问已销毁控件的错误，忽略
        return
    # 其他错误正常处理
    sys.__excepthook__(exctype, value, tb)

# 安装自定义错误处理器
sys.excepthook = _splash_error_handler

class SplashScreen:
    """启动画面类"""
    def __init__(self, root, on_close_callback):
        self.root = root
        self.on_close_callback = on_close_callback
        self.local_model_service = None
        self.download_progress = 0.0
        self.is_alive = True
        self.pending_callbacks = []  # 跟踪所有pending的after回调
        
        # 创建顶层窗口
        self.splash = ctk.CTkToplevel(root)
        self.splash.title("AI电脑控制")
        self.splash.geometry("850x520")
        self.splash.attributes("-topmost", True)
        self.splash.overrideredirect(True)

        # 居中显示
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width - 850) // 2
        y = (screen_height - 520) // 2
        self.splash.geometry(f"850x520+{x}+{y}")
        
        # 创建主框架
        self.frame = ctk.CTkFrame(self.splash, fg_color="#1a1a1a")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ASCII艺术显示
        self.ascii_label = ctk.CTkLabel(
            self.frame,
            text=SPLASH_ASCII,
            font=ctk.CTkFont(family="Courier New", size=8),
            text_color="#00ff00",
            justify="left"
        )
        self.ascii_label.pack(pady=20)
        
        # 加载提示
        self.loading_label = ctk.CTkLabel(
            self.frame,
            text="正在初始化...",
            font=ctk.CTkFont(size=16),
            text_color="#ffffff"
        )
        self.loading_label.pack(pady=10)
        
        # 详细进度信息
        self.detail_label = ctk.CTkLabel(
            self.frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#00ff00"
        )
        self.detail_label.pack(pady=5)
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(self.frame, width=600)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # 下载速度显示
        self.speed_label = ctk.CTkLabel(
            self.frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="#666666"
        )
        self.speed_label.pack(pady=5)
        
        # 版本信息
        self.version_label = ctk.CTkLabel(
            self.frame,
            text="v1.0.0 | AI电脑控制系统",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        self.version_label.pack(pady=10)
        
        # 开始加载
        self.start_loading()
    
    def update_progress(self, progress, status=""):
        """更新进度条"""
        if self.safe_update():
            try:
                self.progress_bar.set(progress)
                if status:
                    self.detail_label.configure(text=status)
                self.splash.update_idletasks()
            except:
                pass
    
    def start_loading(self):
        """开始加载过程"""
        thread = threading.Thread(target=self.load_process, daemon=True)
        thread.start()
    
    def safe_update(self):
        """安全更新检查"""
        try:
            return self.is_alive and self.splash is not None and self.splash.winfo_exists()
        except:
            return False
    
    def _safe_configure_label(self, label, **kwargs):
        """安全配置标签 - 直接更新，无视所有错误"""
        if not self.is_alive:
            return
        try:
            def _safe_configure():
                if not self.is_alive:
                    return
                try:
                    label.configure(**kwargs)
                except:
                    pass
            callback_id = self.splash.after(0, _safe_configure)
            self.pending_callbacks.append(callback_id)
        except:
            pass
    
    def _safe_update_progress(self, progress, status=""):
        """安全更新进度 - 直接更新，无视所有错误"""
        if not self.is_alive:
            return
        try:
            def _safe_update():
                if not self.is_alive:
                    return
                try:
                    self.progress_bar.set(progress)
                    if status:
                        self.detail_label.configure(text=status)
                except:
                    pass
            callback_id = self.splash.after(0, _safe_update)
            self.pending_callbacks.append(callback_id)
        except:
            pass
    
    def _cancel_all_callbacks(self):
        """取消所有pending的回调"""
        try:
            for callback_id in self.pending_callbacks:
                try:
                    self.splash.after_cancel(callback_id)
                except:
                    pass
            self.pending_callbacks.clear()
        except:
            pass
    
    def load_process(self):
        """完整的加载流程"""
        try:
            self._safe_configure_label(self.loading_label, text="初始化配置...")
            self._safe_update_progress(0.05, "加载配置文件")
            time.sleep(0.5)
            
            self._safe_configure_label(self.loading_label, text="加载模型服务...")
            self._safe_update_progress(0.10, "初始化本地模型服务")
            self._init_local_model_service()
            time.sleep(0.3)
            
            self._safe_configure_label(self.loading_label, text="检查模型...")
            self._safe_update_progress(0.15, "检查本地模型")
            self._download_models()
            
            self._safe_configure_label(self.loading_label, text="加载AI服务...")
            self._safe_update_progress(0.75, "初始化AI服务")
            time.sleep(0.5)
            
            self._safe_configure_label(self.loading_label, text="加载系统控制器...")
            self._safe_update_progress(0.85, "初始化系统控制模块")
            time.sleep(0.3)
            
            self._safe_configure_label(self.loading_label, text="加载视觉模块...")
            self._safe_update_progress(0.95, "初始化视觉捕获模块")
            time.sleep(0.3)
            
            self._safe_configure_label(self.loading_label, text="加载完成")
            self._safe_update_progress(1.0, "准备就绪")
            time.sleep(0.5)
            
        except Exception as e:
            self._safe_configure_label(self.loading_label, text="加载失败")
            self._safe_configure_label(self.detail_label, text=f"错误: {str(e)}")
            time.sleep(2)
        
        # 销毁窗口 - 在销毁前确保所有 pending 的回调都被取消
        try:
            self.is_alive = False  # 标记为不再活动
            self._cancel_all_callbacks()  # 取消所有pending回调
            
            if self.splash and self.splash.winfo_exists():
                # 先隐藏窗口，避免视觉闪烁
                self.splash.withdraw()
                
                # 多次执行update来清空事件队列
                for _ in range(5):
                    try:
                        self.splash.update_idletasks()
                        self.splash.update()
                    except:
                        break
                
                # 强制销毁窗口
                try:
                    self.splash.destroy()
                except:
                    pass
        except Exception as e:
            print(f"销毁窗口时出错: {e}")
        
        # 确保引用被清除
        self.splash = None
        self.pending_callbacks = []
        self.frame = None
        self.ascii_label = None
        self.loading_label = None
        self.detail_label = None
        self.progress_bar = None
        self.speed_label = None
        self.version_label = None
        
        # 延迟执行回调，给Tkinter时间处理事件
        if self.on_close_callback:
            import threading
            threading.Timer(0.1, self.on_close_callback).start()
    
    def _init_local_model_service(self):
        """初始化本地模型服务"""
        try:
            from src.services.local_model_service import LocalModelService
            self.local_model_service = LocalModelService()
        except Exception as e:
            print(f"Failed to init local model service: {e}")
    
    def _download_models(self):
        """检查并下载本地模型"""
        if not self.local_model_service:
            self._safe_update_progress(0.70, "跳过模型检查")
            return
        
        # 检查预定义模型是否已下载
        models_to_download = []
        for model in PREDEFINED_MODELS:
            model_info = self.local_model_service.get_model_info(model["name"])
            if model_info and not model_info.get("is_downloaded", False):
                models_to_download.append(model)
        
        if not models_to_download:
            self._safe_update_progress(0.70, "所有模型已下载")
            return
        
        # 下载模型
        total_models = len(models_to_download)
        progress_per_model = 0.55 / total_models  # 从15%到70%，共55%
        current_progress = 0.15
        
        for idx, model in enumerate(models_to_download):
            if not self.is_alive:
                break
            
            self._safe_configure_label(self.loading_label, text=f"下载模型 {model['name']}...")
            self._safe_update_progress(current_progress, f"正在下载 {model['name']} ({model['size']})")
            
            # 模拟下载进度
            for i in range(10):
                if not self.is_alive:
                    break
                time.sleep(0.2)
                download_progress = (i + 1) / 10
                self._safe_update_progress(
                    current_progress + download_progress * progress_per_model,
                    f"正在下载 {model['name']} ({int(download_progress * 100)}%)"
                )
            
            if not self.is_alive:
                break
            current_progress += progress_per_model
        
        self._safe_update_progress(0.70, "模型下载完成")