"""私教课包存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.models.contracts import LessonPackageStatus


@dataclass(frozen=True, kw_only=True)
class LessonPackage:
    """对应 lesson_packages 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    member_id: int
    product_id: int
    purchase_sale_item_id: int
    name: str
    total_lessons: int
    remaining_lessons: int
    reserved_lessons: int
    available_lessons: int | None
    valid_from: date
    valid_until: date | None
    status: LessonPackageStatus
    created_at: datetime
    updated_at: datetime
