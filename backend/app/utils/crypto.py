"""
加密工具
- 敏感数据加密（如 RTSP 密码）
"""
import base64
from cryptography.fernet import Fernet

# TODO: Implement encryption functions
# - encrypt: 加密字符串
# - decrypt: 解密字符串
# - generate_key: 生成加密密钥

# 临时实现（生产环境需要使用环境变量中的密钥）
def get_cipher():
    """获取加密器（需要从配置中读取密钥）"""
    # 这里应该从环境变量或配置文件中读取密钥
    # 临时使用固定密钥，生产环境必须更换！
    key = b'your-32-byte-key-here-change-it!'  # 需要32字节
    # Fernet 需要 URL-safe base64 编码的 32 字节密钥
    return None  # TODO: 实现真正的加密


def encrypt_password(plain_text: str) -> str:
    """加密密码"""
    # TODO: 实现真正的加密
    return base64.b64encode(plain_text.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """解密密码"""
    # TODO: 实现真正的解密
    return base64.b64decode(encrypted.encode()).decode()
