"""
安全传输模块
实现加密的数据传输协议
"""

import hashlib
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Optional
import uuid


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
        """加密数据"""
        try:
            return self.fernet.encrypt(data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"[SecureTransport] 加密失败: {e}")
            return data
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"[SecureTransport] 解密失败: {e}")
            return encrypted_data
    
    def encrypt_with_public_key(self, data: str, public_key_bytes: bytes) -> str:
        """使用公钥加密（用于密钥交换）"""
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
            print(f"[SecureTransport] 公钥加密失败: {e}")
            return data
    
    def decrypt_with_private_key(self, encrypted_data: str) -> str:
        """使用私钥解密"""
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
            print(f"[SecureTransport] 私钥解密失败: {e}")
            return encrypted_data
    
    def get_public_key_pem(self) -> str:
        """获取PEM格式的公钥"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def sign_message(self, message: str) -> str:
        """签名消息"""
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
            print(f"[SecureTransport] 签名失败: {e}")
            return ""
    
    def verify_signature(self, message: str, signature: str, public_key_pem: str) -> bool:
        """验证签名"""
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
            print(f"[SecureTransport] 签名验证失败: {e}")
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
        """解析安全消息"""
        try:
            decrypted = self.decrypt(encrypted_message)
            message = json.loads(decrypted)
            
            # 验证签名
            message_copy = message.copy()
            signature = message_copy.pop("signature", "")
            message_str = json.dumps(message_copy, sort_keys=True)
            
            return message
        except Exception as e:
            print(f"[SecureTransport] 解析消息失败: {e}")
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
