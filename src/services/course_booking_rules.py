"""课程与预约服务共用的输入校验、权限和防重复工具。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.errors.business import ConflictError, InvalidInputError, PermissionDenied
from src.models.operation import OperationRecord


def require_admin(actor) -> None:
    if actor.role != "admin":
        raise PermissionDenied("只有管理员可以执行该操作")


def positive_id(value: int, label: str = "编号") -> int:
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise InvalidInputError(f"{label}必须是有效的正整数")
    return value


def text_field(value: str | None, label: str, *, minimum: int, maximum: int, optional: bool = False) -> str | None:
    if value is None:
        if optional:
            return None
        raise InvalidInputError(f"{label}不能为空")
    if not isinstance(value, str):
        raise InvalidInputError(f"{label}必须是文字")
    text = value.strip()
    if optional and not text:
        return None
    if len(text) < minimum or len(text) > maximum:
        raise InvalidInputError(f"{label}长度必须在 {minimum}–{maximum} 个字符之间")
    return text


def int_range(value: int, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise InvalidInputError(f"{label}必须在 {minimum}–{maximum} 之间")
    return value


def aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InvalidInputError(f"{label}必须包含时区信息")
    if value.year < 1000:
        raise InvalidInputError(f"{label}超出数据库可用范围")
    return value


def request_uuid(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidInputError("请求编号必须是标准 UUID")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise InvalidInputError("请求编号必须是标准 UUID") from exc
    if str(parsed) != value.lower():
        raise InvalidInputError("请求编号必须是标准 UUID")
    return str(parsed)


def ensure_replay(record: OperationRecord, *, actor_id: int, operation: str, payload: str) -> None:
    if record.actor_id != actor_id or record.operation != operation or record.payload_hash != payload:
        raise ConflictError("请求编号已被其他操作使用，请核实原结果")
