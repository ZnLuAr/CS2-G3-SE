"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.models.contracts import PaymentMethod


@dataclass(frozen=True, kw_only=True)
class Payment:
    """对应 payments 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    membership_id: int
    member_id: int
    amount: Decimal
    method: PaymentMethod
    paid_at: datetime
    operator_id: int
    created_at: datetime
