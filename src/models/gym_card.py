"""健身房卡存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.models.contracts import GymCardStatus


@dataclass(frozen=True, kw_only=True)
class GymCard:
    """对应 gym_cards 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    member_id: int
    product_id: int
    kind: str
    purchase_sale_item_id: int | None
    gift_grant_id: int | None
    name: str
    status: GymCardStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class DurationGymCard:
    """对应 duration_gym_cards 表的存储字段；尚未配置 ORM 映射。"""

    gym_card_id: int
    member_id: int
    kind: str
    valid_days: int
    start_policy: str
    valid_from: date
    valid_until: date


@dataclass(frozen=True, kw_only=True)
class VisitGymCard:
    """对应 visit_gym_cards 表的存储字段；尚未配置 ORM 映射。"""

    gym_card_id: int
    member_id: int
    kind: str
    total_entries: int
    remaining_entries: int
