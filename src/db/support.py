"""数据库 UTC 时间与业务时区感知时间之间的转换。"""

from datetime import datetime, timezone


def from_db_utc(value: datetime | str) -> datetime:
    """把数据库返回的 UTC 时刻转换为带时区的 datetime。"""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_db_utc(value: datetime) -> datetime:
    """把带时区的时刻转换为 UTC DATETIME 列的值。"""
    return value.astimezone(timezone.utc).replace(tzinfo=None)
