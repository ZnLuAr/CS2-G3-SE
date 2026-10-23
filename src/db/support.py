"""课程与预约仓储共用的 UTC、分页、时间窗和请求摘要工具。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.errors.business import InvalidInputError
from src.models.contracts import DateWindow, PageRequest

MAX_PAGE_SIZE = 100


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_db_utc(value: datetime) -> datetime:
    """带时区的时刻转成 UTC 无时区值，供 DATETIME(6) 列保存。"""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InvalidInputError("时间必须带时区")
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def from_db_utc(value: datetime | str | None) -> datetime | None:
    """数据库 UTC 值还原为带 utc 时区的 datetime。"""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def validate_paging(paging: PageRequest) -> tuple[int, int]:
    if not isinstance(paging, PageRequest):
        raise InvalidInputError("分页参数格式不正确")
    if type(paging.page) is not int or paging.page < 1:
        raise InvalidInputError("页码必须从 1 开始")
    if type(paging.page_size) is not int or not 1 <= paging.page_size <= MAX_PAGE_SIZE:
        raise InvalidInputError(f"每页条数必须在 1–{MAX_PAGE_SIZE} 之间")
    if (paging.page - 1) * paging.page_size > 2**63 - 1:
        raise InvalidInputError("分页位置超出数据库可用范围")
    return paging.page, paging.page_size


def window_bounds(window: DateWindow) -> tuple[datetime, datetime]:
    if not isinstance(window, DateWindow):
        raise InvalidInputError("时间范围格式不正确")
    if window.end <= window.start:
        raise InvalidInputError("时间范围的结束必须晚于开始")
    return to_db_utc(window.start), to_db_utc(window.end)


def validate_request_id(request_id: str) -> str:
    """v3 要求标准 UUID；CHAR(36) 列只接受该格式。"""
    if not isinstance(request_id, str):
        raise InvalidInputError("请求编号必须是文字")
    try:
        value = str(UUID(request_id))
    except (ValueError, AttributeError) as exc:
        raise InvalidInputError("请求编号必须是标准 UUID") from exc
    if value != request_id.lower():
        raise InvalidInputError("请求编号必须是标准 UUID")
    return value


def payload_hash(values: dict[str, Any]) -> str:
    """按 v3 约定生成输入摘要：键排序、紧凑 JSON、UTC ISO、SHA-256。"""
    def canonical(value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise InvalidInputError("时间必须带时区")
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, Decimal):
            return format(value, ".2f")
        if isinstance(value, dict):
            return {str(key): canonical(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [canonical(item) for item in value]
        if value is None or isinstance(value, (str, int, bool, float)):
            return value
        raise InvalidInputError("请求内容包含无法摘要的字段")

    text = json.dumps(canonical(values), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
