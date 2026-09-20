"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class Member:
    """对应 members 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    account_id: int | None
    name: str
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
