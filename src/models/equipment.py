"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.contracts import EquipmentStatus


@dataclass(frozen=True, kw_only=True)
class Equipment:
    """对应 equipment 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    asset_code: str
    name: str
    location: str
    status: EquipmentStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class MaintenanceRecord:
    """对应 maintenance_records 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    equipment_id: int
    description: str
    reported_at: datetime
    resolved_at: datetime | None
    operator_id: int
    resolved_by: int | None
    created_at: datetime
