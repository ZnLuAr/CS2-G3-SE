"""站内通知存储字段；尚未配置 ORM 映射。"""

from dataclasses import dataclass
from datetime import datetime

from src.models.contracts import NotificationKind


@dataclass(frozen=True, kw_only=True)
class Notification:
    """对应 notifications 表的存储字段。"""

    id: int
    member_id: int
    session_id: int | None
    kind: NotificationKind
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None
