"""销售项目存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.models.contracts import SaleItemKind


@dataclass(frozen=True, kw_only=True)
class SaleItem:
    """对应 sale_items 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    sale_order_id: int
    member_id: int
    kind: SaleItemKind
    product_name: str
    quantity: int
    unit_price: Decimal
    line_amount: Decimal


@dataclass(frozen=True, kw_only=True)
class GymCardSaleItem:
    """对应 gym_card_sale_items 表的存储字段；尚未配置 ORM 映射。"""

    sale_item_id: int
    member_id: int
    kind: str
    gym_card_product_id: int


@dataclass(frozen=True, kw_only=True)
class LessonPackageSaleItem:
    """对应 lesson_package_sale_items 表的存储字段；尚未配置 ORM 映射。"""

    sale_item_id: int
    member_id: int
    kind: str
    lesson_package_product_id: int
