"""课程模板与课次服务；事务由 CourseLogic 管理。"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from src.db.course_repo import (
    CoachRepository, CourseRepository, RoomRepository, SessionRepository,
)
from src.db.booking_repo import BookingRepository
from src.db.operation_repo import OperationRepository
from src.db.support import payload_hash, utc_now
from src.errors.business import (
    ConflictError, InvalidInputError, InvalidState, NotFoundError,
    PermissionDenied, ScheduleConflict,
)
from src.models.contracts import (
    Actor, CourseInput, CourseView, DateWindow, NamedQuery, Page, SessionInput,
    SessionQuery, SessionView,
)
from src.services.auth_service import AuthService
from src.services.course_booking_rules import (
    aware, ensure_replay, int_range, positive_id, request_uuid, require_admin,
    text_field,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _course_input(data: CourseInput) -> CourseInput:
    if not isinstance(data, CourseInput):
        raise InvalidInputError("课程输入格式不正确")
    if data.kind != "private":
        raise InvalidInputError("当前只支持私教课（private）")
    return CourseInput(
        name=text_field(data.name, "课程名称", minimum=1, maximum=100),
        description=text_field(data.description, "课程说明", minimum=1, maximum=1000, optional=True),
        kind="private",
        duration_minutes=int_range(data.duration_minutes, "默认时长", minimum=1, maximum=150),
    )


class CourseService:
    """课程模板与课次服务；actor 来自可信登录会话。"""

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def create_course(self, session: Session, actor: Actor, data: CourseInput) -> CourseView:
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        return CourseRepository(session).create(_course_input(data))

    def update_course(self, session: Session, actor: Actor, course_id: int, data: CourseInput) -> CourseView:
        positive_id(course_id, "课程编号")
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        repo = CourseRepository(session)
        if repo.lock(course_id) is None:
            raise NotFoundError("课程模板不存在")
        return repo.update(course_id, _course_input(data))

    def get_course(self, session: Session, actor: Actor, course_id: int) -> CourseView:
        positive_id(course_id, "课程编号")
        current = self._auth.verify_actor(session, actor)
        view = CourseRepository(session).get(course_id)
        if view is None or (current.role != "admin" and not view.is_active):
            raise NotFoundError("课程模板不存在或不可见")
        return view

    def list_courses(self, session: Session, actor: Actor, query: NamedQuery) -> Page[CourseView]:
        if not isinstance(query, NamedQuery):
            raise InvalidInputError("课程查询格式不正确")
        current = self._auth.verify_actor(session, actor)
        if current.role != "admin":
            query = replace(query, is_active=True)
        return CourseRepository(session).list(query)

    def set_course_active(self, session: Session, actor: Actor, course_id: int, is_active: bool) -> CourseView:
        positive_id(course_id, "课程编号")
        if not isinstance(is_active, bool):
            raise InvalidInputError("启用状态必须是布尔值")
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        repo = CourseRepository(session)
        if repo.lock(course_id) is None:
            raise NotFoundError("课程模板不存在")
        view = repo.get(course_id)
        if view is None:
            raise NotFoundError("课程模板不存在")
        if view.is_active == is_active:
            return view
        return repo.set_active(course_id, is_active)

    def create_session(self, session: Session, actor: Actor, data: SessionInput, request_id: str) -> SessionView:
        request_id = request_uuid(request_id)
        if not isinstance(data, SessionInput):
            raise InvalidInputError("排课输入格式不正确")
        starts_at = aware(data.starts_at, "开始时间")
        ends_at = aware(data.ends_at, "结束时间")
        positive_id(data.course_id, "课程编号")
        positive_id(data.coach_id, "教练编号")
        positive_id(data.room_id, "场地编号")
        payload = payload_hash({
            "course_id": data.course_id, "coach_id": data.coach_id,
            "room_id": data.room_id, "starts_at": starts_at, "ends_at": ends_at,
        })
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        operations = OperationRepository(session)
        existing = operations.get_by_request(request_id)
        if existing is not None:
            ensure_replay(existing, actor_id=current.account_id, operation="create_session", payload=payload)
            view = SessionRepository(session).get(existing.result_id)
            if view is None:
                raise ConflictError("原排课记录不存在")
            return view

        # 锁顺序：教练 → 课程模板 → 场地。
        coach = CoachRepository(session).lock(data.coach_id)
        if coach is None:
            raise NotFoundError("教练不存在")
        if not coach.is_active:
            raise InvalidState("教练已停用")
        course = CourseRepository(session).lock(data.course_id)
        if course is None:
            raise NotFoundError("课程模板不存在")
        if not course.is_active:
            raise InvalidState("课程模板已归档")
        room = RoomRepository(session).lock(data.room_id)
        if room is None:
            raise NotFoundError("场地不存在")
        if not room.is_active:
            raise InvalidState("场地已停用")

        if starts_at <= utc_now():
            raise InvalidState("开始时间必须晚于当前时刻")
        if ends_at <= starts_at:
            raise InvalidInputError("结束时间必须晚于开始时间")
        seconds = (ends_at - starts_at).total_seconds()
        if seconds != course.duration_minutes * 60:
            raise InvalidInputError("课次时长必须等于课程模板时长")
        if seconds > 150 * 60:
            raise InvalidInputError("单节课最长 150 分钟")
        if SessionRepository(session).has_conflict(
            coach_id=data.coach_id, room_id=data.room_id,
            window=DateWindow(start=starts_at, end=ends_at),
        ):
            raise ScheduleConflict("教练或场地在该时段已有课次")
        view = SessionRepository(session).create(
            replace(data, starts_at=starts_at, ends_at=ends_at),
            course_name=course.name, kind=course.kind,
        )
        operations.create(
            request_id=request_id, actor_id=current.account_id,
            operation="create_session", payload_hash=payload, result_id=view.id,
        )
        return view

    def get_session(self, session: Session, actor: Actor, session_id: int) -> SessionView:
        positive_id(session_id, "课次编号")
        current = self._auth.verify_actor(session, actor)
        view = SessionRepository(session).get(session_id)
        if view is None:
            raise NotFoundError("课次不存在")
        if current.role == "coach":
            if current.coach_id is None or view.coach.id != current.coach_id:
                raise NotFoundError("课次不存在")
        elif current.role == "member":
            if view.status != "scheduled" or view.starts_at <= utc_now():
                raise NotFoundError("课次不存在或不可浏览")
        return view

    def list_sessions(self, session: Session, actor: Actor, query: SessionQuery) -> Page[SessionView]:
        if not isinstance(query, SessionQuery):
            raise InvalidInputError("课表查询格式不正确")
        if query.kind is not None and query.kind != "private":
            raise InvalidInputError("当前只支持私教课（private）")
        if query.status is not None and query.status not in ("scheduled", "completed", "cancelled"):
            raise InvalidInputError("课次状态不合法")
        current = self._auth.verify_actor(session, actor)
        scope_coach_id = None
        bookable_after = None
        if current.role == "coach":
            if current.coach_id is None:
                raise PermissionDenied("当前账号未关联教练档案")
            if query.coach_id is not None and query.coach_id != current.coach_id:
                raise PermissionDenied("教练只能查看自己的课表")
            scope_coach_id = current.coach_id
        elif current.role == "member":
            bookable_after = utc_now()
        return SessionRepository(session).list(
            query, scope_coach_id=scope_coach_id, bookable_after=bookable_after,
        )

    def get_session_by_request(self, session: Session, actor: Actor, request_id: str) -> SessionView:
        request_id = request_uuid(request_id)
        current = self._auth.verify_actor(session, actor)
        record = OperationRepository(session).get_by_request(request_id)
        if record is None:
            raise NotFoundError("没有该请求编号的记录")
        if record.actor_id != current.account_id and current.role != "admin":
            raise NotFoundError("没有该请求编号的记录")
        if record.operation not in ("create_session", "cancel_session"):
            raise ConflictError("该请求编号属于其他操作")
        view = SessionRepository(session).get(record.result_id)
        if view is None:
            raise NotFoundError("课次不存在")
        if current.role == "coach" and (current.coach_id is None or view.coach.id != current.coach_id):
            raise NotFoundError("课次不存在")
        return view

    def complete_session(self, session: Session, actor: Actor, session_id: int) -> SessionView:
        positive_id(session_id, "课次编号")
        current = self._auth.verify_actor(session, actor)
        repo = SessionRepository(session)
        course_session = repo.lock(session_id)
        if course_session is None:
            raise NotFoundError("课次不存在")
        if current.role != "admin" and not (
            current.role == "coach" and current.coach_id == course_session.coach_id
        ):
            raise PermissionDenied("只有管理员或本课教练可以完成课次")
        if course_session.status == "completed":
            view = repo.get(session_id)
            if view is None:
                raise NotFoundError("课次不存在")
            return view
        if course_session.status == "cancelled":
            raise InvalidState("已取消的课次不能完成")
        if course_session.ends_at > utc_now():
            raise InvalidState("课次尚未结束")
        if BookingRepository(session).has_open_for_session(session_id):
            raise InvalidState("仍有待处理预约")
        return repo.set_status(session_id, "completed")

    def cancel_session(self, session: Session, actor: Actor, session_id: int, request_id: str) -> SessionView:
        request_id = request_uuid(request_id)
        positive_id(session_id, "课次编号")
        payload = payload_hash({"session_id": session_id})
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        operations = OperationRepository(session)
        existing = operations.get_by_request(request_id)
        if existing is not None:
            ensure_replay(existing, actor_id=current.account_id, operation="cancel_session", payload=payload)
            view = SessionRepository(session).get(existing.result_id)
            if view is None:
                raise ConflictError("原取消记录不存在")
            return view
        repo = SessionRepository(session)
        course_session = repo.lock(session_id)
        if course_session is None:
            raise NotFoundError("课次不存在")
        if course_session.status == "cancelled":
            raise InvalidState("课次已取消")
        if course_session.status == "completed":
            raise InvalidState("已完成的课次不能取消")
        if course_session.starts_at <= utc_now():
            raise InvalidState("课次已开始，不能取消")
        view = repo.set_status(session_id, "cancelled")
        operations.create(
            request_id=request_id, actor_id=current.account_id,
            operation="cancel_session", payload_hash=payload, result_id=view.id,
        )
        return view
