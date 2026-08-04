import os
import sys
import argparse
import signal
import time
import logging
import threading
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings
from src.utils.logger import setup_logger

logger = None  # 延迟初始化


class AppContext:
    _instance: Optional['AppContext'] = None

    def __init__(self):
        self.websocket_server = None
        self.api_server = None
        self.screen_monitor = None
        self.video_editor = None
        self.ai_service = None
        self.local_model_service = None
        self.is_running = False

    @classmethod
    def get_instance(cls) -> 'AppContext':
        if cls._instance is None:
            cls._instance = AppContext()
        return cls._instance


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI电脑控制 - 主程序入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                                # 正常运行
  python main.py --debug                        # 调试模式
  python main.py --noui                         # 无GUI模式
  python main.py --noweb                        # 不启动Web服务
  python main.py --port 15000                   # 指定WebSocket端口
  python main.py --theme dark                   # 设置主题
  python main.py --log-level DEBUG              # 设置日志级别
  python main.py --proxy http://127.0.0.1:7890  # 设置代理
  python main.py --help                         # 显示帮助  
        """
    )

    g_run = parser.add_argument_group("运行模式")
    g_run.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    g_run.add_argument("--noui", action="store_true", help="无GUI模式（终端模式）")
    g_run.add_argument("--noweb", action="store_true", help="不启动Web服务")
    g_run.add_argument("--noeditor", action="store_true", help="不启动视频剪辑服务")
    g_run.add_argument("--nomonitor", action="store_true", help="不启动桌面监控服务")
    g_run.add_argument("--nosystray", action="store_true", help="不显示系统托盘")
    g_run.add_argument("--autorestart", action="store_true", help="服务崩溃后自动重启")

    g_server = parser.add_argument_group("服务器设置")
    g_server.add_argument("--host", type=str, default=None, help="监听地址")
    g_server.add_argument("--port", "-p", type=int, default=None, help="WebSocket端口")
    g_server.add_argument("--api-port", type=int, default=None, help="API端口")
    g_server.add_argument("--rcon-port", type=int, default=None, help="RCON端口")
    g_server.add_argument("--monitor-port", type=int, default=None, help="桌面监控端口")
    g_server.add_argument("--editor-port", type=int, default=None, help="视频编辑端口")

    g_monitor = parser.add_argument_group("桌面监控设置")
    g_monitor.add_argument("--monitor-quality", type=int, default=None, help="监控画质 (1-100)")
    g_monitor.add_argument("--monitor-fps", type=int, default=None, help="监控帧率")
    g_monitor.add_argument("--monitor-bitrate", type=int, default=None, help="监控码率")
    g_monitor.add_argument("--monitor-audio", action="store_true", help="启用音频监控")
    g_monitor.add_argument("--monitor-udp", action="store_true", help="使用UDP传输")

    g_editor = parser.add_argument_group("视频剪辑设置")
    g_editor.add_argument("--editor-quality", type=str, default=None, help="导出质量 (low/medium/high)")
    g_editor.add_argument("--editor-format", type=str, default=None, help="导出格式 (mp4/mov/webm)")

    g_log = parser.add_argument_group("日志设置")
    g_log.add_argument("--log-level", type=str, default=None, choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别")
    g_log.add_argument("--log-dir", type=str, default=None, help="日志目录")
    g_log.add_argument("--log-file", type=str, default=None, help="日志文件名")
    g_log.add_argument("--log-console", action="store_true", default=None, help="启用控制台日志")
    g_log.add_argument("--nolog", action="store_true", help="禁用日志文件保存（正常运行时不保存）")

    g_ui = parser.add_argument_group("界面设置")
    g_ui.add_argument("--theme", type=str, default=None, choices=["dark", "light", "system"], help="界面主题")
    g_ui.add_argument("--theme-color", type=str, default=None, help="主题颜色 (blue/green/dark-blue)")
    g_ui.add_argument("--language", type=str, default=None, help="语言")
    g_ui.add_argument("--fullscreen", action="store_true", help="全屏启动")
    g_ui.add_argument("--window-size", type=str, default=None, help="窗口大小 (如 1200x800)")

    g_ai = parser.add_argument_group("AI设置")
    g_ai.add_argument("--ai-provider", type=str, default=None, help="AI提供商")
    g_ai.add_argument("--ai-model", type=str, default=None, help="AI模型")
    g_ai.add_argument("--ai-api-key", type=str, default=None, help="API密钥")
    g_ai.add_argument("--ai-base-url", type=str, default=None, help="API地址")
    g_ai.add_argument("--ai-max-tokens", type=int, default=None, help="最大Token数")
    g_ai.add_argument("--ai-temperature", type=float, default=None, help="温度参数")

    g_proxy = parser.add_argument_group("代理设置")
    g_proxy.add_argument("--proxy-enable", action="store_true", default=None, help="启用代理")
    g_proxy.add_argument("--proxy", type=str, default=None, help="代理地址 (http://host:port)")

    g_ssl = parser.add_argument_group("SSL/TLS设置")
    g_ssl.add_argument("--ssl-enable", action="store_true", default=None, help="启用SSL")
    g_ssl.add_argument("--ssl-cert", type=str, default=None, help="证书文件路径")
    g_ssl.add_argument("--ssl-key", type=str, default=None, help="密钥文件路径")

    g_perf = parser.add_argument_group("性能设置")
    g_perf.add_argument("--max-history", type=int, default=None, help="最大历史记录数")
    g_perf.add_argument("--auto-save", action="store_true", default=None, help="启用自动保存")
    g_perf.add_argument("--profiling", action="store_true", default=None, help="启用性能分析")

    g_db = parser.add_argument_group("数据库设置")
    g_db.add_argument("--db-dir", type=str, default=None, help="数据库目录")
    g_db.add_argument("--db-type", type=str, default=None, help="数据库类型")

    g_cfg = parser.add_argument_group("配置文件")
    g_cfg.add_argument("--config", "-c", type=str, default=None, help="指定配置文件路径")
    g_cfg.add_argument("--save-config", type=str, default=None, help="保存当前配置到文件")

    return parser.parse_args()


def resolve_bool(env_val: bool, cli_val: Optional[bool]) -> bool:
    if cli_val is not None:
        return cli_val
    return env_val

def resolve_int(env_val: int, cli_val: Optional[int]) -> int:
    if cli_val is not None:
        return cli_val
    return env_val

def resolve_str(env_val: str, cli_val: Optional[str]) -> str:
    if cli_val is not None:
        return cli_val
    return env_val


def setup_signal_handlers():
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在停止服务...")
        stop_all_services()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def stop_all_services():
    ctx = AppContext.get_instance()
    ctx.is_running = False

    if ctx.websocket_server:
        logger.info("停止WebSocket服务器...")
        ctx.websocket_server.stop()
    if ctx.api_server:
        logger.info("停止API服务器...")
        ctx.api_server.stop()
    if ctx.screen_monitor:
        logger.info("停止桌面监控服务...")
        ctx.screen_monitor.stop()
    if ctx.video_editor:
        logger.info("停止视频剪辑服务器...")
        ctx.video_editor.stop()
    if ctx.ai_service:
        logger.info("停止AI服务...")
        if hasattr(ctx.ai_service, 'stop'):
            ctx.ai_service.stop()
    logger.info("所有服务已停止")


def _start_websocket_server(ctx, host, port):
    """启动WebSocket服务器（线程函数）"""
    try:
        from src.services.websocket_server import WebSocketServer
        logger.info(f"启动 WebSocket 服务: {host}:{port}")
        ctx.websocket_server = WebSocketServer(host=host, port=port)
        ctx.websocket_server.start()
        logger.info(f"WebSocket 服务启动成功: {host}:{port}")
    except Exception as e:
        logger.error(f"WebSocket 服务启动失败: {e}")

def _start_api_server(ctx, host, port):
    """启动API服务器（线程函数）"""
    try:
        from src.services.api_server import APIServer
        logger.info(f"启动 API 服务: {host}:{port}")
        ctx.api_server = APIServer(host=host, port=port)
        ctx.api_server.start()
        logger.info(f"API 服务启动成功: {host}:{port}")
    except Exception as e:
        logger.error(f"API 服务启动失败: {e}")

def _start_screen_monitor(ctx, monitor_port, quality, fps, bitrate):
    """启动桌面监控服务（线程函数）"""
    try:
        from src.services.screen_monitor import screen_monitor
        screen_monitor.port = monitor_port
        if quality:
            screen_monitor.quality = quality
        if fps:
            screen_monitor.fps = fps
        if bitrate:
            screen_monitor.bitrate = bitrate
        logger.info(f"启动桌面监控服务: {monitor_port}")
        screen_monitor.start()
        ctx.screen_monitor = screen_monitor
        logger.info(f"桌面监控服务启动成功: {monitor_port}")
    except Exception as e:
        logger.error(f"桌面监控服务启动失败: {e}")

def _start_video_editor(ctx, editor_port):
    """启动视频剪辑服务（线程函数）"""
    try:
        from src.services.video_editor import VideoEditor
        logger.info(f"启动视频剪辑服务: {editor_port}")
        ctx.video_editor = VideoEditor()
        ctx.video_editor.port = editor_port
        ctx.video_editor.start()
        logger.info(f"视频剪辑服务启动成功: {editor_port}")
    except Exception as e:
        logger.error(f"视频剪辑服务启动失败: {e}")

def _start_ai_service(ctx):
    """启动AI服务（线程函数）"""
    try:
        from src.services.ai_service import AIService
        logger.info("启动 AI 服务...")
        ctx.ai_service = AIService()
        logger.info("AI 服务启动成功")
    except Exception as e:
        logger.error(f"AI 服务启动失败: {e}")

def _start_local_model_service(ctx):
    """启动本地模型服务（线程函数）"""
    try:
        from src.services.local_model_service import LocalModelService
        logger.info("启动本地模型服务...")
        ctx.local_model_service = LocalModelService()
        logger.info("本地模型服务启动成功")
    except Exception as e:
        logger.error(f"本地模型服务启动失败: {e}")

def start_services(args):
    """使用多线程并行启动所有服务"""
    ctx = AppContext.get_instance()

    host = resolve_str(settings.host, args.host)
    ws_port = resolve_int(settings.websocket_port, args.port)
    api_port = resolve_int(settings.api_port, args.api_port)
    monitor_port = resolve_int(settings.screen_monitor_port, args.monitor_port)
    editor_port = resolve_int(settings.video_editor_port, args.editor_port)

    noweb_mode = resolve_bool(settings.noweb, args.noweb)
    noeditor_mode = resolve_bool(settings.noeditor, args.noeditor)
    nomonitor_mode = resolve_bool(settings.nomonitor, args.nomonitor)
    debug_mode = resolve_bool(settings.debug, args.debug)

    logger.info("=" * 50)
    logger.info("AI电脑控制 - 服务启动")
    logger.info("=" * 50)
    logger.info(f"运行模式: {'终端' if args.noui else 'GUI'}")
    logger.info(f"调试模式: {'启用' if debug_mode else '禁用'}")
    logger.info(f"Web服务: {'禁用' if noweb_mode else '启用'}")
    logger.info(f"视频剪辑服务: {'禁用' if noeditor_mode else '启用'}")
    logger.info(f"桌面监控服务: {'禁用' if nomonitor_mode else '启用'}")
    logger.info("使用多线程并行启动服务...")

    # 创建线程列表
    threads = []

    # Web服务线程组
    if not noweb_mode:
        ws_thread = threading.Thread(
            target=_start_websocket_server,
            args=(ctx, host, ws_port),
            name="WebSocketServer",
            daemon=True
        )
        threads.append(ws_thread)

        api_thread = threading.Thread(
            target=_start_api_server,
            args=(ctx, host, api_port),
            name="APIServer",
            daemon=True
        )
        threads.append(api_thread)

    # 桌面监控线程
    if not nomonitor_mode:
        monitor_thread = threading.Thread(
            target=_start_screen_monitor,
            args=(ctx, monitor_port, args.monitor_quality, args.monitor_fps, args.monitor_bitrate),
            name="ScreenMonitor",
            daemon=True
        )
        threads.append(monitor_thread)

    # 视频剪辑线程
    if not noeditor_mode:
        editor_thread = threading.Thread(
            target=_start_video_editor,
            args=(ctx, editor_port),
            name="VideoEditor",
            daemon=True
        )
        threads.append(editor_thread)

    # AI服务线程
    ai_thread = threading.Thread(
        target=_start_ai_service,
        args=(ctx,),
        name="AIService",
        daemon=True
    )
    threads.append(ai_thread)

    # 本地模型服务线程
    local_model_thread = threading.Thread(
        target=_start_local_model_service,
        args=(ctx,),
        name="LocalModelService",
        daemon=True
    )
    threads.append(local_model_thread)

    # 启动所有线程
    for thread in threads:
        thread.start()
        logger.debug(f"启动线程: {thread.name}")

    # 等待所有线程启动完成（带超时）
    timeout = 30  # 最大等待30秒
    start_time = time.time()
    
    for thread in threads:
        elapsed = time.time() - start_time
        remaining = max(0, timeout - elapsed)
        thread.join(remaining)
        
        if thread.is_alive():
            logger.warning(f"线程 {thread.name} 启动超时，继续等待其他服务...")

    ctx.is_running = True
    logger.info("=" * 50)
    logger.info("所有服务启动完成")
    logger.info("=" * 50)


def run_ui(args):
    from src.ui.customtkinter_app import CustomTkinterApp

    if args.theme:
        import customtkinter as ctk
        ctk.set_appearance_mode(args.theme)
    elif settings.theme:
        import customtkinter as ctk
        ctk.set_appearance_mode(settings.theme)

    if args.theme_color:
        import customtkinter as ctk
        ctk.set_default_color_theme(args.theme_color)
    elif settings.theme_color:
        import customtkinter as ctk
        ctk.set_default_color_theme(settings.theme_color)

    app = CustomTkinterApp()
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)

    if args.fullscreen:
        app.root.attributes("-fullscreen", True)

    if args.window_size:
        try:
            w, h = map(int, args.window_size.split('x'))
            app.root.geometry(f"{w}x{h}")
        except:
            pass

    app.run()


def main():
    global logger
    
    args = parse_args()

    debug_mode = resolve_bool(settings.debug, args.debug)
    
    # 确定是否启用文件日志保存
    # debug模式默认开启日志保存，除非使用-nolog参数
    # 正常模式默认不保存日志
    enable_file_logging = debug_mode and not args.nolog
    
    if args.log_level:
        log_level = args.log_level
    elif debug_mode:
        log_level = "DEBUG"
    else:
        log_level = settings.log_level
    
    # 初始化日志记录器
    logger = setup_logger(__name__, log_level=log_level, enable_file_logging=enable_file_logging)
    
    if debug_mode:
        os.environ["DEBUG"] = "1"
        os.environ["DEBUG_MODE"] = "true"
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("调试模式已启用")
    
    if enable_file_logging:
        logger.info("日志文件保存已启用")
    else:
        logger.info("日志文件保存已禁用")

    setup_signal_handlers()

    noui_mode = resolve_bool(settings.noui, args.noui)
    logger.info(f"启动模式: {'终端' if noui_mode else 'GUI'}")

    if noui_mode:
        start_services(args)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_all_services()
    else:
        start_services(args)
        run_ui(args)


if __name__ == "__main__":
    main()
