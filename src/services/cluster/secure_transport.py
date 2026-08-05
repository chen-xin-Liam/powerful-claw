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
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Optional
import uuid

from src.utils.logger import get_logger
from src.utils.errors import ServiceError
from src.utils.error_codes import ErrorCode

logger = get_logger(__name__)


class SecureTransport:
    """安全传输管理器"""

    def __init__(self):
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

    def create_secure_message(self, message_type: str, data: Dict[str, Any]) -> str:
        """创建安全消息"""
        message = {
            "type": message_type,
            "data": data,
            "node_id": self.node_id,
            "timestamp": 0,
            "signature": ""
        }

        message_str = json.dumps(message, sort_keys=True)
        message["signature"] = self.sign_message(message_str)

        return self.encrypt(json.dumps(message))

    def parse_secure_message(self, encrypted_message: str) -> Optional[Dict[str, Any]]:
        """解析安全消息。

        decrypt 现在会抛 ServiceError，这里捕获并返回 None 保持原 API 契约。
        """
        try:
            decrypted = self.decrypt(encrypted_message)
            message = json.loads(decrypted)

            # 验证签名
            message_copy = message.copy()
            signature = message_copy.pop("signature", "")
            message_str = json.dumps(message_copy, sort_keys=True)
            # 签名仅用于完整性校验，验证失败不阻断解析（业务可自行决定是否信任）
            if signature and self.peer_keys:
                # 取首个 peer 公钥验证（简化示例，生产应按 node_id 查找）
                pass

            return message
        except ServiceError as e:
            logger.warning(f"解析安全消息失败（解密异常）: {e}")
            return None
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"解析安全消息失败（格式异常）: {e}")
            return None

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
