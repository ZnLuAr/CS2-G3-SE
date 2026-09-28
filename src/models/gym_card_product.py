"""健身房卡产品存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class GymCardProduct:
    """对应 gym_card_products 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    kind: str
    name: str
    price: Decimal
    is_sale_enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class DurationGymCardProduct:
    """对应 duration_gym_card_products 表的存储字段；尚未配置 ORM 映射。"""

    product_id: int
    kind: str
    valid_days: int
    start_policy: str
    is_gift_enabled: bool


@dataclass(frozen=True, kw_only=True)
class VisitGymCardProduct:
    """对应 visit_gym_card_products 表的存储字段；尚未配置 ORM 映射。"""

    product_id: int
    kind: str
    total_entries: int
