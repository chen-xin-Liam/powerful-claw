"""
统一异常体系

所有自定义异常继承 AppError，携带以下统一字段：
  code:    ErrorCode 枚举，用于程序判断与日志检索
  message: 面向用户的简明消息（中文）
  details: 额外结构化上下文（dict），如 {"host":..., "port":...}
  cause:   原始异常（保留异常链，便于 traceback 排查）
  module:  抛出异常的模块名（自动从调用栈推断，无需手填）

输出格式：[E{code:04d}][{module}] {message}
"""

import sys
from typing import Any, Dict, Optional

from src.utils.error_codes import ErrorCode


class AppError(Exception):
    """所有自定义异常的基类。"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
        module: Optional[str] = None,
    ):
        self.code: ErrorCode = code
        self.message: str = message
        self.details: Dict[str, Any] = details or {}
        self.cause: Optional[BaseException] = cause
        self.module: str = module or self._guess_module()
        super().__init__(message)
        if cause is not None:
            # 显式保留异常链，traceback 模块可正常展开原始堆栈
            self.__cause__ = cause

    @staticmethod
    def _guess_module() -> str:
        """从调用栈自动取调用方模块名。

        _guess_module 是静态方法，调用栈为：
          [0] _guess_module 自身
          [1] AppError.__init__
          [2] 实际 raise AppError(...) 的调用方帧
        """
        try:
            frame = sys._getframe(2)
            return frame.f_globals.get("__name__", "unknown")
        except (ValueError, AttributeError):
            return "unknown"

    def __str__(self) -> str:
        return f"[E{int(self.code):04d}][{self.module}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(code={self.code.name}, "
            f"message={self.message!r}, module={self.module!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """供 api_server / websocket_server 序列化展示给前端。"""
        return {
            "code": int(self.code),
            "code_name": self.code.name,
            "message": self.message,
            "module": self.module,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


# ───────── 分领域子类（对应错误码段位） ─────────

class ConfigError(AppError):
    """配置加载/校验失败（1xxx）。"""

class ValidationError(AppError):
    """输入参数校验失败（5xxx）。"""

class ServiceError(AppError):
    """服务初始化/运行时失败（2xxx）。"""

class NetworkError(AppError):
    """socket / HTTP / WebSocket 通信失败（3xxx）。"""

class IOError_(AppError):
    """文件读写、磁盘操作失败（4xxx）。

    命名加下划线后缀，避免遮蔽 Python 内建 IOError。
    """

class ExternalDependencyError(AppError):
    """外部依赖缺失/调用失败（6xxx）：psutil、nvidia-smi、OpenCV、Tesseract、Whisper、transformers、ffmpeg 等。"""

class SubprocessError_(AppError):
    """subprocess 调用失败（7xxx）：超时、找不到可执行文件、非零退出码。

    命名加下划线后缀，避免遮蔽 subprocess.SubprocessError。
    """


# ───────── 解决建议映射 ─────────

_SUGGESTIONS: Dict[ErrorCode, str] = {
    ErrorCode.E_CONFIG_LOAD_FAILED:
        "请检查 .env / settings.json 文件格式，或参考 .env.example 重新生成",
    ErrorCode.E_CONFIG_FILE_NOT_FOUND:
        "请确认配置文件路径，或使用 --config 指定配置文件",
    ErrorCode.E_CONFIG_INVALID_VALUE:
        "请检查配置项取值是否在合法范围内",
    ErrorCode.E_CONFIG_THEME_INVALID:
        "主题名无效，可选值: dark / light / system",
    ErrorCode.E_SERVICE_START_FAILED:
        "请查看日志文件获取详细 traceback，常见原因: 端口占用、依赖缺失",
    ErrorCode.E_SERVICE_DEPENDENCY_MISSING:
        "请运行 pip install -r requirements.txt 安装依赖",
    ErrorCode.E_SERVICE_TIMEOUT:
        "服务启动超时（30s），请检查系统负载或相关外部资源是否可用",
    ErrorCode.E_NET_SOCKET_BIND:
        "端口被占用，请使用 --port / --api-port 指定其他端口",
    ErrorCode.E_NET_SOCKET_CONNECT:
        "目标地址不可达，请检查网络连接与对端服务状态",
    ErrorCode.E_NET_HTTP_REQUEST:
        "HTTP 请求失败，请检查网络/代理设置（--proxy）与 API Key",
    ErrorCode.E_NET_DISCOVERY_FAILED:
        "LAN 节点发现失败，请确认集群节点处于同一网段且防火墙放行",
    ErrorCode.E_CRYPTO_DECRYPT:
        "解密失败：密钥不匹配或数据被篡改，请勿将密文当作明文使用",
    ErrorCode.E_IO_FILE_NOT_FOUND:
        "文件不存在，请确认路径或重新生成所需资源",
    ErrorCode.E_IO_PERMISSION_DENIED:
        "权限不足，请以管理员身份运行或检查文件权限",
    ErrorCode.E_IO_DB_OPERATION:
        "数据库操作失败，请检查数据库文件完整性或磁盘空间",
    ErrorCode.E_VAL_INVALID_ARG:
        "参数类型/取值非法，请检查调用方传入的参数",
    ErrorCode.E_VAL_MISSING_REQUIRED:
        "必填参数缺失，请补全后重试",
    ErrorCode.E_VAL_OUT_OF_RANGE:
        "参数超出允许范围，请检查取值",
    ErrorCode.E_EXT_PSUTIL:
        "psutil 调用失败，请确认 psutil 已正确安装且系统支持",
    ErrorCode.E_EXT_NVIDIA_SMI:
        "未检测到 NVIDIA 显卡驱动，GPU 相关功能将不可用（如不需要可忽略）",
    ErrorCode.E_EXT_OPENCV:
        "OpenCV 调用失败，请确认 opencv-python 已安装",
    ErrorCode.E_EXT_TESSERACT:
        "Tesseract OCR 不可用，请安装 Tesseract 并加入 PATH",
    ErrorCode.E_EXT_WHISPER:
        "Whisper 语音识别调用失败，请确认模型已下载",
    ErrorCode.E_EXT_TRANSFORMERS:
        "transformers 模型加载失败，请确认模型名称与网络",
    ErrorCode.E_EXT_FFMPEG:
        "FFmpeg 不可用，请安装 FFmpeg 并加入 PATH",
    ErrorCode.E_EXT_MOVIEPY:
        "moviepy 调用失败，请确认 FFmpeg 已安装",
    ErrorCode.E_SUBPROCESS_TIMEOUT:
        "子进程执行超时，请确认目标命令是否需要交互或调大 timeout",
    ErrorCode.E_SUBPROCESS_NOT_FOUND:
        "目标命令不存在或未加入 PATH",
    ErrorCode.E_SUBPROCESS_NONZERO_EXIT:
        "子进程非零退出，请查看其 stderr 输出",
    ErrorCode.E_FATAL_UNEXPECTED:
        "发生未预期错误，请查看日志文件获取完整 traceback 并反馈",
}


def get_suggestion(code: ErrorCode) -> str:
    """按错误码返回解决建议文本，未映射时返回通用提示。"""
    return _SUGGESTIONS.get(code, "请查看日志文件获取详细信息")


__all__ = [
    "AppError",
    "ConfigError",
    "ValidationError",
    "ServiceError",
    "NetworkError",
    "IOError_",
    "ExternalDependencyError",
    "SubprocessError_",
    "get_suggestion",
]
