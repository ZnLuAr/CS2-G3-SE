"""课程模板与课次服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

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
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md 的返回、异常、权限和事务约定。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    # ========== 课程模板 ==========
    def create_course(self, session: Session, actor: Actor, data: CourseInput) -> CourseView:
        """管理员输入完整课程名称、可空说明、private 类型与 1～150 分钟时长，创建后返回 CourseView。字段非法抛 InvalidInputError，写入由 Logic 统一提交。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.create_course 尚未实现")

    def update_course(self, session: Session, actor: Actor, course_id: int, data: CourseInput) -> CourseView:
        """管理员输入模板编号与完整条款，锁内更新后返回 CourseView。已发课次保留名称、类型、时长快照；字段非法或不存在抛项目异常。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.update_course 尚未实现")

    def get_course(self, session: Session, actor: Actor, course_id: int) -> CourseView:
        """输入模板编号，返回 CourseView。管理员可查全部，允许浏览课次的其他角色限启用模板；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.get_course 尚未实现")

    def list_courses(self, session: Session, actor: Actor, query: NamedQuery) -> Page[CourseView]:
        """输入名称、启用与分页条件，返回 Page[CourseView]。管理员可查全部，其他允许角色限启用模板；非法条件抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.list_courses 尚未实现")

    def set_course_active(self, session: Session, actor: Actor, course_id: int, is_active: bool) -> CourseView:
        """管理员输入模板编号与布尔状态，锁内更新后返回 CourseView。重复目标状态复用当前结果，启用状态控制后续排课；不存在或字段非法抛项目异常。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.set_course_active 尚未实现")

    # ========== 课次 ==========
    def create_session(self, session: Session, actor: Actor, data: SessionInput, request_id: str) -> SessionView:
        """管理员输入模板、教练、场地、带时区起止时间与 UUID 请求编号，返回 SessionView。按全局顺序锁资源，复核时长、启用和撞期，创建固定容量 1 的课次与操作记录；重复请求复用原结果，输入、时段或状态冲突抛项目异常。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.create_session 尚未实现")

    def get_session(self, session: Session, actor: Actor, session_id: int) -> SessionView:
        """输入课次编号，返回 SessionView。会员限未开课 scheduled 课次，教练限本人，前台和管理员可查全部；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.get_session 尚未实现")

    def list_sessions(self, session: Session, actor: Actor, query: SessionQuery) -> Page[SessionView]:
        """输入日期窗口、教练、场地、类型、状态与分页条件，按 starts_at ASC, id ASC 返回 Page[SessionView]。SQL 计数和当前页先应用角色范围，余位按开放预约计算；非法条件抛 InvalidInputError。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.list_sessions 尚未实现")

    def get_session_by_request(self, session: Session, actor: Actor, request_id: str) -> SessionView:
        """输入创建或取消课次的原请求编号，按原操作者范围返回当前 SessionView。不存在或不可见抛 NotFoundError，类型不匹配抛 ConflictError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.get_session_by_request 尚未实现")

    def complete_session(self, session: Session, actor: Actor, session_id: int) -> SessionView:
        """本课教练或管理员输入课次编号，锁内确认已结束且开放预约全部结算，返回 completed 的 SessionView。已完成时返回当前结果，边界或状态不符抛 InvalidState；更新课次状态由 Logic 提交。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.complete_session 尚未实现")

    def cancel_session(self, session: Session, actor: Actor, session_id: int, request_id: str) -> SessionView:
        """管理员输入课次编号与 UUID 请求编号，返回 cancelled 的 SessionView。本方法维护课程状态和操作记录；ReservationLogic 统筹同事务内的预约占用释放、候补关闭与通知。已开课、已完成或重复新请求取消抛 InvalidState，候选持续变化抛 ConflictError。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CourseService.cancel_session 尚未实现")
