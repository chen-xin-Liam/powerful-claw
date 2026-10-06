"""
安全传输模块
实现加密的数据传输协议

重要安全策略：
  - encrypt / decrypt / sign_message 失败时抛 ServiceError，绝不返回原文/空字符串，
    避免调用方误把明文当密文（或反之）使用。
  - verify_signature 失败返回 False 是合理的密码学模式（验证函数语义），保留。
"""

import hashlib
import base64
import json
import time
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Optional, Tuple
import uuid

from src.utils.logger import get_logger
from src.utils.errors import ServiceError
from src.utils.error_codes import ErrorCode

logger = get_logger(__name__)

# 默认允许的收发时钟偏差/消息有效期（秒）
DEFAULT_ALLOWED_SKEW = 300
# 重放缓存条目上限，防止无界增长
_REPLAY_CACHE_CAP = 5000


class SecureTransport:
    """安全传输管理器"""

    def __init__(self, allowed_skew: int = DEFAULT_ALLOWED_SKEW):
        self.symmetric_key = Fernet.generate_key()
        self.fernet = Fernet(self.symmetric_key)
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.node_id = str(uuid.uuid4())
        self.peer_keys: Dict[str, bytes] = {}
        # 消息有效期 / 允许时钟偏差（秒）
        self.allowed_skew = int(allowed_skew) if allowed_skew and allowed_skew > 0 else DEFAULT_ALLOWED_SKEW
        # 重放检测：(node_id, nonce) -> 首次见到的 unix 秒
        self._seen_nonces: Dict[Tuple[str, str], int] = {}

    def encrypt(self, data: str) -> str:
        """加密数据。

        失败时抛 ServiceError，绝不返回原文（避免明文被当作密文发送）。
        """
        try:
            return self.fernet.encrypt(data.encode('utf-8')).decode('utf-8')
        except (TypeError, ValueError) as e:
            logger.error(f"加密失败: {e}", exc_info=True)
            raise ServiceError(
                ErrorCode.E_CRYPTO_DECRYPT,
                f"加密失败: {e}",
                details={"data_len": len(data) if isinstance(data, str) else None},
                cause=e,
            ) from e

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据。

        失败时抛 ServiceError，绝不返回密文（避免调用方误把密文当明文使用）。
        """
        try:
            return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except (InvalidToken, TypeError, ValueError) as e:
            logger.error(f"解密失败: {e}", exc_info=True)
            raise ServiceError(
                ErrorCode.E_CRYPTO_DECRYPT,
                f"解密失败: 密钥不匹配或数据被篡改",
                details={"data_len": len(encrypted_data) if isinstance(encrypted_data, str) else None},
                cause=e,
            ) from e

    def encrypt_with_public_key(self, data: str, public_key_bytes: bytes) -> str:
        """使用公钥加密（用于密钥交换）。

        失败时抛 ServiceError，避免返回明文。
        """
        try:
            public_key = serialization.load_pem_public_key(public_key_bytes)
            encrypted = public_key.encrypt(
                data.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"公钥加密失败: {e}", exc_info=True)
            raise ServiceError(
                ErrorCode.E_CRYPTO_DECRYPT,
                f"公钥加密失败: {e}",
                cause=e,
            ) from e

    def decrypt_with_private_key(self, encrypted_data: str) -> str:
        """使用私钥解密。

        失败时抛 ServiceError，避免返回密文。
        """
        try:
            encrypted = base64.b64decode(encrypted_data)
            decrypted = self.private_key.decrypt(
                encrypted,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"私钥解密失败: {e}", exc_info=True)
            raise ServiceError(
                ErrorCode.E_CRYPTO_DECRYPT,
                f"私钥解密失败: {e}",
                cause=e,
            ) from e

    def get_public_key_pem(self) -> str:
        """获取PEM格式的公钥"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def sign_message(self, message: str) -> str:
        """签名消息。

        失败时抛 ServiceError，避免返回空字符串（空签名会让 verify 失败但调用方可能不检查）。
        """
        try:
            signature = self.private_key.sign(
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"签名失败: {e}", exc_info=True)
            raise ServiceError(
                ErrorCode.E_CRYPTO_DECRYPT,
                f"签名失败: {e}",
                cause=e,
            ) from e

    def verify_signature(self, message: str, signature: str, public_key_pem: str) -> bool:
        """验证签名。

        返回 bool 是密码学验证函数的标准语义（验证成功 True / 验证失败 False），保留。
        异常情况（公钥格式错误等）记录日志并返回 False。
        """
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
            signature_bytes = base64.b64decode(signature)
            public_key.verify(
                signature_bytes,
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            # 签名验证失败是常态（伪造签名、密钥不匹配），用 debug 级别避免噪音
            logger.debug(f"签名验证失败: {e}")
            return False

    @staticmethod
    def _canonical_payload(message: Dict[str, Any]) -> str:
        """计算被签名的规范化载荷：剔除 signature 字段后稳定序列化。

        签名与验签必须使用完全一致的序列化规则。
        """
        payload = {k: v for k, v in message.items() if k != "signature"}
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _peer_public_pem(self, node_id: str) -> Optional[str]:
        """按 node_id 解析发送方公钥（PEM 文本）。

        - 来自本节点的消息使用本节点公钥（支持自发自收/回环节点）；
        - 其它节点必须已在 peer_keys 注册，否则无公钥可验，直接拒绝。
        """
        if node_id == self.node_id:
            return self.get_public_key_pem()
        key = self.peer_keys.get(node_id)
        if key is None:
            return None
        return key.decode("utf-8") if isinstance(key, (bytes, bytearray)) else str(key)

    def create_secure_message(self, message_type: str, data: Dict[str, Any]) -> str:
        """创建安全消息（真实时间戳 + 随机 nonce + 强制签名）。"""
        message = {
            "type": message_type,
            "data": data,
            "node_id": self.node_id,
            "timestamp": int(time.time()),
            "nonce": uuid.uuid4().hex,
        }

        # 对不含 signature 的规范化载荷签名
        message["signature"] = self.sign_message(self._canonical_payload(message))

        return self.encrypt(json.dumps(message))

    def parse_secure_message(self, encrypted_message: str) -> Optional[Dict[str, Any]]:
        """解析安全消息：强制结构、时间窗口、签名校验、重放检测。

        任一环节失败返回 None，绝不返回未经验证的消息。
        """
        try:
            decrypted = self.decrypt(encrypted_message)
            message = json.loads(decrypted)
        except ServiceError as e:
            logger.warning(f"解析安全消息失败（解密异常）: {e}")
            return None
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"解析安全消息失败（格式异常）: {e}")
            return None

        try:
            # 1. 结构校验
            if not isinstance(message, dict):
                logger.warning("安全消息不是 JSON 对象")
                return None
            node_id = message.get("node_id")
            timestamp = message.get("timestamp")
            nonce = message.get("nonce")
            signature = message.get("signature")
            if not isinstance(node_id, str) or not node_id:
                logger.warning("安全消息缺少 node_id")
                return None
            if not isinstance(signature, str) or not signature:
                logger.warning("安全消息缺少签名")
                return None
            if not isinstance(nonce, str) or not nonce:
                logger.warning("安全消息缺少 nonce")
                return None
            # bool 是 int 的子类，需显式排除
            if not isinstance(timestamp, int) or isinstance(timestamp, bool):
                logger.warning("安全消息时间戳非法")
                return None

            # 2. 时间窗口：过期或超出时钟偏差的消息拒绝
            now = int(time.time())
            if abs(now - timestamp) > self.allowed_skew:
                logger.warning(
                    f"安全消息超出有效期窗口: 偏差 {now - timestamp}s > {self.allowed_skew}s"
                )
                return None

            # 3. 强制验签：按 node_id 取公钥，验签规范化载荷
            public_pem = self._peer_public_pem(node_id)
            if public_pem is None:
                logger.warning(f"未知节点 {node_id}，无公钥可用于验签")
                return None
            if not self.verify_signature(self._canonical_payload(message), signature, public_pem):
                logger.warning("安全消息签名校验失败")
                return None

            # 4. 重放检测：同一 (node_id, nonce) 在窗口内只允许出现一次
            replay_key = (node_id, nonce)
            if replay_key in self._seen_nonces:
                logger.warning(f"检测到重放消息: node={node_id} nonce={nonce}")
                return None
            self._seen_nonces[replay_key] = now
            self._prune_replay_cache(now)

            return message
        except (KeyError, TypeError) as e:
            logger.warning(f"解析安全消息失败（结构异常）: {e}")
            return None

    def _prune_replay_cache(self, now: int) -> None:
        """清理过期 nonce；超上限时再淘汰最旧条目，防止无界增长。"""
        expired = [k for k, ts in self._seen_nonces.items() if now - ts > self.allowed_skew]
        for k in expired:
            self._seen_nonces.pop(k, None)
        if len(self._seen_nonces) > _REPLAY_CACHE_CAP:
            for k in sorted(self._seen_nonces, key=self._seen_nonces.get)[:_REPLAY_CACHE_CAP // 5]:
                self._seen_nonces.pop(k, None)

    def compute_checksum(self, data: str) -> str:
        """计算数据校验和"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def verify_checksum(self, data: str, checksum: str) -> bool:
        """验证数据校验和"""
        return self.compute_checksum(data) == checksum


# 测试
if __name__ == "__main__":
    transport = SecureTransport()

    print("=== 安全传输测试 ===")

    # 测试加密解密
    original = "Hello, World!"
    encrypted = transport.encrypt(original)
    decrypted = transport.decrypt(encrypted)
    print(f"原始: {original}")
    print(f"加密: {encrypted[:30]}...")
    print(f"解密: {decrypted}")
    print(f"匹配: {original == decrypted}")

    # 测试签名验证
    message = "Test message"
    signature = transport.sign_message(message)
    public_key = transport.get_public_key_pem()
    verified = transport.verify_signature(message, signature, public_key)
    print(f"\n签名验证: {verified}")

    # 测试安全消息
    secure_msg = transport.create_secure_message("test", {"key": "value"})
    parsed = transport.parse_secure_message(secure_msg)
    print(f"\n安全消息解析: {parsed}")
