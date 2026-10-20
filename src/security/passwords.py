"""密码格式校验、哈希和验证。"""

from __future__ import annotations

import re

from src.errors.business import InvalidInputError, ResourceError
from src.errors.storage import StorageError


PASSWORD_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,32}$")


def hash_password(password: str) -> str:
    """校验原始密码并使用 Argon2 生成带随机盐的哈希。"""
    if not isinstance(password, str) or PASSWORD_PATTERN.fullmatch(password) is None:
        raise InvalidInputError("密码必须为 6-32 位字母、数字、下划线或短横线")
    try:
        from argon2 import PasswordHasher
    except ImportError as exc:
        raise ResourceError("密码哈希工具不可用") from exc
    return PasswordHasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """核对原始密码；输入格式不合法或不匹配时返回 False。"""
    if not isinstance(password, str) or PASSWORD_PATTERN.fullmatch(password) is None:
        return False
    try:
        from argon2 import PasswordHasher
        from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
    except ImportError as exc:
        raise ResourceError("密码哈希工具不可用") from exc
    try:
        return PasswordHasher().verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except (InvalidHashError, VerificationError) as exc:
        raise StorageError("账号密码数据损坏") from exc
