"""账号与档案关联存储模型。当前仅声明字段，尚未配置 ORM 映射。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class MemberAccountLink:
    """对应 member_account_links 表的存储字段；尚未配置 ORM 映射。"""

    account_id: int
    member_id: int
    linked_at: datetime
    linked_by: int


@dataclass(frozen=True, kw_only=True)
class CoachAccountLink:
    """对应 coach_account_links 表的存储字段；尚未配置 ORM 映射。"""

    account_id: int
    coach_id: int
    linked_at: datetime
    linked_by: int
