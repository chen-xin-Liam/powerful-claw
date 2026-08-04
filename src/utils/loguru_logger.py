from loguru import logger
import sys
import os
from datetime import datetime
from typing import Optional
import threading

from src.config.app_config import settings


class LoguruLogger:
    """Loguru日志管理器 - 支持多格式输出和自动轮转"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 移除默认处理器
        logger.remove()
        
        # 创建日志目录
        os.makedirs(settings.log_dir, exist_ok=True)
        
        # 生成日志文件名（按日期命名）
        log_filename = f"{datetime.now().strftime('%Y-%m-%d')}.log"
        log_path = os.path.join(settings.log_dir, log_filename)
        
        # 配置文件输出（详细格式）
        logger.add(
            log_path,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=settings.log_level,
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="zip",
            encoding="utf-8"
        )
        
        # 配置控制台输出（简洁格式）
        logger.add(
            sys.stdout,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.log_level
        )
        
        self._initialized = True
    
    def get_logger(self):
        """获取logger实例"""
        return logger
    
    def debug(self, message: str, **kwargs):
        """调试级别日志"""
        logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息级别日志"""
        logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告级别日志"""
        logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误级别日志"""
        logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误级别日志"""
        logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """异常日志"""
        logger.exception(message, **kwargs)


# 创建全局日志实例
loguru_logger = LoguruLogger()
logger = loguru_logger.get_logger()
