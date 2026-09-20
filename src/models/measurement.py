"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, kw_only=True)
class BodyMeasurement:
    """对应 body_measurements 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    member_id: int
    coach_id: int
    measured_at: datetime
    height_cm: Decimal  # 100.00–250.00 cm
    weight_kg: Decimal  # 30.00–150.00 kg
    body_fat_pct: Decimal | None
    created_at: datetime
