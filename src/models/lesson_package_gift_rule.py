"""私教课包赠卡规则存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class LessonPackageGiftRule:
    """对应 lesson_package_gift_rules 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    trigger_product_id: int
    active_trigger_product_id: int | None
    reward_gym_card_product_id: int
    reward_quantity: int
    activation_policy: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
