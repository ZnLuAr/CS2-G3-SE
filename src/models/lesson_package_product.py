"""私教课包产品存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class LessonPackageProduct:
    """对应 lesson_package_products 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    name: str
    price: Decimal
    lesson_credits: int
    valid_days: int | None
    is_sale_enabled: bool
    created_at: datetime
    updated_at: datetime
