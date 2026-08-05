import logging
import os
import sys
from datetime import datetime


def _color_enabled() -> bool:
    """判断是否启用终端着色。

    启用条件：标准输出是 TTY 且未设置 NO_COLOR 环境变量。
    重定向到文件时自动禁用，避免日志文件出现 ANSI 转义码。
    """
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return bool(sys.stdout.isatty())
    except (AttributeError, ValueError):
        return False


class ColorFormatter(logging.Formatter):
    """仅对 levelname 着色，不染整行，保持日志可读。

    ERROR 红 / WARNING 黄 / INFO 绿 / DEBUG 青 / CRITICAL 品红
    依赖 colorama（已在 requirements.txt:15），但在非 Windows 平台也兼容原始 ANSI。
    """

    _COLORS = {
        logging.DEBUG:    "\033[36m",   # cyan
        logging.INFO:     "\033[32m",   # green
        logging.WARNING:  "\033[33m",   # yellow
        logging.ERROR:    "\033[31m",   # red
        logging.CRITICAL: "\033[35m",   # magenta
    }
    _RESET = "\033[0m"

    def __init__(self, fmt: str = None, datefmt: str = None, use_color: bool = True):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if self._use_color:
            color = self._COLORS.get(record.levelno)
            if color:
                # 用副本避免污染其他 handler 共享的 record
                record = logging.makeLogRecord(record.__dict__)
                record.levelname = f"{color}{record.levelname}{self._RESET}"
        return super().format(record)


_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logger(
    name: str = "ai_control",
    log_level: str = "INFO",
    enable_file_logging: bool = True,
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        enable_file_logging: 是否启用文件日志保存

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    use_color = _color_enabled()
    plain_formatter = logging.Formatter(_DEFAULT_FORMAT)
    color_formatter = ColorFormatter(_DEFAULT_FORMAT, use_color=use_color)

    # 控制台日志（按需着色）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter if use_color else plain_formatter)
    logger.addHandler(console_handler)

    # 文件日志（可选，始终无 ANSI 码）
    if enable_file_logging:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(plain_formatter)
        logger.addHandler(file_handler)

    return logger


# 兜底配置记录：避免服务模块在 setup_logger 之前 import 时出现 "No handlers found" 警告
_CONFIGURED_LOGGERS: set = set()


def get_logger(name: str) -> logging.Logger:
    """便捷获取 logger。

    - 若 logger 已有 handler（已被 setup_logger 配置过）则直接返回；
    - 否则给一个 INFO 级别 + StreamHandler 的兜底 handler，
      并标记 propagate=False，避免重复打印。

    服务模块统一使用：logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    if name in _CONFIGURED_LOGGERS:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    use_color = _color_enabled()
    handler = logging.StreamHandler()
    handler.setFormatter(
        ColorFormatter(_DEFAULT_FORMAT, use_color=use_color) if use_color
        else logging.Formatter(_DEFAULT_FORMAT)
    )
    logger.addHandler(handler)
    _CONFIGURED_LOGGERS.add(name)
    return logger


__all__ = ["setup_logger", "get_logger", "ColorFormatter"]
