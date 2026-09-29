"""销售订单存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.models.contracts import SaleKind


@dataclass(frozen=True, kw_only=True)
class SaleOrder:
    """对应 sale_orders 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    member_id: int
    kind: SaleKind
    total_amount: Decimal
    sold_at: datetime
    operator_id: int
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class SaleOrderAggregate:
    """销售订单聚合，包含订单及其关联的销售项目、付款等信息。"""

    order: SaleOrder
    # 其他关联数据字段待补充
