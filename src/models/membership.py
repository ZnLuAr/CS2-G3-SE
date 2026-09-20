"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.models.contracts import CardKind, CardStatus


@dataclass(frozen=True, kw_only=True)
class CardProduct:
    """对应 card_products 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    name: str
    kind: CardKind
    price: Decimal
    private_lesson_credits: int
    access_uses: int | None
    valid_days: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class Membership:
    """对应 memberships 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    member_id: int
    product_id: int
    name: str
    kind: CardKind
    price: Decimal
    private_lesson_credits: int
    access_uses: int | None
    valid_days: int | None
    valid_from: date
    valid_until: date | None
    remaining_accesses: int | None
    remaining_private_lessons: int
    reserved_private_lessons: int
    status: CardStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class GymEntry:
    """对应 gym_entries 表的存储字段；同一会员每个门店日期最多一条。"""

    id: int
    member_id: int
    membership_id: int
    business_date: date
    entered_at: datetime
    accesses_used: int
    operator_id: int
