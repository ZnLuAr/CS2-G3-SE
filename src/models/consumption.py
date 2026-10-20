"""课节结算存储字段；尚未配置 ORM 映射。"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class ConsumptionRecord:
    """对应 consumption_records 表，预约唯一，保存课包来源和实际结算操作者。"""

    id: int
    booking_id: int
    lesson_package_id: int
    lessons_used: int
    completed_at: datetime
    operator_id: int
