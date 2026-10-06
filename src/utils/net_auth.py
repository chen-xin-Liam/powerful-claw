# -*- coding: utf-8 -*-
"""网络鉴权基础组件（NetAuth）

为 api_server / websocket_server / cluster_api 提供统一、最小依赖的鉴权能力：

- Token 解析优先级：环境变量 ``PCNATIVE_API_TOKEN`` → ``.env`` 中的 ``API_TOKEN``
  → 缺失时用 :func:`secrets.token_urlsafe` 生成并回写 ``.env``（不抛错）。
- 回环地址（127.0.0.0/8、::1、localhost）放行；其余地址必须提供有效 Token。
- Token 比较使用 :func:`hmac.compare_digest` 恒定时间比较。
- Token 不写入日志。

本模块不依赖 ``websockets``（惰性导入），便于在未安装该库时做单元测试。
"""

import asyncio
import hmac
import ipaddress
import json
import os
import re
import secrets
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

# 解析顺序固定的键名
_TOKEN_ENV_VAR = "PCNATIVE_API_TOKEN"
_ENV_TOKEN_KEY = "API_TOKEN"

# src/utils/net_auth.py → 项目根（上溯三级）
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")

# .env 中 KEY=VALUE 形式（值可带引号）
_ENV_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")

# 首条消息携带 Token 的等待时长（秒）
HANDSHAKE_TOKEN_TIMEOUT = 5.0


def project_root() -> str:
    """返回项目根目录绝对路径。"""
    return _PROJECT_ROOT


def _strip_quotes(value: str) -> str:
    """去掉 .env 值两侧成对的单/双引号。"""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def read_env_value(key: str, env_path: Optional[str] = None) -> Optional[str]:
    """读取 .env 中指定键的值；不存在或文件缺失返回 None。"""
    path = env_path or _ENV_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                m = _ENV_LINE_RE.match(line.rstrip("\n"))
                if m and m.group(1) == key:
                    return _strip_quotes(m.group(2))
    except OSError:
        return None
    return None


def write_env_value(key: str, value: str, env_path: Optional[str] = None) -> bool:
    """更新或追加 .env 中的键值（保留其余内容）。失败返回 False，不抛异常。"""
    path = env_path or _ENV_PATH
    try:
        lines = []
        found = False
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().split("\n")
        for i, line in enumerate(lines):
            m = _ENV_LINE_RE.match(line)
            if m and m.group(1) == key:
                lines[i] = f'{key}="{value}"'
                found = True
        if not found:
            if lines and lines[-1].strip() != "":
                lines.append(f'{key}="{value}"')
            else:
                # 避免在文件末尾留下重复空行
                lines.append(f'{key}="{value}"')
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return True
    except OSError:
        return False


def get_token() -> str:
    """返回当前有效 Token；缺失则安全生成并持久化到 .env。"""
    token = os.environ.get(_TOKEN_ENV_VAR, "").strip()
    if token:
        return token

    token = (read_env_value(_ENV_TOKEN_KEY) or "").strip()
    if token:
        # 让当前进程也能直接读到
        os.environ[_TOKEN_ENV_VAR] = token
        return token

    token = secrets.token_urlsafe(32)
    write_env_value(_ENV_TOKEN_KEY, token)
    os.environ[_TOKEN_ENV_VAR] = token
    return token


def is_loopback(host: Any) -> bool:
    """判断主机是否为回环地址（localhost / 127.0.0.0/8 / ::1）。"""
    if host is None:
        return False
    text = str(host).strip().lower()
    if text in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


def token_valid(provided: Any) -> bool:
    """恒定时间比较：provided 与当前 Token 是否一致；空值直接 False。"""
    if provided is None:
        return False
    text = str(provided)
    if not text:
        return False
    return hmac.compare_digest(get_token(), text)


def _token_from_query(path_or_url: Optional[str]) -> Optional[str]:
    """从路径/URL 的 ?token= 查询参数提取 Token。"""
    if not path_or_url:
        return None
    try:
        query = urlparse(str(path_or_url)).query
        values = parse_qs(query).get("token")
        if values:
            return values[0]
    except (ValueError, AttributeError):
        return None
    return None


def _websocket_path(websocket: Any, path: Optional[str]) -> Optional[str]:
    """兼容不同 websockets 版本取得握手路径。"""
    if path:
        return path
    for attr in ("path",):
        val = getattr(websocket, attr, None)
        if isinstance(val, str):
            return val
    request = getattr(websocket, "request", None)
    if request is not None:
        val = getattr(request, "path", None)
        if isinstance(val, str):
            return val
    return None


async def authorize_websocket(websocket: Any, path: Optional[str] = None) -> bool:
    """WebSocket 连接鉴权。

    - 回环对端直接放行；
    - 否则依次尝试：握手路径 ``?token=`` → 首条消息携带的 Token
      （纯文本 Token，或 JSON ``{"token": "..."}`` / ``{"data": {"token": "..."}}``）；
    - 首条消息超时或 Token 无效返回 False（调用方应关闭连接）。
    """
    remote = getattr(websocket, "remote_address", None)
    host = remote[0] if remote else ""
    if is_loopback(host):
        return True

    token = _token_from_query(_websocket_path(websocket, path))
    if token and token_valid(token):
        return True

    try:
        message = await asyncio.wait_for(websocket.recv(), timeout=HANDSHAKE_TOKEN_TIMEOUT)
    except Exception:  # 连接关闭/超时统一拒绝；CancelledError 属 BaseException 不会被误吞
        return False

    provided: Optional[str] = None
    if isinstance(message, str):
        try:
            data = json.loads(message)
        except (ValueError, TypeError):
            provided = message
        else:
            if isinstance(data, dict):
                provided = data.get("token")
                if not provided:
                    inner = data.get("data")
                    if isinstance(inner, dict):
                        provided = inner.get("token")
    return bool(provided) and token_valid(provided)


class TokenAuthMixin:
    """``http.server.BaseHTTPRequestHandler`` 鉴权混入。

    使用方式：让 Handler 继承本混入，并在处理请求前调用
    :meth:`_require_authorization`；返回 False 时已发送 401，应直接结束处理。
    """

    def _client_host(self) -> str:
        address = getattr(self, "client_address", None)
        return address[0] if address else ""

    def _extract_http_token(self) -> Optional[str]:
        # 1) Authorization: Bearer <token>
        headers = getattr(self, "headers", None)
        if headers is not None:
            auth = headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                return auth[7:].strip()
            # 兼容 X-API-Token
            direct = headers.get("X-Api-Token", "")
            if direct:
                return direct.strip()
        # 2) ?token=
        token = _token_from_query(getattr(self, "path", ""))
        if token:
            return token
        return None

    def _is_authorized(self) -> bool:
        if is_loopback(self._client_host()):
            return True
        return token_valid(self._extract_http_token())

    def _send_unauthorized(self) -> None:
        body = json.dumps({"error": "unauthorized"}).encode("utf-8")
        try:
            self.send_response(401)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("WWW-Authenticate", 'Bearer realm="pcnative"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (OSError, BrokenPipeError):
            # 客户端已断开，无需再处理
            pass

    def _require_authorization(self) -> bool:
        """已授权返回 True；否则发送 401 并返回 False。"""
        if self._is_authorized():
            return True
        self._send_unauthorized()
        return False
