"""课程模板与课次服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import (
    Actor,
    CourseInput,
    CourseView,
    NamedQuery,
    Page,
    SessionInput,
    SessionQuery,
    SessionView,
)
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CourseService:
    """课程模板与课次服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture.md 的返回、异常、权限和事务约定。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    # ========== 课程模板 ==========
    def create_course(self, actor: Actor, data: CourseInput) -> CourseView:
        """创建课程模板。"""
        raise NotImplementedError("CourseService.create_course 尚未实现")

    def update_course(self, actor: Actor, course_id: int, data: CourseInput) -> CourseView:
        """修改课程模板。"""
        raise NotImplementedError("CourseService.update_course 尚未实现")

    def get_course(self, actor: Actor, course_id: int) -> CourseView:
        """查询课程详情。"""
        raise NotImplementedError("CourseService.get_course 尚未实现")

    def list_courses(self, actor: Actor, query: NamedQuery) -> Page[CourseView]:
        """分页查询课程。"""
        raise NotImplementedError("CourseService.list_courses 尚未实现")

    def set_course_active(self, actor: Actor, course_id: int, is_active: bool) -> CourseView:
        """停用或恢复课程模板。"""
        raise NotImplementedError("CourseService.set_course_active 尚未实现")

    # ========== 课次 ==========
    def create_session(self, actor: Actor, data: SessionInput, request_id: str) -> SessionView:
        """创建课次（幂等）。"""
        raise NotImplementedError("CourseService.create_session 尚未实现")

    def get_session(self, actor: Actor, session_id: int) -> SessionView:
        """查询课次详情。"""
        raise NotImplementedError("CourseService.get_session 尚未实现")

    def list_sessions(self, actor: Actor, query: SessionQuery) -> Page[SessionView]:
        """分页查询课次。"""
        raise NotImplementedError("CourseService.list_sessions 尚未实现")

    def get_session_by_request(self, actor: Actor, request_id: str) -> SessionView:
        """按幂等请求编号查课次。"""
        raise NotImplementedError("CourseService.get_session_by_request 尚未实现")

    def complete_session(self, actor: Actor, session_id: int) -> SessionView:
        """标记课次为已完成。"""
        raise NotImplementedError("CourseService.complete_session 尚未实现")

    def cancel_session(self, actor: Actor, session_id: int, request_id: str) -> SessionView:
        """取消课次（幂等）。"""
        raise NotImplementedError("CourseService.cancel_session 尚未实现")
