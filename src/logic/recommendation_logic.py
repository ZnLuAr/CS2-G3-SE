"""RecommendationLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

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
    from src.services.recommendation_service import RecommendationService


class RecommendationLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        recommendation_service: RecommendationService,
        snapshots: RecommendationSnapshotStore,
    ) -> None:
        self._session_factory = session_factory
        self._recommendation_service = recommendation_service
        self._snapshots = snapshots

    def add_course_tag(self, actor: Actor, data: CourseTagInput) -> CourseTagView:
        raise NotImplementedError

    def remove_course_tag(self, actor: Actor, course_id: int, tag: str) -> CourseTagRemovalView:
        raise NotImplementedError

    def list_course_tags(self, actor: Actor, course_id: int, paging: PageRequest) -> Page[CourseTagView]:
        raise NotImplementedError

    def recommend_courses(self, actor: Actor, query: RecommendationQuery) -> Page[RecommendedCourseView]:
        raise NotImplementedError

    def refresh_snapshot(self) -> None:
        """系统入口：消费刷新请求或检查10分钟期限，再读取独立一致性快照。

        关闭读取 Session 后纯计算并一次替换共享快照；失败保留旧快照、再次申请刷新，
        传播 StorageError/ResourceError。用户请求只读完整快照。当前业务编排仅占位。
        """
        raise NotImplementedError
