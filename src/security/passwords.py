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


_DUMMY_HASH: str | None = None


def prepare_dummy_hash() -> None:
    """在接收登录请求前生成一次占位哈希，供账号不存在的分支做等时校验。

    必须在请求路径之外调用（AuthService 构造时）：若留到请求内惰性生成，
    进程内第一个账号不存在的请求会比其他请求多一次哈希运算，时间仍可区分。
    只保证单线程装配阶段调用；并发调用至多重复生成，各线程拿到的哈希都可用，不影响正确性。
    哈希工具不可用抛 ResourceError；占位密码是常量，格式校验失败属编程错误。
    """
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("dummy-password-for-timing")


def verify_against_dummy(password: str) -> None:
    """对格式合法的密码执行一次与真实校验同参数的 Argon2 运算，结果丢弃。

    供登录时账号不存在的分支调用，使两条分支的响应时间一致，避免通过耗时判断账号是否存在。
    依赖 prepare_dummy_hash 已调用；未调用时抛 ResourceError，不在请求内惰性生成。
    其余异常与 verify_password 相同。
    """
    if _DUMMY_HASH is None:
        raise ResourceError("密码哈希工具不可用")
    verify_password(password, _DUMMY_HASH)
