"""密码加密与验证

使用 bcrypt 进行密码哈希存储和验证。
"""

import bcrypt


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码字符串
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与哈希值匹配

    Args:
        plain_password: 明文密码
        hashed_password: 已存储的哈希密码

    Returns:
        是否匹配
    """
    pwd_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)
