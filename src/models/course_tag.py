"""课程标签存储字段；尚未配置 ORM 映射。"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class CourseTag:
    """对应 course_tags 表的存储字段。"""

    id: int
    course_id: int
    tag: str
    created_at: datetime
