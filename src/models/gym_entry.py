"""健身房入场存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.models.contracts import EntrySourceKind


@dataclass(frozen=True, kw_only=True)
class GymEntry:
    """对应 gym_entries 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    member_id: int
    source_kind: EntrySourceKind
    duration_gym_card_id: int | None
    visit_gym_card_id: int | None
    booking_id: int | None
    business_date: date
    entered_at: datetime
    operator_id: int


@dataclass(frozen=True, kw_only=True)
class EntryAggregate:
    """入场记录聚合，包含入场记录及关联数据。"""

    entry: GymEntry
    # 其他关联数据字段待补充
