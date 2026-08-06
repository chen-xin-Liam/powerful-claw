from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    model_name: str = "z-ai/glm4.7"
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: int = 16384

    enable_thinking: bool = True
    clear_thinking: bool = False

    app_name: str = "AI Computer Control"
    app_version: str = "1.0.0"

    max_calls_per_minute: int = 40
    max_iterations: int = 10
    iteration_delay: float = 1.0

    host: str = "0.0.0.0"
    port: int = 8000
    websocket_port: int = 15000
    rcon_port: int = 15001
    api_port: int = 15002

    debug: bool = False
    noui: bool = False
    noweb: bool = False
    noeditor: bool = False
    nomonitor: bool = False

    screen_monitor_port: int = 15004
    screen_monitor_quality: int = 50
    screen_monitor_fps: int = 30
    screen_monitor_bitrate: int = 2500000

    video_editor_port: int = 15010

    log_level: str = "INFO"
    log_dir: str = "logs"
    log_rotation: str = "1 day"
    log_retention: str = "7 days"
    enable_file_logging: bool = False  # 是否启用文件日志保存

    enable_profiling: bool = False
    enable_systray: bool = True
    enable_auto_start: bool = False

    permission_level: str = "normal"

    # ── 高危操作二次授权 ──
    high_risk_confirmation: bool = True   # 二次授权总开关（True 开启，False 则高危操作直接拒绝）
    high_risk_timeout: int = 30           # 确认超时（秒，超时默认拒绝）
    high_risk_whitelist: str = ""         # 免确认命令（逗号分隔，如 ls,cat,whoami）
    high_risk_extra_blacklist: str = ""   # 追加黑名单关键词（逗号分隔）

    db_dir: str = "userspick"
    db_type: str = "sqlite"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    ai_provider: str = "openai"
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None

    max_history: int = 100
    auto_save: bool = True
    auto_save_interval: int = 300

    theme: str = "dark"
    theme_color: str = "blue"
    theme_name: str = "Ocean Blue"
    themes_dir: str = "config/themes"

    language: str = "zh_CN"
    timezone: str = "Asia/Shanghai"

    proxy_enabled: bool = False
    proxy_url: Optional[str] = None

    cert_enabled: bool = False
    cert_path: Optional[str] = None
    key_path: Optional[str] = None

settings = Settings()
