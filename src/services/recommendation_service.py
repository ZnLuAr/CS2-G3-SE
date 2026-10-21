"""Course-tag and recommendation service contract."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.recommendation import RecommendationSource
from src.services.recommendation_snapshot import RecommendationSnapshotStore

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        CourseTagInput,
        CourseTagRemovalView,
        CourseTagView,
        Page,
        PageRequest,
        RecommendationQuery,
        RecommendedCourseView,
    )
    from src.services.auth_service import AuthService


class RecommendationService:
    """标签与推荐领域接口；共用身份服务和进程内快照，业务操作尚未实现。"""
    def __init__(self, auth_service: AuthService, snapshots: RecommendationSnapshotStore) -> None:
        self._auth_service = auth_service
        self._snapshots = snapshots

    def load_snapshot_source(
        self, session: Session, as_of: datetime,
    ) -> RecommendationSource:
        """系统用例在同一 Session/as_of 下读取课程、行为和标签，不写数据。

        返回不可变 RecommendationSource，SQL 失败抛 StorageError；当前仅占位。
        计算与发布由 RecommendationLogic 在读取会话关闭后执行。
        """
        raise NotImplementedError("推荐快照输入读取尚未实现")

    def add_course_tag(
        self, session: Session, actor: Actor, data: CourseTagInput,
    ) -> CourseTagView:
        """管理员校验并新增课程标签，返回View；重复抛ConflictError，Logic提交后申请刷新。"""
        raise NotImplementedError

    def remove_course_tag(
        self, session: Session, actor: Actor, course_id: int, tag: str,
    ) -> CourseTagRemovalView:
        """管理员移除指定课程标签，返回是否删除的View；不存在课程抛NotFoundError。"""
        raise NotImplementedError

    def list_course_tags(
        self, session: Session, actor: Actor, course_id: int, paging: PageRequest,
    ) -> Page[CourseTagView]:
        """在角色可见课程范围内分页读取标签，返回固定Page，不写数据。"""
        raise NotImplementedError

    def recommend_courses(
        self, session: Session, actor: Actor, query: RecommendationQuery,
    ) -> Page[RecommendedCourseView]:
        """会员查本人、前台管理员查目标会员，top_n为1至20，返回推荐Page。

        使用完整只读快照并以当前Session过滤课程与课次；角色拒绝抛PermissionDenied，
        目标不可见抛NotFoundError，快照不可用降级空Page并记录错误。当前仅占位。
        """
        raise NotImplementedError
