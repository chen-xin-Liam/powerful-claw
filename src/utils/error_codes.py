"""
统一错误码定义

按千位分段，便于按段位范围过滤与日志检索：
  1xxx 配置
  2xxx 服务（业务层）
  3xxx 网络
  4xxx IO
  5xxx 校验
  6xxx 外部依赖
  7xxx 子进程
  9xxx 致命/未分类

新增错误码时按段位扩展，保持段位语义稳定。
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """错误码枚举。所有自定义异常 AppError 必须携带一个 ErrorCode。"""

    # ── 1xxx 配置 ──
    E_CONFIG_LOAD_FAILED      = 1001   # .env / settings.json 解析失败
    E_CONFIG_INVALID_VALUE    = 1002   # 配置项取值非法
    E_CONFIG_FILE_NOT_FOUND   = 1003   # 配置文件缺失
    E_CONFIG_THEME_INVALID    = 1004   # 主题名无效

    # ── 2xxx 服务（业务层） ──
    E_SERVICE_START_FAILED       = 2001   # 服务启动失败（线程级）
    E_SERVICE_STOP_FAILED        = 2002
    E_SERVICE_TIMEOUT            = 2003    # 线程启动超时
    E_SERVICE_DEPENDENCY_MISSING = 2004   # 必备 Python 包缺失
    E_SERVICE_ALREADY_RUNNING    = 2005

    # ── 3xxx 网络 ──
    E_NET_SOCKET_BIND      = 3001
    E_NET_SOCKET_CONNECT  = 3002
    E_NET_HTTP_REQUEST    = 3003   # requests 调用失败
    E_NET_WS_HANDSHAKE    = 3004
    E_NET_DISCOVERY_FAILED = 3005  # LAN 节点发现失败
    E_CRYPTO_DECRYPT      = 3401   # 解密失败（密文不可信，必须抛出而非返回原文）

    # ── 4xxx IO ──
    E_IO_FILE_NOT_FOUND     = 4001
    E_IO_PERMISSION_DENIED  = 4002
    E_IO_DISK_FULL          = 4003
    E_IO_DB_OPERATION       = 4004   # SQLAlchemy / sqlite 异常

    # ── 5xxx 校验 ──
    E_VAL_INVALID_ARG     = 5001   # 参数类型/取值非法
    E_VAL_MISSING_REQUIRED = 5002   # 必填参数缺失
    E_VAL_OUT_OF_RANGE     = 5003
    E_PERMISSION_HIGH_RISK_DENIED = 5004   # 高危操作被用户二次授权拒绝
    E_VALIDATION_MATH_ERROR = 5005   # 数学计算/节点图执行错误

    # ── 6xxx 外部依赖 ──
    E_EXT_DEPENDENCY_MISSING = 6000   # 通用外部依赖缺失
    E_EXT_PSUTIL        = 6001
    E_EXT_NVIDIA_SMI   = 6002   # nvidia-smi 调用失败/不可用
    E_EXT_OPENCV        = 6003
    E_EXT_TESSERACT     = 6004
    E_EXT_WHISPER       = 6005
    E_EXT_TRANSFORMERS  = 6006
    E_EXT_FFMPEG        = 6007
    E_EXT_MOVIEPY       = 6008

    # ── 7xxx 子进程 ──
    E_SUBPROCESS_TIMEOUT       = 7001
    E_SUBPROCESS_NOT_FOUND     = 7002   # FileNotFoundError: 命令不存在
    E_SUBPROCESS_NONZERO_EXIT  = 7003

    # ── 9xxx 致命/未分类 ──
    E_FATAL_UNEXPECTED = 9000


__all__ = ["ErrorCode"]
