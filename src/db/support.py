"""数据访问层共用的小工具：分页校验、时间窗口和 UTC 转换。

数据库表使用不带时区的 DATETIME 保存 UTC 时刻，界面与业务层使用带
`timezone.utc` 的 datetime。所有转换集中在这里，避免每个仓储各写一套。
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.errors.business import InvalidInputError
from src.models.contracts import DateWindow, PageRequest

MAX_PAGE_SIZE = 100


def utc_now() -> datetime:
    """返回当前 UTC 时刻，统一使用 timezone.utc，避免服务器本地时区影响业务。"""
    return datetime.now(timezone.utc)


def to_db_utc(value: datetime) -> datetime:
    """把带时区的时刻转成 UTC 并去掉 tzinfo，供 DATETIME(6) 列保存。

    输入必须是带时区的 datetime；不带时区的输入无法判断门店时区，直接拒绝，
    避免把“本地时间”误当成 UTC 写入数据库。
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidInputError("时间必须带时区")
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def from_db_utc(value: datetime | None) -> datetime | None:
    """把数据库中的 UTC 时刻还原为带 timezone.utc 的 datetime；空值保持 None。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_paging(paging: PageRequest) -> tuple[int, int]:
    """检查页码和每页条数，返回 (page, page_size)。

    页码从 1 开始，每页 1–100 条。越界抛 InvalidInputError，而不是悄悄改成默认值，
    这样界面能提示用户，分页总数也不会与显示不一致。
    """
    if paging.page < 1:
        raise InvalidInputError("页码必须从 1 开始")
    if paging.page_size < 1 or paging.page_size > MAX_PAGE_SIZE:
        raise InvalidInputError(f"每页条数必须在 1–{MAX_PAGE_SIZE} 之间")
    return paging.page, paging.page_size


def window_bounds(window: DateWindow) -> tuple[datetime, datetime]:
    """把查询窗口转换成数据库使用的 UTC 无时区边界，并检查先后顺序。

    窗口约定为 [start, end)：开始包含、结束不包含。
    """
    if window.end <= window.start:
        raise InvalidInputError("时间范围的结束必须晚于开始")
    return to_db_utc(window.start), to_db_utc(window.end)


def escape_like(keyword: str) -> str:
    """转义 LIKE 通配符，让用户输入的 % 和 _ 按普通字符匹配。"""
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
