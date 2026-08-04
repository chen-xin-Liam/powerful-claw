import asyncio
import websockets
import json
import threading
import time
import os
import sys
import base64
import io
import socket
from typing import Dict, List, Optional, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from dataclasses import dataclass, field

try:
    import cv2
    HAS_OPENCV = True
    print("[ScreenMonitor] OpenCV 库已加载，支持RTMP流")
except ImportError:
    HAS_OPENCV = False
    print("[ScreenMonitor] 警告：OpenCV 库未安装，将使用PIL方式")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.remote_desktop_streamer import RemoteDesktopStreamer, RDConfig

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    print("[ScreenMonitor] 警告：mss 库未安装，将使用 PIL 方式")

try:
    from PIL import Image, ImageGrab, ImageEnhance, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[ScreenMonitor] 错误：PIL 库未安装，无法捕获屏幕")

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    print("[ScreenMonitor] 警告：pyaudio 库未安装")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("[ScreenMonitor] 警告：numpy 库未安装，音频处理功能受限")

try:
    import soundcard as sc
    HAS_SOUNDCARD = True
    print("[ScreenMonitor] soundcard 库已加载，支持系统音频捕获")
except ImportError:
    HAS_SOUNDCARD = False
    print("[ScreenMonitor] 警告：soundcard 库未安装，将尝试使用其他方法捕获系统音频")

@dataclass
class MonitorConfig:
    enabled: bool = True
    fps: int = 10
    quality: int = 95
    scale: float = 1.0
    bitrate: int = 2500000
    region: Optional[tuple] = None
    max_frame_skip: int = 1
    preset: str = 'standard'  # 'low', 'standard', 'high', 'hdr', 'ultra', 'bluray'
    use_hdr: bool = False
    chroma_subsampling: str = '4:4:4'  # '4:2:0', '4:2:2', '4:4:4'
    audio_enabled: bool = True
    audio_sample_rate: int = 44100
    audio_channels: int = 2
    audio_bitrate: int = 128
    # 音频设备黑名单（排除的设备名称关键词）
    audio_device_blacklist: list = field(default_factory=lambda: ['todesk', 'netease', '网易'])
    # UDP配置
    use_udp: bool = True
    udp_port: int = 15007
    udp_buffer_size: int = 65536
    # RTMP配置
    rtmp_enabled: bool = False
    rtmp_url: str = "rtmp://localhost/live/stream"
    # SRT配置
    srt_enabled: bool = False
    srt_port: int = 15009
    srt_latency: int = 120
    # SRTP配置
    srtp_enabled: bool = False
    srtp_port: int = 15009
    srtp_key: str = ""
    # 视频传输协议优先级
    video_protocol_priority: list = field(default_factory=lambda: ['rtmp', 'srt', 'srtp'])
    # 远程桌面式视频流配置
    use_remote_desktop_stream: bool = True
    rd_diff_threshold: int = 10
    rd_block_size: int = 64
    rd_keyframe_interval: int = 60
    rd_motion_detection: bool = True
    rd_adaptive_quality: bool = True
    rd_min_quality: int = 30
    rd_max_quality: int = 95
    rd_compress_blocks: bool = True
    rd_block_cache_size: int = 256
    # 音频传输配置
    # WebRTC配置
    webrtc_enabled: bool = True
    webrtc_port: int = 15008
    # SRTP音频配置
    audio_srtp_enabled: bool = False
    audio_srtp_port: int = 15008
    # SMPTE 2110配置
    smpte2110_enabled: bool = False
    smpte2110_port: int = 15008
    smpte2110_multicast: str = "239.255.0.1"
    # 音频传输协议优先级
    audio_protocol_priority: list = field(default_factory=lambda: ['webrtc', 'srtp', 'smpte2110'])

class MonitorHTTPServerHandler(BaseHTTPRequestHandler):
    """监控页面 HTTP 处理器"""
    
    def __init__(self, web_dir, *args, **kwargs):
        self.web_dir = web_dir
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            file_path = os.path.join(self.web_dir, "index.html")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
                return
        
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Found")

class ScreenMonitor:
    """实时桌面监控服务（端口 15005）- 高质量版"""

    def __init__(self):
        self.config = self._load_config_from_env()
        self.clients: List[websockets.WebSocketServerProtocol] = []
        self._lock = threading.RLock()
        self._ws_server = None
        self._http_server = None
        self._ws_thread = None
        self._http_thread = None
        self._capture_thread = None
        self.is_running = False
        self.is_capturing = False
        self.port = int(os.environ.get('SCREEN_MONITOR_PORT', 15004))
        self.ws_port = int(os.environ.get('SCREEN_MONITOR_WS_PORT', 15005))
        self._last_frame_time = 0
        self._frame_interval = 1.0 / self.config.fps
        self._event_loop = None
        self._frame_buffer = None
        self._buffer_lock = threading.Lock()

        # 音频相关
        self._audio_stream = None
        self._audio_thread = None
        self._is_capturing_audio = False
        self._audio_buffer = None
        self._audio_buffer_lock = threading.Lock()

        # UDP相关
        self._udp_socket = None
        self._udp_clients = set()  # 存储已连接的UDP客户端地址
        self._udp_thread = None

        # RTMP相关
        self._rtmp_writer = None
        self._rtmp_thread = None
        self._rtmp_enabled = False

        # 远程桌面式视频流
        self._rd_streamer = None
        self._rd_config = None

    def _load_config_from_env(self) -> MonitorConfig:
        """从环境变量加载配置"""
        import os
        config = MonitorConfig()

        config.fps = int(os.environ.get('SCREEN_MONITOR_FPS', config.fps))
        config.quality = int(os.environ.get('SCREEN_MONITOR_QUALITY', config.quality))
        config.bitrate = int(os.environ.get('SCREEN_MONITOR_BITRATE', config.bitrate))

        config.rtmp_enabled = os.environ.get('RTMP_ENABLED', 'false').lower() == 'true'
        config.rtmp_url = os.environ.get('RTMP_URL', config.rtmp_url)

        config.srt_enabled = os.environ.get('SRT_ENABLED', 'false').lower() == 'true'
        config.srt_port = int(os.environ.get('SRT_PORT', config.srt_port))
        config.srt_latency = int(os.environ.get('SRT_LATENCY', config.srt_latency))

        config.srtp_enabled = os.environ.get('SRTP_ENABLED', 'false').lower() == 'true'
        config.srtp_port = int(os.environ.get('SRTP_PORT', config.srtp_port))
        config.srtp_key = os.environ.get('SRTP_KEY', config.srtp_key)

        video_priority = os.environ.get('VIDEO_PROTOCOL_PRIORITY', 'rtmp,srt,srtp')
        config.video_protocol_priority = [p.strip() for p in video_priority.split(',')]

        config.use_remote_desktop_stream = os.environ.get('REMOTE_DESKTOP_STREAM', 'true').lower() == 'true'
        config.rd_diff_threshold = int(os.environ.get('RD_DIFF_THRESHOLD', config.rd_diff_threshold))
        config.rd_block_size = int(os.environ.get('RD_BLOCK_SIZE', config.rd_block_size))
        config.rd_keyframe_interval = int(os.environ.get('RD_KEYFRAME_INTERVAL', config.rd_keyframe_interval))
        config.rd_motion_detection = os.environ.get('RD_MOTION_DETECTION', 'true').lower() == 'true'
        config.rd_adaptive_quality = os.environ.get('RD_ADAPTIVE_QUALITY', 'true').lower() == 'true'
        config.rd_min_quality = int(os.environ.get('RD_MIN_QUALITY', config.rd_min_quality))
        config.rd_max_quality = int(os.environ.get('RD_MAX_QUALITY', config.rd_max_quality))

        config.webrtc_enabled = os.environ.get('WEBRTC_ENABLED', 'true').lower() == 'true'
        config.webrtc_port = int(os.environ.get('WEBRTC_PORT', config.webrtc_port))
        config.audio_srtp_enabled = os.environ.get('AUDIO_SRTP_ENABLED', 'false').lower() == 'true'
        config.audio_srtp_port = int(os.environ.get('AUDIO_SRTP_PORT', config.audio_srtp_port))
        config.smpte2110_enabled = os.environ.get('SMPTE2110_ENABLED', 'false').lower() == 'true'
        config.smpte2110_port = int(os.environ.get('SMPTE2110_PORT', config.smpte2110_port))
        config.smpte2110_multicast = os.environ.get('SMPTE2110_MULTICAST', config.smpte2110_multicast)

        audio_priority = os.environ.get('AUDIO_PROTOCOL_PRIORITY', 'webrtc,srtp,smpte2110')
        config.audio_protocol_priority = [p.strip() for p in audio_priority.split(',')]

        return config
    
    def start(self):
        """启动监控服务"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动 HTTP 服务器
        self._http_thread = threading.Thread(
            target=self._http_thread_func,
            daemon=True,
            name="MonitorHTTP"
        )
        self._http_thread.start()
        
        # 启动 WebSocket 服务器
        self._ws_thread = threading.Thread(
            target=self._ws_thread_func,
            daemon=True,
            name="MonitorWS"
        )
        self._ws_thread.start()
        
        # 等待事件循环启动
        while self._event_loop is None:
            time.sleep(0.1)
        
        # 启动 UDP 服务器（用于低延迟视频传输）
        if self.config.use_udp:
            self._start_udp_server()

        # 初始化远程桌面式视频流
        if self.config.use_remote_desktop_stream:
            self._init_remote_desktop_stream()

        # 启动屏幕捕获
        self._start_capture()

        print(f"[ScreenMonitor] 监控页面已启动：http://0.0.0.0:{self.port}")
        print(f"[ScreenMonitor] WebSocket 服务器已启动：ws://0.0.0.0:{self.ws_port}")
        if self.config.use_udp:
            print(f"[ScreenMonitor] UDP 视频流服务器已启动：udp://0.0.0.0:{self.config.udp_port}")
        if self.config.use_remote_desktop_stream:
            print(f"[ScreenMonitor] 远程桌面式视频流已启用（帧差压缩+分块编码）")
    
    def stop(self):
        """停止监控服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.is_capturing = False
        self._is_capturing_audio = False
        
        # 停止音频流
        if self._audio_stream:
            try:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
            except:
                pass
            self._audio_stream = None
        
        if self._http_server:
            self._http_server.shutdown()
            self._http_server.server_close()
        
        if self._ws_server:
            self._ws_server.close()
        
        # 停止 UDP 服务器
        if self._udp_socket:
            try:
                self._udp_socket.close()
            except:
                pass
            self._udp_socket = None
        
        print("[ScreenMonitor] 监控服务已停止")
    
    def _start_udp_server(self):
        """启动UDP服务器用于低延迟视频传输"""
        try:
            self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.config.udp_buffer_size)
            self._udp_socket.bind(('0.0.0.0', self.config.udp_port))
            self._udp_socket.setblocking(False)
            
            # 启动UDP接收线程（用于接收客户端注册）
            self._udp_thread = threading.Thread(
                target=self._udp_listen_loop,
                daemon=True,
                name="UDPListener"
            )
            self._udp_thread.start()
            print(f"[ScreenMonitor] UDP服务器已启动在端口 {self.config.udp_port}")
            
        except Exception as e:
            print(f"[ScreenMonitor] UDP服务器启动失败：{e}")
            self.config.use_udp = False
    
    def _udp_listen_loop(self):
        """UDP监听循环 - 接收客户端注册"""
        while self.is_running and self.config.use_udp:
            try:
                data, addr = self._udp_socket.recvfrom(1024)
                if data:
                    msg = data.decode('utf-8')
                    if msg == 'REGISTER':
                        self._udp_clients.add(addr)
                        print(f"[ScreenMonitor] UDP客户端已注册：{addr}")
                    elif msg == 'UNREGISTER':
                        self._udp_clients.discard(addr)
                        print(f"[ScreenMonitor] UDP客户端已注销：{addr}")
            except BlockingIOError:
                time.sleep(0.01)
            except Exception as e:
                print(f"[ScreenMonitor] UDP监听错误：{e}")
                time.sleep(0.1)
    
    def _send_frame_via_udp(self, frame_data):
        """通过UDP发送视频帧"""
        if not self.config.use_udp or not self._udp_socket or not self._udp_clients:
            return
        
        try:
            # 将帧数据分块发送（UDP包最大约64KB）
            chunk_size = 60000
            total_size = len(frame_data)
            chunks = []
            
            for i in range(0, total_size, chunk_size):
                chunks.append(frame_data[i:i+chunk_size])
            
            # 发送帧头（包含块数）
            header = f"FRAME:{len(chunks)}:{total_size}".encode('utf-8')
            
            for client in self._udp_clients:
                try:
                    self._udp_socket.sendto(header, client)
                    for chunk in chunks:
                        self._udp_socket.sendto(chunk, client)
                except Exception as e:
                    print(f"[ScreenMonitor] UDP发送失败到 {client}：{e}")
                    self._udp_clients.discard(client)
                    
        except Exception as e:
            print(f"[ScreenMonitor] UDP发送错误：{e}")

    def _init_remote_desktop_stream(self):
        """初始化远程桌面式视频流"""
        try:
            self._rd_config = RDConfig(
                fps=self.config.fps,
                quality=self.config.quality,
                scale=self.config.scale,
                diff_threshold=self.config.rd_diff_threshold,
                block_size=self.config.rd_block_size,
                keyframe_interval=self.config.rd_keyframe_interval,
                motion_detection=self.config.rd_motion_detection,
                adaptive_quality=self.config.rd_adaptive_quality,
                min_quality=self.config.rd_min_quality,
                max_quality=self.config.rd_max_quality,
                compress_blocks=self.config.rd_compress_blocks,
                block_cache_size=self.config.rd_block_cache_size
            )
            self._rd_streamer = RemoteDesktopStreamer(self._rd_config)
            print("[ScreenMonitor] 远程桌面式视频流初始化完成")
        except Exception as e:
            print(f"[ScreenMonitor] 远程桌面式视频流初始化失败：{e}")
            self.config.use_remote_desktop_stream = False

    def _process_frame_remote_desktop(self, frame: Any) -> Optional[Dict]:
        """使用远程桌面式视频流处理帧"""
        if not self.config.use_remote_desktop_stream or not self._rd_streamer:
            return None

        try:
            if isinstance(frame, str):
                frame_bytes = base64.b64decode(frame)
                img = Image.open(io.BytesIO(frame_bytes))
                frame_array = np.array(img)
                if len(frame_array.shape) == 2:
                    if HAS_OPENCV:
                        frame_array = cv2.cvtColor(frame_array, cv2.COLOR_GRAY2BGR)
                else:
                    if HAS_OPENCV:
                        frame_array = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
            else:
                frame_array = frame

            result = self._rd_streamer.process_frame(frame_array)
            return result

        except Exception as e:
            print(f"[ScreenMonitor] 远程桌面式视频流处理失败：{e}")
            return None

    def enable(self):
        """启用监控"""
        self.config.enabled = True
        self._start_capture()
        print("[ScreenMonitor] 监控已启用")
    
    def disable(self):
        """禁用监控"""
        self.config.enabled = False
        self.is_capturing = False
        print("[ScreenMonitor] 监控已禁用")
    
    def toggle(self):
        """切换监控状态"""
        if self.config.enabled:
            self.disable()
        else:
            self.enable()
        return self.config.enabled
    
    def set_fps(self, fps: int):
        """设置帧率"""
        self.config.fps = max(1, min(30, fps))
        self._frame_interval = 1.0 / self.config.fps
        print(f"[ScreenMonitor] 帧率已设置为：{fps} FPS")
    
    def set_quality(self, quality: int):
        """设置图片质量"""
        self.config.quality = max(10, min(100, quality))
        print(f"[ScreenMonitor] 质量已设置为：{quality}%")
    
    def set_scale(self, scale: float):
        """设置缩放比例"""
        self.config.scale = max(0.1, min(1.0, scale))
        print(f"[ScreenMonitor] 缩放比例已设置为：{scale}x")
    
    def set_preset(self, preset: str):
        """设置画质预设"""
        presets = {
            'low': {'quality': 50, 'scale': 0.5, 'hdr': False, 'subsampling': '4:2:0'},
            'standard': {'quality': 80, 'scale': 0.8, 'hdr': False, 'subsampling': '4:2:2'},
            'high': {'quality': 90, 'scale': 1.0, 'hdr': False, 'subsampling': '4:4:4'},
            'hdr': {'quality': 95, 'scale': 1.0, 'hdr': True, 'subsampling': '4:4:4'},
            'ultra': {'quality': 98, 'scale': 1.0, 'hdr': True, 'subsampling': '4:4:4'},
            'bluray': {'quality': 100, 'scale': 1.0, 'hdr': True, 'subsampling': '4:4:4'}
        }
        
        if preset in presets:
            self.config.preset = preset
            params = presets[preset]
            self.config.quality = params['quality']
            self.config.scale = params['scale']
            self.config.use_hdr = params['hdr']
            self.config.chroma_subsampling = params['subsampling']
            print(f"[ScreenMonitor] 画质已设置为：{preset}")
    
    def _start_capture(self):
        """启动屏幕捕获线程"""
        if self.is_capturing:
            return
        
        self.is_capturing = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="ScreenCapture"
        )
        self._capture_thread.start()
        
        # 启动音频捕获（支持 soundcard 或 pyaudio）
        if self.config.audio_enabled and (HAS_SOUNDCARD or HAS_PYAUDIO):
            self._start_audio_capture()
    
    def _start_audio_capture(self):
        """启动音频捕获 - 捕获系统音频输出（所有应用的声音）"""
        if self._is_capturing_audio:
            return
        
        if HAS_SOUNDCARD:
            self._start_system_audio_capture()
        elif HAS_PYAUDIO:
            self._start_microphone_capture()
        else:
            print("[ScreenMonitor] 无法捕获音频：未安装 soundcard 或 pyaudio")
    
    def _is_device_blacklisted(self, device_name: str) -> bool:
        """检查设备是否在黑名单中"""
        name_lower = device_name.lower()
        for keyword in self.config.audio_device_blacklist:
            if keyword.lower() in name_lower:
                return True
        return False
    
    def _start_system_audio_capture(self):
        """使用 soundcard 捕获系统音频输出（所有应用的声音）"""
        try:
            # 获取所有麦克风设备（包括循环回送设备）
            self._audio_microphone = None
            
            # 设备优先级列表（按优先级排序）
            priority_keywords = [
                'realtek',           # 优先选择 Realtek 设备
                'stereo mix',        # 立体声混音
                '立体声混音',          # 中文立体声混音
                'loopback',          # 回送设备
                'virtual',           # 虚拟设备
                'virtual audio',
            ]
            
            # 获取所有设备并过滤黑名单
            print("[ScreenMonitor] 可用音频设备列表：")
            all_mics = sc.all_microphones(include_loopback=True)
            filtered_mics = []
            
            for i, mic in enumerate(all_mics):
                is_loopback = getattr(mic, 'isloopback', False)
                is_blacklisted = self._is_device_blacklisted(mic.name)
                
                status = ""
                if is_blacklisted:
                    status = " [已排除]"
                elif is_loopback:
                    status = " [回送设备]"
                
                print(f"  [{i}] {mic.name}{status}")
                
                # 跳过黑名单设备
                if not is_blacklisted:
                    filtered_mics.append(mic)
            
            # 尝试找到最优的循环回送设备（按优先级排序）
            loopback_candidates = []
            selected_mic = None
            best_priority = float('inf')  # 记录最佳优先级
            
            try:
                for mic in filtered_mics:
                    name_lower = mic.name.lower()
                    is_loopback = getattr(mic, 'isloopback', False)
                    
                    if is_loopback:
                        loopback_candidates.append(mic)
                        
                        # 按优先级检查设备名称
                        for priority, keyword in enumerate(priority_keywords):
                            if keyword in name_lower:
                                # 只有当找到更高优先级的设备时才更新
                                if priority < best_priority:
                                    best_priority = priority
                                    selected_mic = mic
                                    print(f"[ScreenMonitor] 找到优先设备 '{mic.name}' (优先级: {priority})")
                                break
            except Exception as e:
                print(f"[ScreenMonitor] 遍历音频设备时出错：{e}")
            
            # 如果找到优先设备，使用它
            if selected_mic:
                self._audio_microphone = selected_mic
            # 如果找到回送设备但没有找到最优匹配，选择第一个回送设备
            elif loopback_candidates:
                self._audio_microphone = loopback_candidates[0]
                print(f"[ScreenMonitor] 选择第一个回送设备: {self._audio_microphone.name}")
            # 如果没有找到回送设备，使用默认麦克风（不受黑名单限制）
            else:
                self._audio_microphone = sc.default_microphone()
                print("[ScreenMonitor] 警告：未找到可用的回送设备，将使用默认麦克风输入")
            
            print(f"[ScreenMonitor] 音频设备：{self._audio_microphone.name}")
            
            self._is_capturing_audio = True
            self._audio_thread = threading.Thread(
                target=self._system_audio_capture_loop_with_retry,
                daemon=True,
                name="SystemAudioCapture"
            )
            self._audio_thread.start()
            print("[ScreenMonitor] 系统音频捕获已启动（捕获所有应用声音）")
            
        except Exception as e:
            print(f"[ScreenMonitor] 系统音频捕获启动失败：{e}")
            # 回退到麦克风捕获
            self._start_microphone_capture()
    
    def _start_microphone_capture(self):
        """使用 PyAudio 捕获麦克风输入（备选方案）"""
        if not HAS_PYAUDIO:
            return
        
        try:
            self._audio_stream = pyaudio.PyAudio().open(
                format=pyaudio.paInt16,
                channels=self.config.audio_channels,
                rate=self.config.audio_sample_rate,
                input=True,
                frames_per_buffer=1024
            )
            
            self._is_capturing_audio = True
            self._audio_thread = threading.Thread(
                target=self._microphone_capture_loop,
                daemon=True,
                name="MicrophoneCapture"
            )
            self._audio_thread.start()
            print("[ScreenMonitor] 麦克风音频捕获已启动")
            
        except Exception as e:
            print(f"[ScreenMonitor] 麦克风音频捕获启动失败：{e}")
    
    def _system_audio_capture_loop_with_retry(self):
        """系统音频捕获循环 - 带重试机制，处理 COM 初始化错误"""
        import io
        import wave
        
        frame_count = 0
        retry_count = 0
        max_retries = 5
        retry_delay = 1.0  # 重试间隔（秒）
        
        while self.is_running and self._is_capturing_audio and self.config.audio_enabled:
            try:
                # 使用 soundcard 捕获系统音频
                data = self._audio_microphone.record(
                    numframes=1024,
                    samplerate=self.config.audio_sample_rate
                )
                
                # 重置重试计数器
                retry_count = 0
                
                # soundcard 返回的是 float32 数据（-1.0 到 1.0），直接转换为字节
                if HAS_NUMPY:
                    # 确保数据类型为 float32
                    if data.dtype != np.float32:
                        data = data.astype(np.float32)
                    # 直接转换为字节
                    audio_bytes = data.tobytes()
                else:
                    audio_bytes = bytes(data)
                
                # 编码音频数据为 base64
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                
                # 广播音频数据
                if self._event_loop:
                    message = json.dumps({
                        'type': 'audio',
                        'data': audio_base64,
                        'sample_rate': self.config.audio_sample_rate,
                        'channels': self.config.audio_channels,
                        'format': 'float32'  # 添加格式信息
                    })
                
                    asyncio.run_coroutine_threadsafe(
                        self._send_to_all_clients(message),
                        self._event_loop
                    )
                
                frame_count += 1
                if frame_count % 100 == 0:
                    print(f"[ScreenMonitor] 已发送 {frame_count} 帧音频数据")
            
            except Exception as e:
                error_msg = str(e).lower()
                # 检测 COM 初始化错误（Error 0x800401f0）
                if '0x800401f0' in error_msg or 'coinitialize' in error_msg or 'com' in error_msg:
                    retry_count += 1
                    print(f"[ScreenMonitor] COM 初始化错误，尝试重新初始化 ({retry_count}/{max_retries})")
                    
                    if retry_count <= max_retries:
                        # 等待后重试
                        time.sleep(retry_delay)
                        # 重新初始化 soundcard（尝试重新获取设备）
                        try:
                            all_mics = sc.all_microphones(include_loopback=True)
                            for mic in all_mics:
                                if 'realtek' in mic.name.lower() and getattr(mic, 'isloopback', False):
                                    self._audio_microphone = mic
                                    print(f"[ScreenMonitor] 重新选择设备: {mic.name}")
                                    break
                        except Exception as reinit_e:
                            print(f"[ScreenMonitor] 重新初始化设备失败: {reinit_e}")
                        continue
                    else:
                        print(f"[ScreenMonitor] 音频捕获重试 {max_retries} 次失败，停止音频捕获")
                        self._is_capturing_audio = False
                        break
    
    def _microphone_capture_loop(self):
        """麦克风音频捕获循环"""
        while self.is_running and self._is_capturing_audio and self.config.audio_enabled:
            try:
                if self._audio_stream:
                    data = self._audio_stream.read(1024, exception_on_overflow=False)
                    
                    # 编码音频数据为 base64
                    audio_base64 = base64.b64encode(data).decode('utf-8')
                    
                    # 广播音频数据
                    if self._event_loop:
                        message = json.dumps({
                            'type': 'audio',
                            'data': audio_base64,
                            'sample_rate': self.config.audio_sample_rate,
                            'channels': self.config.audio_channels
                        })
                        
                        asyncio.run_coroutine_threadsafe(
                            self._send_to_all_clients(message),
                            self._event_loop
                        )
                
            except Exception as e:
                print(f"[ScreenMonitor] 麦克风音频捕获错误：{e}")
                time.sleep(0.01)
    
    def _capture_loop(self):
        """屏幕捕获主循环 - 优化版"""
        frame_skip_counter = 0
        while self.is_running and self.is_capturing and self.config.enabled:
            try:
                current_time = time.time()
                elapsed = current_time - self._last_frame_time
                
                if elapsed < self._frame_interval:
                    time.sleep(0.002)
                    continue
                
                frame_skip_counter += 1
                
                if frame_skip_counter > self.config.max_frame_skip:
                    frame_skip_counter = 0
                    frame = self._capture_screen()
                    if frame:
                        with self._buffer_lock:
                            self._frame_buffer = frame
                        self._broadcast_frame(frame)
                        self._last_frame_time = current_time
                else:
                    time.sleep(0.001)
                    
            except Exception as e:
                print(f"[ScreenMonitor] 捕获错误：{e}")
                time.sleep(0.05)
    
    def _capture_screen(self) -> Optional[str]:
        """捕获屏幕并返回 base64 编码的图片 - 高质量版"""
        try:
            if HAS_MSS:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
            elif HAS_PIL:
                img = ImageGrab.grab()
            else:
                return None
            
            # HDR 增强处理
            if self.config.use_hdr or self.config.preset == 'hdr':
                img = self._apply_hdr_enhancement(img)
            
            # 画质预设调整
            if self.config.preset == 'ultra':
                img = self._apply_sharpen(img)
            elif self.config.preset == 'bluray':
                img = self._apply_bluray_enhancement(img)
            
            # 缩放处理
            if self.config.scale != 1.0:
                new_size = (int(img.width * self.config.scale), int(img.height * self.config.scale))
                if self.config.preset in ['high', 'hdr', 'ultra', 'bluray']:
                    img = img.resize(new_size, Image.LANCZOS)
                else:
                    img = img.resize(new_size, Image.BICUBIC)
            
            buffer = io.BytesIO()
            
            # JPEG 压缩参数优化
            jpeg_params = {
                'quality': self.config.quality,
                'progressive': True,
                'optimize': True,
            }
            
            # 色度抽样设置
            if self.config.chroma_subsampling == '4:4:4':
                jpeg_params['subsampling'] = '4:4:4'
            elif self.config.chroma_subsampling == '4:2:2':
                jpeg_params['subsampling'] = '4:2:2'
            else:
                jpeg_params['subsampling'] = '4:2:0'
            
            img.save(buffer, format='JPEG', **jpeg_params)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"[ScreenMonitor] 截图失败：{e}")
            return None
    
    def _apply_hdr_enhancement(self, img: Image.Image) -> Image.Image:
        """应用 HDR 增强效果"""
        # 提升对比度
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        # 提升饱和度
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.3)
        
        # 提升亮度
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        
        return img
    
    def _apply_sharpen(self, img: Image.Image) -> Image.Image:
        """应用锐化效果"""
        # 轻微锐化
        img = img.filter(ImageFilter.SHARPEN)
        
        # 增强细节
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.3)
        
        return img
    
    def _apply_bluray_enhancement(self, img: Image.Image) -> Image.Image:
        """应用蓝光画质增强"""
        # HDR 增强
        img = self._apply_hdr_enhancement(img)
        
        # 锐化
        img = self._apply_sharpen(img)
        
        # 降噪（使用轻微模糊后再锐化）
        img = img.filter(ImageFilter.SMOOTH_MORE)
        img = self._apply_sharpen(img)
        
        return img
    
    def _broadcast_frame(self, frame_data: str):
        """广播视频帧到所有客户端 - 优化版（支持UDP+远程桌面式流）"""
        if self._event_loop and self.clients:
            message = f'{{"type":"frame","data":"{frame_data}","t":{time.time():.3f}}}'
            asyncio.run_coroutine_threadsafe(
                self._send_to_all_clients(message),
                self._event_loop
            )

        try:
            frame_bytes = base64.b64decode(frame_data)
            self._send_frame_via_udp(frame_bytes)
        except Exception as e:
            print(f"[ScreenMonitor] UDP发送帧失败：{e}")

        if self.config.use_remote_desktop_stream and self._rd_streamer:
            try:
                rd_result = self._process_frame_remote_desktop(frame_data)
                if rd_result and self._event_loop and self.clients:
                    rd_message = json.dumps({
                        'type': 'rd_frame',
                        'data': rd_result,
                        'timestamp': time.time()
                    })
                    asyncio.run_coroutine_threadsafe(
                        self._send_to_all_clients(rd_message),
                        self._event_loop
                    )
            except Exception as e:
                print(f"[ScreenMonitor] 远程桌面式视频流广播失败：{e}")
    
    async def _send_to_all_clients(self, message: str):
        """发送消息给所有客户端 - 并行发送优化"""
        tasks = []
        with self._lock:
            clients_copy = list(self.clients)
        
        for client in clients_copy:
            tasks.append(self._send_to_client(client, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        with self._lock:
            for client in clients_copy:
                if client not in self.clients:
                    continue
                try:
                    await asyncio.wait_for(client.ping(), timeout=0.1)
                except:
                    self.clients.remove(client)
    
    async def _send_to_client(self, client, message):
        """发送消息给单个客户端"""
        try:
            await client.send(message)
        except:
            with self._lock:
                if client in self.clients:
                    self.clients.remove(client)
    
    async def _handle_client(self, websocket):
        """处理监控客户端连接"""
        with self._lock:
            self.clients.append(websocket)
            print(f"[ScreenMonitor] 客户端已连接：{websocket.remote_address}")
        
        try:
            await websocket.send(json.dumps({
                'type': 'config',
                'enabled': self.config.enabled,
                'fps': self.config.fps,
                'quality': self.config.quality,
                'scale': self.config.scale,
                'preset': self.config.preset,
                'hdr': self.config.use_hdr,
                'audio_enabled': self.config.audio_enabled,
                'audio_sample_rate': self.config.audio_sample_rate,
                'audio_channels': self.config.audio_channels
            }))
            
            # 发送最新帧
            with self._buffer_lock:
                if self._frame_buffer:
                    await websocket.send(json.dumps({
                        'type': 'frame',
                        'data': self._frame_buffer,
                        'timestamp': time.time(),
                        'fps': self.config.fps,
                        'quality': self.config.quality,
                        'scale': self.config.scale
                    }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    command = data.get('command')
                    
                    if command == 'toggle':
                        self.toggle()
                    elif command == 'set_fps':
                        self.set_fps(data.get('value', 10))
                    elif command == 'set_quality':
                        self.set_quality(data.get('value', 80))
                    elif command == 'set_scale':
                        self.set_scale(data.get('value', 0.5))
                    elif command == 'set_preset':
                        self.set_preset(data.get('value', 'standard'))
                    elif command == 'status':
                        await websocket.send(json.dumps({
                            'type': 'status',
                            'enabled': self.config.enabled,
                            'fps': self.config.fps,
                            'quality': self.config.quality,
                            'scale': self.config.scale,
                            'preset': self.config.preset,
                            'hdr': self.config.use_hdr,
                            'clients': len(self.clients)
                        }))
                except Exception as e:
                    print(f"[ScreenMonitor] 处理客户端消息失败：{e}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            with self._lock:
                if websocket in self.clients:
                    self.clients.remove(websocket)
                print(f"[ScreenMonitor] 客户端已断开：{websocket.remote_address}")
    
    async def _run_ws_server(self):
        """运行 WebSocket 服务器"""
        self._ws_server = await websockets.serve(
            self._handle_client,
            '0.0.0.0',
            self.ws_port
        )
        await self._ws_server.wait_closed()
    
    def _ws_thread_func(self):
        """WebSocket 服务器线程函数"""
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        self._event_loop.run_until_complete(self._run_ws_server())
    
    def _http_thread_func(self):
        """HTTP 服务器线程函数"""
        web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_monitor")
        os.makedirs(web_dir, exist_ok=True)
        self._create_web_page(web_dir)
        
        handler = lambda *args, **kwargs: MonitorHTTPServerHandler(web_dir, *args, **kwargs)
        self._http_server = HTTPServer(('0.0.0.0', self.port), handler)
        print(f"[ScreenMonitor] HTTP 服务器已启动：http://0.0.0.0:{self.port}")
        self._http_server.serve_forever()
    
    def _create_web_page(self, web_dir):
        """创建监控网页"""
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>桌面监控 - Screen Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
        }
        
        #videoContainer {
            width: 100vw;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #000;
            position: relative;
        }
        
        #videoCanvas {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            image-rendering: high-quality;
        }
        
        .controls {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 15px;
            align-items: center;
            background: rgba(0,0,0,0.7);
            padding: 15px 25px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            z-index: 100;
        }
        
        .control-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-start {
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: white;
        }
        
        .btn-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 212, 255, 0.4);
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
            color: white;
        }
        
        .btn-stop:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 107, 107, 0.4);
        }
        
        .settings-panel {
            position: fixed;
            top: 20px;
            right: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            background: rgba(0,0,0,0.7);
            padding: 15px 25px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            z-index: 100;
        }
        
        .setting-item {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .setting-item label {
            font-size: 12px;
            color: rgba(255,255,255,0.7);
            text-align: center;
        }
        
        .setting-item input[type="range"] {
            width: 100px;
            height: 6px;
            border-radius: 3px;
            background: rgba(255,255,255,0.2);
            outline: none;
            -webkit-appearance: none;
        }
        
        .setting-item input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: linear-gradient(135deg, #00d4ff, #7b2cbf);
            cursor: pointer;
        }
        
        .setting-value {
            font-size: 12px;
            color: #00d4ff;
            text-align: center;
            font-family: 'Courier New', monospace;
        }
        
        .status-indicator {
            position: fixed;
            top: 20px;
            left: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(0,0,0,0.7);
            padding: 10px 20px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            z-index: 100;
            font-size: 14px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4ade80;
            animation: pulse 2s infinite;
        }
        
        .status-dot.offline {
            background: #f87171;
            animation: none;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .frame-rate {
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: rgba(255,255,255,0.8);
            margin-left: 10px;
        }
        
        .fullscreen-btn {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            border: none;
            color: white;
            padding: 12px 20px;
            border-radius: 10px;
            cursor: pointer;
            z-index: 100;
            font-size: 14px;
            transition: all 0.3s;
            backdrop-filter: blur(10px);
        }
        
        .fullscreen-btn:hover {
            background: rgba(0,0,0,0.9);
            transform: translateX(-50%) scale(1.05);
        }
        
        .connection-status {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 15px;
            background: rgba(0,0,0,0.7);
            border-radius: 20px;
            font-size: 12px;
            backdrop-filter: blur(10px);
            z-index: 100;
        }
        
        .connection-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        
        .connection-dot.connected {
            background: #4ade80;
        }
        
        .connection-dot.disconnected {
            background: #f87171;
        }
        
        .preset-selector {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }
        
        .preset-btn {
            padding: 6px 12px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 6px;
            background: rgba(255,255,255,0.1);
            color: white;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.3s;
        }
        
        .preset-btn:hover {
            background: rgba(255,255,255,0.2);
        }
        
        .preset-btn.active {
            border-color: #00d4ff;
            background: rgba(0, 212, 255, 0.3);
        }
        
        @media (max-width: 768px) {
            .settings-panel {
                padding: 10px 15px;
            }
            
            .controls {
                flex-wrap: wrap;
                justify-content: center;
                padding: 10px 15px;
            }
            
            .setting-item input[type="range"] {
                width: 80px;
            }
        }
    </style>
</head>
<body>
    <div id="videoContainer">
        <canvas id="videoCanvas"></canvas>
    </div>
    
    <button class="fullscreen-btn" id="fullscreenBtn" title="全屏切换">⛶ 全屏模式</button>
    
    <div class="status-indicator">
        <div class="status-dot offline" id="statusDot"></div>
        <span id="statusLabel">离线</span>
        <span class="frame-rate" id="frameRate">0 FPS</span>
    </div>
    
    <button class="fullscreen-btn" id="audioTestBtn" title="测试音频" style="position:fixed;top:80px;left:20px;z-index:1000;">🔊 测试音频</button>
    
    <div class="settings-panel">
        <div class="setting-item">
            <label>帧率</label>
            <input type="range" id="fpsSlider" min="1" max="30" value="10" oninput="updateFPS(this.value)">
            <span class="setting-value" id="fpsValue">10</span>
        </div>
        <div class="setting-item">
            <label>质量</label>
            <input type="range" id="qualitySlider" min="10" max="100" value="95" oninput="updateQuality(this.value)">
            <span class="setting-value" id="qualityValue">95</span>
        </div>
        <div class="setting-item">
            <label>缩放</label>
            <input type="range" id="scaleSlider" min="10" max="100" value="100" oninput="updateScale(this.value)">
            <span class="setting-value" id="scaleValue">100</span>
        </div>
        <div class="setting-item">
            <label>画质预设</label>
            <div class="preset-selector">
                <button class="preset-btn" data-preset="low" onclick="setPreset('low')">流畅</button>
                <button class="preset-btn" data-preset="standard" onclick="setPreset('standard')">标准</button>
                <button class="preset-btn" data-preset="high" onclick="setPreset('high')">高清</button>
                <button class="preset-btn" data-preset="hdr" onclick="setPreset('hdr')">HDR</button>
                <button class="preset-btn" data-preset="ultra" onclick="setPreset('ultra')">超清</button>
                <button class="preset-btn" data-preset="bluray" onclick="setPreset('bluray')">蓝光</button>
            </div>
        </div>
    </div>
    
    <div class="controls">
        <button class="control-btn btn-start" id="startBtn" onclick="toggleMonitor()">
            <span>▶</span> 开始监控
        </button>
        <button class="control-btn btn-stop" id="stopBtn" onclick="toggleMonitor()" disabled>
            <span>⏹</span> 停止监控
        </button>
    </div>
    
    <div class="connection-status">
        <div class="connection-dot disconnected" id="connStatus"></div>
        <span>WebSocket</span>
    </div>

    <script>
        const canvas = document.getElementById('videoCanvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: false });
        const videoContainer = document.getElementById('videoContainer');
        
        // 音频相关
        let audioContext = null;
        let audioBufferQueue = [];
        let isAudioPlaying = false;
        let audioSource = null;
        
        // UDP相关
        let udpSocket = null;
        let isUdpConnected = false;
        let udpFrameBuffer = [];
        let udpExpectedChunks = 0;
        let udpTotalSize = 0;
        let udpCurrentSize = 0;
        
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const fullscreenBtn = document.getElementById('fullscreenBtn');
        
        const statusDot = document.getElementById('statusDot');
        const statusLabel = document.getElementById('statusLabel');
        const frameRate = document.getElementById('frameRate');
        const connStatus = document.getElementById('connStatus');
        
        const fpsSlider = document.getElementById('fpsSlider');
        const qualitySlider = document.getElementById('qualitySlider');
        const scaleSlider = document.getElementById('scaleSlider');
        const fpsValue = document.getElementById('fpsValue');
        const qualityValue = document.getElementById('qualityValue');
        const scaleValue = document.getElementById('scaleValue');
        
        let ws = null;
        let isConnected = false;
        let frameCount = 0;
        let lastFpsTime = Date.now();
        let isFullscreen = false;
        let currentPreset = 'standard';
        
        function initUdpClient() {
            try {
                udpSocket = new UDPSocket();
                udpSocket.onmessage = function(event) {
                    processUdpData(event.data);
                };
                udpSocket.onopen = function() {
                    isUdpConnected = true;
                    // 注册到UDP服务器
                    udpSocket.send('REGISTER');
                    console.log('UDP客户端已连接');
                };
                udpSocket.onerror = function(err) {
                    console.error('UDP错误:', err);
                    isUdpConnected = false;
                };
                udpSocket.connect(window.location.hostname, 15007);
            } catch (e) {
                console.warn('浏览器不支持UDP或UDP服务器不可用:', e);
            }
        }
        
        function processUdpData(data) {
            try {
                const header = data.slice(0, 30).toString('utf-8');
                if (header.startsWith('FRAME:')) {
                    const parts = header.split(':');
                    udpExpectedChunks = parseInt(parts[1]);
                    udpTotalSize = parseInt(parts[2]);
                    udpCurrentSize = 0;
                    udpFrameBuffer = [];
                    
                    // 提取帧数据部分
                    const frameData = data.slice(header.indexOf('\0') + 1);
                    if (frameData.length > 0) {
                        udpFrameBuffer.push(frameData);
                        udpCurrentSize += frameData.length;
                    }
                } else {
                    // 帧数据块
                    udpFrameBuffer.push(data);
                    udpCurrentSize += data.length;
                    
                    // 检查是否接收完一帧
                    if (udpCurrentSize >= udpTotalSize) {
                        const completeFrame = Buffer.concat(udpFrameBuffer);
                        displayFrame(completeFrame);
                        udpFrameBuffer = [];
                        udpExpectedChunks = 0;
                        udpTotalSize = 0;
                        udpCurrentSize = 0;
                    }
                }
            } catch (e) {
                console.error('UDP数据处理错误:', e);
            }
        }
        
        // 简化的UDP实现（使用WebSocket作为备选）
        class UDPSocket {
            constructor() {
                this._socket = null;
                this._onmessage = null;
                this._onopen = null;
                this._onerror = null;
            }
            
            get onmessage() { return this._onmessage; }
            set onmessage(fn) { this._onmessage = fn; }
            
            get onopen() { return this._onopen; }
            set onopen(fn) { this._onopen = fn; }
            
            get onerror() { return this._onerror; }
            set onerror(fn) { this._onerror = fn; }
            
            connect(host, port) {
                // 创建WebSocket连接作为UDP的备选方案
                // 在实际应用中，可以使用WebRTC或其他UDP技术
                console.log('UDP客户端连接到:', host, port);
                if (this._onopen) this._onopen();
            }
            
            send(data) {
                console.log('UDP发送:', data);
            }
            
            close() {}
        }
        
        function connectWebSocket() {
            if (ws) {
                ws.close();
            }
            
            ws = new WebSocket('ws://' + window.location.hostname + ':15006');
            
            ws.onopen = function() {
                isConnected = true;
                connStatus.classList.remove('disconnected');
                connStatus.classList.add('connected');
                console.log('WebSocket 连接成功');
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'frame') {
                    frameCount++;
                    const now = Date.now();
                    if (now - lastFpsTime >= 1000) {
                        frameRate.textContent = frameCount + ' FPS';
                        frameCount = 0;
                        lastFpsTime = now;
                    }
                    processFrame(data.data);
                } else if (data.type === 'audio') {
                    processAudio(data);
                } else if (data.type === 'config') {
                    fpsSlider.value = data.fps || 10;
                    fpsValue.textContent = data.fps || 10;
                    qualitySlider.value = data.quality || 95;
                    qualityValue.textContent = data.quality || 95;
                    scaleSlider.value = Math.round((data.scale || 1.0) * 100);
                    scaleValue.textContent = Math.round((data.scale || 1.0) * 100);
                    currentPreset = data.preset || 'standard';
                    updatePresetButtons(currentPreset);
                    
                    // 初始化音频上下文
                    if (data.audio_enabled && !audioContext) {
                        initAudioContext(data.audio_sample_rate || 44100, data.audio_channels || 2);
                    }
                    
                    if (data.enabled) setMonitoringStatus(true);
                } else if (data.type === 'status') {
                    setMonitoringStatus(data.enabled);
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket 错误:', error);
            };
            
            ws.onclose = function() {
                isConnected = false;
                connStatus.classList.remove('connected');
                connStatus.classList.add('disconnected');
                console.log('WebSocket 连接关闭');
            };
        }
        
        function processFrame(frameData) {
            const byteString = atob(frameData);
            const mimeType = 'image/jpeg';
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            for (let i = 0; i < byteString.length; i++) {
                ia[i] = byteString.charCodeAt(i);
            }
            const blob = new Blob([ab], { type: mimeType });
            
            createImageBitmap(blob).then(function(img) {
                const cw = videoContainer.clientWidth;
                const ch = videoContainer.clientHeight;
                const iw = img.width;
                const ih = img.height;
                
                const scale = Math.min(cw / iw, ch / ih);
                const dw = iw * scale;
                const dh = ih * scale;
                
                if (canvas.width !== dw || canvas.height !== dh) {
                    canvas.width = dw;
                    canvas.height = dh;
                }
                
                ctx.drawImage(img, 0, 0, dw, dh);
                img.close();
            }).catch(function() {
                const img = new Image();
                img.onload = function() {
                    const cw = videoContainer.clientWidth;
                    const ch = videoContainer.clientHeight;
                    const scale = Math.min(cw / img.width, ch / img.height);
                    canvas.width = img.width * scale;
                    canvas.height = img.height * scale;
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                };
                img.src = 'data:image/jpeg;base64,' + frameData;
            });
        }
        
        function setMonitoringStatus(enabled) {
            if (enabled) {
                statusDot.classList.remove('offline');
                statusLabel.textContent = '监控中';
                startBtn.disabled = true;
                stopBtn.disabled = false;
            } else {
                statusDot.classList.add('offline');
                statusLabel.textContent = '已停止';
                startBtn.disabled = false;
                stopBtn.disabled = true;
            }
        }
        
        function sendCommand(command, data) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ command, ...data }));
            }
        }
        
        function toggleMonitor() {
            sendCommand('toggle');
        }
        
        function updateFPS(value) {
            fpsValue.textContent = value;
            sendCommand('set_fps', { value: parseInt(value) });
        }
        
        function updateQuality(value) {
            qualityValue.textContent = value;
            sendCommand('set_quality', { value: parseInt(value) });
        }
        
        function updateScale(value) {
            scaleValue.textContent = value;
            sendCommand('set_scale', { value: parseFloat(value) / 100 });
        }
        
        function setPreset(preset) {
            currentPreset = preset;
            updatePresetButtons(preset);
            sendCommand('set_preset', { value: preset });
        }
        
        function updatePresetButtons(activePreset) {
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.preset === activePreset) {
                    btn.classList.add('active');
                }
            });
        }
        
        function initAudioContext(sampleRate, channels) {
            try {
                audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: sampleRate
                });
                console.log('音频上下文已初始化:', sampleRate, 'Hz,', channels, '通道');
                playAudioQueue();
            } catch (e) {
                console.error('音频上下文初始化失败:', e);
            }
        }
        
        function processAudio(data) {
            console.log('收到音频数据:', data);
            
            if (!audioContext) {
                console.warn('音频上下文未初始化，等待配置消息...');
                return;
            }
            
            try {
                const audioData = atob(data.data);
                const arrayBuffer = new ArrayBuffer(audioData.length);
                const view = new Uint8Array(arrayBuffer);
                
                for (let i = 0; i < audioData.length; i++) {
                    view[i] = audioData.charCodeAt(i);
                }
                
                // 处理 float32 格式的音频数据
                const channels = data.channels || 2;
                const sampleRate = data.sample_rate || 44100;
                const format = data.format || 'float32';
                
                // float32: 4 bytes per sample
                const bytesPerSample = 4;
                const frameLength = Math.floor(audioData.length / bytesPerSample / channels);
                
                console.log('音频参数:', channels, '声道,', sampleRate, 'Hz,', frameLength, '采样');
                
                const audioBuffer = audioContext.createBuffer(channels, frameLength, sampleRate);
                
                for (let channel = 0; channel < channels; channel++) {
                    const channelData = audioBuffer.getChannelData(channel);
                    for (let i = 0; i < frameLength; i++) {
                        const index = (i * channels + channel) * bytesPerSample;
                        // 读取 float32 数据
                        const float32 = new Float32Array(arrayBuffer, index, 1)[0];
                        channelData[i] = float32;
                    }
                }
                
                audioBufferQueue.push(audioBuffer);
                console.log('音频队列长度:', audioBufferQueue.length);
                
                if (audioBufferQueue.length > 10) {
                    audioBufferQueue.shift();
                }
            } catch (e) {
                console.error('音频处理错误:', e);
            }
        }
        
        function playAudioQueue() {
            if (!audioContext) {
                setTimeout(playAudioQueue, 100);
                return;
            }
            
            if (audioBufferQueue.length === 0) {
                setTimeout(playAudioQueue, 100);
                return;
            }
            
            if (isAudioPlaying) {
                setTimeout(playAudioQueue, 50);
                return;
            }
            
            const buffer = audioBufferQueue.shift();
            if (!buffer) {
                setTimeout(playAudioQueue, 100);
                return;
            }
            
            console.log('开始播放音频，缓冲区长度:', buffer.length, '采样');
            
            const source = audioContext.createBufferSource();
            source.buffer = buffer;
            
            const gainNode = audioContext.createGain();
            gainNode.gain.value = 1.0;
            
            source.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            source.onended = function() {
                console.log('音频播放结束');
                isAudioPlaying = false;
                setTimeout(playAudioQueue, 10);
            };
            
            source.onerror = function(e) {
                console.error('音频播放错误:', e);
                isAudioPlaying = false;
                setTimeout(playAudioQueue, 100);
            };
            
            isAudioPlaying = true;
            source.start(0);
            console.log('音频开始播放');
        }
        
        fullscreenBtn.addEventListener('click', function() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().then(() => {
                    isFullscreen = true;
                    fullscreenBtn.textContent = '⛶ 退出全屏';
                });
            } else {
                document.exitFullscreen().then(() => {
                    isFullscreen = false;
                    fullscreenBtn.textContent = '⛶ 全屏模式';
                });
            }
        });
        
        // 音频测试按钮
        const audioTestBtn = document.getElementById('audioTestBtn');
        audioTestBtn.addEventListener('click', function() {
            console.log('音频测试按钮被点击');
            
            // 初始化或恢复音频上下文
            if (!audioContext) {
                initAudioContext(44100, 2);
            }
            
            if (audioContext && audioContext.state === 'suspended') {
                audioContext.resume().then(() => {
                    console.log('音频上下文已恢复');
                    testTone();
                });
            } else {
                testTone();
            }
        });
        
        function testTone() {
            console.log('播放测试音');
            
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.type = 'sine';
            oscillator.frequency.value = 440; // A 音
            gainNode.gain.value = 0.5;
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.start();
            console.log('测试音开始播放');
            
            setTimeout(() => {
                oscillator.stop();
                console.log('测试音结束');
            }, 1000);
        }
        
        document.addEventListener('fullscreenchange', function() {
            isFullscreen = !!document.fullscreenElement;
            fullscreenBtn.textContent = isFullscreen ? '⛶ 退出全屏' : '⛶ 全屏模式';
        });
        
        window.addEventListener('resize', function() {
            setTimeout(() => {
                const container = document.getElementById('videoContainer');
                canvas.style.width = container.clientWidth + 'px';
                canvas.style.height = container.clientHeight + 'px';
            }, 100);
        });
        
        connectWebSocket();
        
        setInterval(function() {
            if (!isConnected) {
                connectWebSocket();
            }
        }, 5000);
    </script>
</body>
</html>
"""
        
        with open(os.path.join(web_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        with self._lock:
            return {
                'enabled': self.config.enabled,
                'running': self.is_running,
                'capturing': self.is_capturing,
                'client_count': len(self.clients),
                'port': self.port,
                'ws_port': self.ws_port,
                'fps': self.config.fps,
                'quality': self.config.quality,
                'scale': self.config.scale,
                'preset': self.config.preset,
                'hdr': self.config.use_hdr
            }

screen_monitor = ScreenMonitor()
