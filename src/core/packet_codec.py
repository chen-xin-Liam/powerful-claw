# -*- coding: utf-8 -*-
"""
packet_codec - PCN1 二进制封包编解码

帧格式（小端）：
    "PCN1" | version u8 | type u8 | flags u8 | reserved u8
    sequence u32 | payload_len u32 | payload... | crc32 u32

原生 pcnative 后端可用时走 C++，否则使用 zlib/struct 回退实现；
两条路径产物完全一致。本模块不含加密/TLS。
"""
import struct
import zlib
from typing import Tuple

MAGIC = b"PCN1"
VERSION = 1
_HEADER = struct.Struct("<4sBBBBII")   # 16 字节

try:
    from src.core.native import pcnative_backend as _backend

    _NATIVE = _backend.NATIVE_AVAILABLE
except Exception:  # pragma: no cover - 绑定层自身异常不应影响导入
    _NATIVE = False


def backend_name() -> str:
    if _NATIVE:
        return _backend.backend_name()
    return "python"


def pack_message(msg_type: int, sequence: int,
                 payload: bytes = b"") -> bytes:
    """打包 PCN1 帧。"""
    payload = bytes(payload or b"")
    if _NATIVE:
        return _backend.pack_message(msg_type, sequence, payload)

    head = _HEADER.pack(MAGIC, VERSION, int(msg_type) & 0xFF, 0, 0,
                        int(sequence) & 0xFFFFFFFF, len(payload))
    body = head + payload
    return body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


def unpack_message(frame: bytes) -> Tuple[int, int, bytes]:
    """解析 PCN1 帧，返回 (msg_type, sequence, payload)。

    任何结构/长度/校验失败均抛 ValueError。
    """
    if _NATIVE:
        return _backend.unpack_message(frame)

    if not isinstance(frame, (bytes, bytearray)):
        raise ValueError("帧必须为 bytes")
    if len(frame) < _HEADER.size + 4:
        raise ValueError("帧长度不足")
    magic, version, msg_type, _flags, _reserved, sequence, plen = \
        _HEADER.unpack_from(frame, 0)
    if magic != MAGIC:
        raise ValueError("魔数不匹配")
    if version != VERSION:
        raise ValueError(f"不支持的版本: {version}")
    total = _HEADER.size + plen + 4
    if len(frame) != total:
        raise ValueError("长度字段与帧实际长度不一致")
    expect = struct.unpack_from("<I", frame, _HEADER.size + plen)[0]
    actual = zlib.crc32(frame[:_HEADER.size + plen]) & 0xFFFFFFFF
    if expect != actual:
        raise ValueError("CRC32 校验失败")
    payload = bytes(frame[_HEADER.size:_HEADER.size + plen])
    return msg_type, sequence, payload
