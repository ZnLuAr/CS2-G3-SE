"""教练、课程模板、场地和课次的业务服务实现。

课程与预约模块由 `CourseService`（教练、模板、场地、排课）和
`BookingService`（预约）配合完成。本文件中的方法都按同一流程执行：

1. 在独立数据库会话中调用 `AuthService.verify_actor` 重验当前身份；
2. 检查角色权限（教练资料、模板、场地、排课的写操作仅管理员）；
3. 校验输入字段，再通过仓储读写；
4. 写操作在同一事务内提交，业务异常回滚后原样抛出，数据库异常转为
   `StorageError`，不把 SQL 细节暴露给界面。

返回类型固定：列表 `Page[T]`，详情 `T`，失败抛异常，不返回字典或 None。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from src.db.booking_repo import (
    BookingRepository,
    active_bookings_for_session,
    lock_memberships,
    release_private_lessons,
)
from src.db.course_repo import (
    CoachRepository,
    CourseRepository,
    RoomRepository,
    SessionRepository,
)
from src.db.operation_repo import OperationRepository
from src.db.support import utc_now
from src.errors.base import GymError
from src.errors.business import (
    ConflictError,
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
    ScheduleConflict,
)
from src.errors.storage import StorageError
from src.models.contracts import (
    Actor,
    CoachInput,
    CoachUpdateInput,
    CoachView,
    CourseInput,
    CourseQuery,
    CourseView,
    DateWindow,
    NamedQuery,
    Page,
    RoomInput,
    RoomView,
    SessionInput,
    SessionQuery,
    SessionView,
)
from src.models.course import Course
from src.services.auth_service import AuthService
from src.services.idempotency import (
    ensure_replay_matches,
    payload_hash,
    validate_request_id,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

T = TypeVar("T")


def _require_admin(actor: Actor) -> None:
    """检查管理员权限；其他角色一律拒绝，而不是只隐藏菜单。"""
    if actor.role != "admin":
        raise PermissionDenied("只有管理员可以执行该操作")


def _text(value: str, label: str, *, minimum: int, maximum: int) -> str:
    """去掉首尾空白后检查长度，返回要保存的文字。

    姓名等字段在数据库用 VARCHAR(100) 保存，这里用 Python 字符数检查，
    与 MySQL 的 CHAR_LENGTH 口径一致。空字符串是否允许由 minimum 决定。
    """
    if not isinstance(value, str):
        raise InvalidInputError(f"{label}必须是文字")
    text = value.strip()
    if len(text) < minimum or len(text) > maximum:
        if minimum == 0:
            raise InvalidInputError(f"{label}不能超过 {maximum} 个字符")
        raise InvalidInputError(f"{label}长度必须在 {minimum}–{maximum} 个字符之间")
    return text


def _integer(value: int, label: str, *, minimum: int, maximum: int) -> int:
    """检查整数范围；显式排除 bool（Python 中 True 也是 int）。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidInputError(f"{label}必须是整数")
    if value < minimum or value > maximum:
        raise InvalidInputError(f"{label}必须在 {minimum}–{maximum} 之间")
    return value


def _read(
    session_factory: Callable[[], Session],
    auth: AuthService,
    actor: Actor,
    operation: Callable[[Session, Actor], T],
) -> T:
    """在只读会话中重验身份后执行查询；不提交事务。"""
    with session_factory() as session:
        current = auth.verify_actor(session, actor)
        return operation(session, current)


def _write(
    session_factory: Callable[[], Session],
    auth: AuthService,
    actor: Actor,
    operation: Callable[[Session, Actor], T],
    *,
    request_id: str | None = None,
) -> T:
    """在一个事务中重验身份、执行写操作并提交。

    业务异常（GymError）回滚后原样抛出；数据库异常回滚后转成 StorageError。
    如果异常发生在提交阶段且调用方提供了请求编号，说明数据库可能已经写入，
    此时抛 OutcomeUnknownError 更准确，不能谎报失败。
    """
    session = session_factory()
    committing = False
    try:
        session.begin()
        current = auth.verify_actor(session, actor)
        result = operation(session, current)
        committing = True
        session.commit()
        return result
    except GymError:
        session.rollback()
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        if committing and request_id is not None:
            from src.errors.storage import OutcomeUnknownError

            raise OutcomeUnknownError(
                "提交结果待核实，请按原请求编号查询，不要直接重试",
                request_id=request_id,
            ) from exc
        raise StorageError("数据库操作失败，请稍后重试") from exc
    finally:
        session.close()


def _coach_input(data: CoachInput) -> CoachInput:
    """校验并规范化教练建档输入。"""
    return replace(
        data,
        name=_text(data.name, "教练姓名", minimum=1, maximum=100),
        specialty=_text(data.specialty, "专长", minimum=0, maximum=200),
    )


def _coach_update_input(data: CoachUpdateInput) -> CoachUpdateInput:
    """校验并规范化教练资料修改输入。"""
    return replace(
        data,
        name=_text(data.name, "教练姓名", minimum=1, maximum=100),
        specialty=_text(data.specialty, "专长", minimum=0, maximum=200),
    )


def _course_input(data: CourseInput) -> CourseInput:
    """校验课程模板输入：名称、固定私教类型和 1–150 整数分钟。"""
    if data.kind != "private":
        raise InvalidInputError("当前只支持私教课（private）")
    return replace(
        data,
        name=_text(data.name, "课程名称", minimum=1, maximum=100),
        duration_minutes=_integer(
            data.duration_minutes, "默认时长", minimum=1, maximum=150,
        ),
    )


def _room_input(data: RoomInput) -> RoomInput:
    """校验场地输入：名称 1–100 字，容量为正整数。"""
    return replace(
        data,
        name=_text(data.name, "场地名称", minimum=1, maximum=100),
        capacity=_integer(data.capacity, "容量", minimum=1, maximum=1000),
    )


def _aware(value: datetime, label: str) -> datetime:
    """要求时间带时区；不带时区无法安全转换成 UTC 和门店日期。"""
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidInputError(f"{label}必须带时区")
    return value


def _session_window(data: SessionInput, course: Course) -> tuple[datetime, datetime]:
    """校验排课时间并返回 (starts_at, ends_at)。

    规则：
    - 私教课容量固定为 1；
    - 开始和结束都带时区，结束必须晚于开始；
    - 起止时间差必须严格等于模板默认时长，多 1 秒也拒绝；
    - 时长仍受 1–150 分钟限制，模板数据异常时也不放行。
    """
    if data.capacity != 1:
        raise InvalidInputError("私教课容量固定为 1")
    starts_at = _aware(data.starts_at, "开始时间")
    ends_at = _aware(data.ends_at, "结束时间")
    if ends_at <= starts_at:
        raise InvalidInputError("结束时间必须晚于开始时间")
    expected_seconds = course.duration_minutes * 60
    actual_seconds = (ends_at - starts_at).total_seconds()
    if actual_seconds != expected_seconds:
        raise InvalidInputError(
            f"课次时长必须等于课程模板的 {course.duration_minutes} 分钟"
        )
    if actual_seconds > 150 * 60:
        raise InvalidInputError("单节课最长 150 分钟")
    if course.kind != "private":
        raise InvalidInputError("当前只支持私教课（private）")
    return starts_at, ends_at


def _session_payload_hash(data: SessionInput) -> str:
    """计算排课请求摘要，用于同一请求编号的重复提交核对。"""
    return payload_hash({
        "course_id": data.course_id,
        "coach_id": data.coach_id,
        "room_id": data.room_id,
        "starts_at": data.starts_at,
        "ends_at": data.ends_at,
        "capacity": data.capacity,
    })


def _ensure_session_visible(actor: Actor, view: SessionView) -> None:
    """检查课次可见范围。

    教练只能查看自己的课次；会员、前台和管理员可以查看课表。会话的
    `SessionView` 不包含其他学员姓名，会员浏览公开课表不会泄露个人信息。
    """
    if actor.role == "coach" and actor.coach_id != view.coach_id:
        raise NotFoundError("课次不存在")


def _session_scope(actor: Actor, query: SessionQuery) -> SessionQuery:
    """按身份收窄课表查询：教练只能查自己的课次。"""
    if actor.role != "coach":
        return query
    if actor.coach_id is None:
        raise PermissionDenied("当前账号未关联教练档案")
    if query.coach_id is not None and query.coach_id != actor.coach_id:
        raise PermissionDenied("教练只能查看自己的课表")
    return replace(query, coach_id=actor.coach_id)


class CourseService:
    """教练、课程和场地服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_coach(self, actor: Actor, data: CoachInput) -> CoachView:
        """创建教练档案。

        权限：管理员。账号必须存在、角色为教练且未绑定其他教练档案。
        返回：CoachView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        validated = _coach_input(data)

        def action(session: Session, current: Actor) -> CoachView:
            _require_admin(current)
            return CoachRepository(session).create(validated)

        return _write(self._session_factory, self._auth, actor, action)

    def update_coach(self, actor: Actor, coach_id: int, data: CoachUpdateInput) -> CoachView:
        """修改教练资料。

        权限：管理员。只修改姓名和专长，不改变账号关联或已排课时间。
        返回：CoachView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        validated = _coach_update_input(data)

        def action(session: Session, current: Actor) -> CoachView:
            _require_admin(current)
            repo = CoachRepository(session)
            if repo.lock(coach_id) is None:
                raise NotFoundError("教练不存在")
            return repo.update(coach_id, validated)

        return _write(self._session_factory, self._auth, actor, action)

    def get_coach(self, actor: Actor, coach_id: int) -> CoachView:
        """查询教练详情。

        返回：CoachView。不修改业务数据；不存在抛 NotFoundError。
        """
        def action(session: Session, current: Actor) -> CoachView:  # noqa: ARG001
            view = CoachRepository(session).get(coach_id)
            if view is None:
                raise NotFoundError("教练不存在")
            return view

        return _read(self._session_factory, self._auth, actor, action)

    def list_coaches(self, actor: Actor, query: NamedQuery) -> Page[CoachView]:
        """分页查询教练。

        返回：Page[CoachView]。不修改业务数据；空结果返回 items 为空的 Page。
        """
        def action(session: Session, current: Actor) -> Page[CoachView]:  # noqa: ARG001
            return CoachRepository(session).list(query)

        return _read(self._session_factory, self._auth, actor, action)

    def set_coach_active(self, actor: Actor, coach_id: int, active: bool) -> CoachView:
        """停用或恢复教练。

        权限：管理员。停用前要求没有未结束课次，历史记录保留。
        返回：CoachView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        def action(session: Session, current: Actor) -> CoachView:
            _require_admin(current)
            repo = CoachRepository(session)
            if repo.lock(coach_id) is None:
                raise NotFoundError("教练不存在")
            return repo.set_active(coach_id, active)

        return _write(self._session_factory, self._auth, actor, action)

    def create_course(self, actor: Actor, data: CourseInput) -> CourseView:
        """创建课程模板。

        仅接受 private 私教类型；duration_minutes 为 1–150 的整数，越界抛 InvalidInputError。
        返回：CourseView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        validated = _course_input(data)

        def action(session: Session, current: Actor) -> CourseView:
            _require_admin(current)
            return CourseRepository(session).create(validated)

        return _write(self._session_factory, self._auth, actor, action)

    def update_course(self, actor: Actor, course_id: int, data: CourseInput) -> CourseView:
        """修改课程模板。

        仅接受 private 类型及 1–150 整数分钟；越界抛 InvalidInputError，不改变已发布课次。
        返回：CourseView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        validated = _course_input(data)

        def action(session: Session, current: Actor) -> CourseView:
            _require_admin(current)
            repo = CourseRepository(session)
            if repo.lock(course_id) is None:
                raise NotFoundError("课程模板不存在")
            return repo.update(course_id, validated)

        return _write(self._session_factory, self._auth, actor, action)

    def get_course(self, actor: Actor, course_id: int) -> CourseView:
        """查询课程模板详情。

        返回：CourseView。不修改业务数据；不存在抛 NotFoundError。
        """
        def action(session: Session, current: Actor) -> CourseView:  # noqa: ARG001
            view = CourseRepository(session).get(course_id)
            if view is None:
                raise NotFoundError("课程模板不存在")
            return view

        return _read(self._session_factory, self._auth, actor, action)

    def list_courses(self, actor: Actor, query: CourseQuery) -> Page[CourseView]:
        """分页查询课程模板。

        返回：Page[CourseView]。不修改业务数据；空结果返回 items 为空的 Page。
        """
        if query.kind is not None and query.kind != "private":
            raise InvalidInputError("当前只支持私教课（private）")

        def action(session: Session, current: Actor) -> Page[CourseView]:  # noqa: ARG001
            return CourseRepository(session).list(query)

        return _read(self._session_factory, self._auth, actor, action)

    def set_course_active(self, actor: Actor, course_id: int, active: bool) -> CourseView:
        """归档或恢复课程模板。

        权限：管理员。归档后不能据此新排课，已有课次及预约仍可查询和处理。
        返回：CourseView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        def action(session: Session, current: Actor) -> CourseView:
            _require_admin(current)
            repo = CourseRepository(session)
            if repo.lock(course_id) is None:
                raise NotFoundError("课程模板不存在")
            return repo.set_active(course_id, active)

        return _write(self._session_factory, self._auth, actor, action)

    def create_room(self, actor: Actor, data: RoomInput) -> RoomView:
        """创建场地。

        权限：管理员。容量必须为正整数，成功后可在排课时选择。
        返回：RoomView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        validated = _room_input(data)

        def action(session: Session, current: Actor) -> RoomView:
            _require_admin(current)
            return RoomRepository(session).create(validated)

        return _write(self._session_factory, self._auth, actor, action)

    def update_room(self, actor: Actor, room_id: int, data: RoomInput) -> RoomView:
        """修改场地资料。

        权限：管理员。缩小容量时不能低于已有课次的占用人数。
        返回：RoomView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        validated = _room_input(data)

        def action(session: Session, current: Actor) -> RoomView:
            _require_admin(current)
            repo = RoomRepository(session)
            if repo.lock(room_id) is None:
                raise NotFoundError("场地不存在")
            return repo.update(room_id, validated)

        return _write(self._session_factory, self._auth, actor, action)

    def get_room(self, actor: Actor, room_id: int) -> RoomView:
        """查询场地详情。

        返回：RoomView。不修改业务数据；不存在抛 NotFoundError。
        """
        def action(session: Session, current: Actor) -> RoomView:  # noqa: ARG001
            view = RoomRepository(session).get(room_id)
            if view is None:
                raise NotFoundError("场地不存在")
            return view

        return _read(self._session_factory, self._auth, actor, action)

    def list_rooms(self, actor: Actor, query: NamedQuery) -> Page[RoomView]:
        """分页查询场地。

        返回：Page[RoomView]。不修改业务数据；空结果返回 items 为空的 Page。
        """
        def action(session: Session, current: Actor) -> Page[RoomView]:  # noqa: ARG001
            return RoomRepository(session).list(query)

        return _read(self._session_factory, self._auth, actor, action)

    def set_room_active(self, actor: Actor, room_id: int, active: bool) -> RoomView:
        """停用或恢复场地。

        权限：管理员。停用前要求没有未结束课次，历史课次保留。
        返回：RoomView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        def action(session: Session, current: Actor) -> RoomView:
            _require_admin(current)
            repo = RoomRepository(session)
            if repo.lock(room_id) is None:
                raise NotFoundError("场地不存在")
            return repo.set_active(room_id, active)

        return _write(self._session_factory, self._auth, actor, action)

    def create_session(self, actor: Actor, data: SessionInput, request_id: str) -> SessionView:
        """创建具体课次。

        起止时间差必须等于模板分钟数，且不超过 150 分钟；容量固定为 1。
        不限定营业时段，允许跨午夜；越界抛 InvalidInputError，教练或场地撞期抛 ScheduleConflict。
        返回：SessionView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        request_id = validate_request_id(request_id)
        payload = _session_payload_hash(data)

        def action(session: Session, current: Actor) -> SessionView:
            _require_admin(current)
            operations = OperationRepository(session)
            existing = operations.get_by_request(request_id)
            if existing is not None:
                ensure_replay_matches(
                    existing,
                    actor_id=current.account_id,
                    operation="create_session",
                    payload=payload,
                )
                view = SessionRepository(session).get(existing.result_id)
                if view is None:
                    raise ConflictError("原排课记录不存在，请核实请求编号")
                return view

            # 锁顺序：教练 → 课程模板 → 场地，与并发控制规则一致。
            coach = CoachRepository(session).lock(data.coach_id)
            if coach is None:
                raise NotFoundError("教练不存在")
            if not coach.is_active:
                raise InvalidState("教练已停用，不能排课")

            course = CourseRepository(session).lock(data.course_id)
            if course is None:
                raise NotFoundError("课程模板不存在")
            if not course.is_active:
                raise InvalidState("课程模板已归档，不能排课")

            room = RoomRepository(session).lock(data.room_id)
            if room is None:
                raise NotFoundError("场地不存在")
            if not room.is_active:
                raise InvalidState("场地已停用，不能排课")

            starts_at, ends_at = _session_window(data, course)
            session_repo = SessionRepository(session)
            if session_repo.has_conflict(
                coach_id=data.coach_id,
                room_id=data.room_id,
                window=DateWindow(start=starts_at, end=ends_at),
            ):
                raise ScheduleConflict("教练或场地在该时段已有课次")

            view = session_repo.create(
                data, course_name=course.name, kind=course.kind,
            )
            operations.create(
                request_id=request_id,
                actor_id=current.account_id,
                operation="create_session",
                payload_hash=payload,
                result_id=view.id,
            )
            return view

        return _write(
            self._session_factory, self._auth, actor, action, request_id=request_id,
        )

    def get_session(self, actor: Actor, session_id: int) -> SessionView:
        """查询课次详情。

        返回：SessionView。不修改业务数据；教练只能查看自己的课次。
        """
        def action(session: Session, current: Actor) -> SessionView:
            view = SessionRepository(session).get(session_id)
            if view is None:
                raise NotFoundError("课次不存在")
            _ensure_session_visible(current, view)
            return view

        return _read(self._session_factory, self._auth, actor, action)

    def list_sessions(self, actor: Actor, query: SessionQuery) -> Page[SessionView]:
        """分页查询课表。

        返回：Page[SessionView]。不修改业务数据；教练只能查自己的课表。
        """
        if query.kind is not None and query.kind != "private":
            raise InvalidInputError("当前只支持私教课（private）")
        scoped = _session_scope(actor, query)

        def action(session: Session, current: Actor) -> Page[SessionView]:  # noqa: ARG001
            return SessionRepository(session).list(scoped)

        return _read(self._session_factory, self._auth, actor, action)

    def get_session_by_request(self, actor: Actor, request_id: str) -> SessionView:
        """按本人原排课或取消请求核实结果，返回课次的当前 SessionView。

        不写数据；无记录或不可见抛 NotFoundError，操作类型不匹配抛 ConflictError。
        查不到不能证明原提交失败；其余异常按设计第 4.1 节。
        """
        request_id = validate_request_id(request_id)

        def action(session: Session, current: Actor) -> SessionView:
            record = OperationRepository(session).get_by_request(request_id)
            if record is None:
                raise NotFoundError("没有该请求编号的记录")
            if record.operation not in ("create_session", "cancel_session"):
                raise ConflictError("该请求编号属于其他操作")
            if record.actor_id != current.account_id:
                raise NotFoundError("没有该请求编号的记录")
            view = SessionRepository(session).get(record.result_id)
            if view is None:
                raise NotFoundError("课次不存在")
            _ensure_session_visible(current, view)
            return view

        return _read(self._session_factory, self._auth, actor, action)

    def complete_session(self, actor: Actor, session_id: int) -> SessionView:
        """本课教练或管理员结束已到结束时间且没有待处理预约的课次。

        返回 SessionView；同事务更新课次状态，重复完成返回当前结果。
        尚未结束、有 reserved/checked_in 预约或已取消时抛 InvalidState。
        """
        def action(session: Session, current: Actor) -> SessionView:
            repo = SessionRepository(session)
            course_session = repo.lock(session_id)
            if course_session is None:
                raise NotFoundError("课次不存在")
            if current.role != "admin" and not (
                current.role == "coach" and current.coach_id == course_session.coach_id
            ):
                raise PermissionDenied("只有管理员或本课教练可以完成课次")
            if course_session.status == "completed":
                return repo.get(session_id)
            if course_session.status == "cancelled":
                raise InvalidState("已取消的课次不能完成")
            if course_session.ends_at > utc_now():
                raise InvalidState("课次尚未结束，不能完成")
            if BookingRepository(session).count_occupied(session_id) > 0:
                raise InvalidState("仍有待处理的预约，不能完成课次")
            return repo.set_status(session_id, "completed")

        return _write(self._session_factory, self._auth, actor, action)

    def cancel_session(self, actor: Actor, session_id: int, request_id: str) -> SessionView:
        """取消课次并释放预约占用。

        管理员在开课前取消；所有未取消预约改为 cancelled，并释放私教额度占用。
        返回：SessionView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        request_id = validate_request_id(request_id)
        payload = payload_hash({"session_id": session_id})

        def action(session: Session, current: Actor) -> SessionView:
            _require_admin(current)
            operations = OperationRepository(session)
            existing = operations.get_by_request(request_id)
            if existing is not None:
                ensure_replay_matches(
                    existing,
                    actor_id=current.account_id,
                    operation="cancel_session",
                    payload=payload,
                )
                view = SessionRepository(session).get(existing.result_id)
                if view is None:
                    raise ConflictError("原取消记录不存在，请核实请求编号")
                return view

            repo = SessionRepository(session)
            course_session = repo.lock(session_id)
            if course_session is None:
                raise NotFoundError("课次不存在")
            if course_session.status == "cancelled":
                raise InvalidState("课次已取消")
            if course_session.status == "completed":
                raise InvalidState("已完成的课次不能取消")

            now = utc_now()
            if course_session.starts_at <= now:
                raise InvalidState("课次已开始，不能取消")

            active = active_bookings_for_session(session, session_id)
            # 先按编号升序锁卡，再逐条释放，避免不同顺序加锁造成死锁。
            locked_cards = lock_memberships(
                session, [booking.membership_id for booking in active]
            )
            for booking in active:
                if booking.membership_id not in locked_cards:
                    raise StorageError("预约关联的会员卡不存在，请核实数据")
                release_private_lessons(session, booking.membership_id)

            booking_repo = BookingRepository(session)
            for booking in active:
                booking_repo.set_state(
                    booking.id,
                    status="cancelled",
                    checked_in_at=None,
                    closed_at=now,
                )

            view = repo.set_status(session_id, "cancelled")
            operations.create(
                request_id=request_id,
                actor_id=current.account_id,
                operation="cancel_session",
                payload_hash=payload,
                result_id=view.id,
            )
            return view

        return _write(
            self._session_factory, self._auth, actor, action, request_id=request_id,
        )
