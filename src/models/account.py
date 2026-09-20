"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.models.contracts import Role


@dataclass(frozen=True, kw_only=True)
class Account:
    """对应 accounts 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    username: str
    password_hash: str = field(repr=False)
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime
