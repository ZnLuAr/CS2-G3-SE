"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.contracts import CourseKind, SessionStatus


@dataclass(frozen=True, kw_only=True)
class Coach:
    """对应 coaches 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    account_id: int
    name: str
    specialty: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class Course:
    """对应 courses 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    name: str
    kind: CourseKind
    duration_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class Room:
    """对应 rooms 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    name: str
    capacity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class CourseSession:
    """对应 course_sessions 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    course_id: int
    course_name: str  # 排课时的课程名称快照
    kind: CourseKind  # 排课时的类型快照
    coach_id: int
    room_id: int
    starts_at: datetime
    ends_at: datetime
    capacity: int
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
