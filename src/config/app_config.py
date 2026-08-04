from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationInfo, field_validator
from typing import Optional
import os
import json
import yaml


class AppSettings(BaseSettings):
    """应用配置类 - 支持从 env/json/yaml 加载配置"""
    
    # 应用基本信息
    app_name: str = Field(default="AI Assistant", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    
    # 服务配置
    host: str = Field(default="0.0.0.0", description="服务主机")
    port: int = Field(default=8000, description="服务端口", ge=1, le=65535)
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_dir: str = Field(default="logs", description="日志目录")
    log_rotation: str = Field(default="1 day", description="日志轮转周期")
    log_retention: str = Field(default="7 days", description="日志保留时间")
    
    # 数据库配置
    db_dir: str = Field(default="userspick", description="数据库目录")
    db_type: str = Field(default="sqlite", description="数据库类型")
    
    # Celery配置（使用本地模式，无需Redis）
    celery_broker_url: str = Field(default="memory://", description="Celery Broker URL - 使用内存模式")
    celery_result_backend: str = Field(default="cache+memory://", description="Celery结果后端 - 使用内存缓存")
    
    # 安全配置
    permission_level: str = Field(default="normal", description="权限级别")
    
    # 模型配置
    model_name: str = Field(default="Qwen/Qwen-1.8B-Chat", description="模型名称")
    max_tokens: int = Field(default=512, description="最大token数", ge=1, le=8192)
    temperature: float = Field(default=0.7, description="温度参数", ge=0.0, le=2.0)
    
    # 性能配置
    enable_profiling: bool = Field(default=False, description="是否启用性能分析")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )
    
    @field_validator('log_level')
    def validate_log_level(cls, v: str, info: ValidationInfo) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator('permission_level')
    def validate_permission_level(cls, v: str, info: ValidationInfo) -> str:
        valid_levels = ["normal", "advanced", "full", "admin"]
        if v.lower() not in valid_levels:
            raise ValueError(f"permission_level must be one of {valid_levels}")
        return v.lower()


class ConfigLoader:
    """配置加载器 - 支持从多种格式加载配置"""
    
    @staticmethod
    def load_from_json(file_path: str) -> dict:
        """从JSON文件加载配置"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def load_from_yaml(file_path: str) -> dict:
        """从YAML文件加载配置"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    @staticmethod
    def load_from_env() -> dict:
        """从环境变量加载配置"""
        return os.environ.copy()
    
    @classmethod
    def load_all(cls, json_path: str = "config.json", yaml_path: str = "config.yaml") -> dict:
        """从所有来源加载配置（优先级：env > yaml > json）"""
        config = {}
        
        # 从JSON加载
        json_config = cls.load_from_json(json_path)
        config.update(json_config)
        
        # 从YAML加载（覆盖JSON）
        yaml_config = cls.load_from_yaml(yaml_path)
        config.update(yaml_config)
        
        # 从环境变量加载（覆盖所有）
        env_config = cls.load_from_env()
        for key, value in env_config.items():
            # 转换环境变量名（APP_NAME -> app_name）
            config_key = key.lower().replace('_', '.')
            config[config_key] = value
        
        return config


# 初始化配置
settings = AppSettings()

# 确保目录存在
os.makedirs(settings.log_dir, exist_ok=True)
os.makedirs(settings.db_dir, exist_ok=True)
