"""赠送记录存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.contracts import GiftActivationPolicy
from src.models.gym_card import GymCardAggregate


@dataclass(frozen=True, kw_only=True)
class GiftGrant:
    """对应 gift_grants 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    trigger_sale_item_id: int
    trigger_product_id: int
    gift_rule_id: int
    member_id: int
    reward_gym_card_product_id: int
    gift_rule_version: int
    activation_policy: GiftActivationPolicy
    reward_product_name: str
    reward_valid_days: int
    sequence: int
    granted_at: datetime
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class GiftGrantAggregate:
    """赠送记录聚合，包含赠送记录及关联的健身房卡信息。"""

    grant: GiftGrant
    gym_card: GymCardAggregate
