"""推荐数据读取与课程标签仓储；SQL 方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import (
    BookingStatus, CourseTagInput, CourseTagView, CourseView, Page, PageRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class RecommendationRepository:
    """同一读取Session取得快照输入；参数绑定，存储故障抛StorageError。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_courses(self) -> tuple[CourseView, ...]:
        """按id读取课程模板供快照构建，不修改数据。"""
        raise NotImplementedError

    def list_behaviors(self, as_of: datetime) -> tuple[tuple[int, int, BookingStatus], ...]:
        """读取会员id、课程id、预约状态元组；权重与去重由推荐服务处理。"""
        raise NotImplementedError

    def list_tags(self) -> tuple[CourseTagView, ...]:
        """读取构建快照所需全部标签，按course_id/tag排序。"""
        raise NotImplementedError

    def list_course_tags(self, course_id: int, paging: PageRequest) -> Page[CourseTagView]:
        """按tag升序分页读取指定课程标签，空结果为空Page。"""
        raise NotImplementedError

    def add_tag(self, data: CourseTagInput) -> CourseTagView:
        """保存已校验标签，重复抛ConflictError；调用方提交。"""
        raise NotImplementedError

    def remove_tag(self, course_id: int, tag: str) -> bool:
        """删除目标标签并返回是否实际删除，由服务转换为RemovalView。"""
        raise NotImplementedError
