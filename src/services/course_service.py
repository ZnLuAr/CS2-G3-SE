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
from typing import TYPE_CHECKING, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from src.db.course_repo import CoachRepository, CourseRepository, RoomRepository
from src.errors.base import GymError
from src.errors.business import InvalidInputError, NotFoundError, PermissionDenied
from src.errors.storage import StorageError
from src.models.contracts import (
    Actor,
    CoachInput,
    CoachUpdateInput,
    CoachView,
    CourseInput,
    CourseQuery,
    CourseView,
    NamedQuery,
    Page,
    RoomInput,
    RoomView,
    SessionInput,
    SessionQuery,
    SessionView,
)
from src.services.auth_service import AuthService

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
        异常：当前为 NotImplementedError，子任务 3 实现。
        """
        raise NotImplementedError("CourseService.create_session 尚未实现")

    def get_session(self, actor: Actor, session_id: int) -> SessionView:
        """查询课次详情。

        返回：SessionView。不修改业务数据。
        异常：当前为 NotImplementedError，子任务 3 实现。
        """
        raise NotImplementedError("CourseService.get_session 尚未实现")

    def list_sessions(self, actor: Actor, query: SessionQuery) -> Page[SessionView]:
        """分页查询课表。

        返回：Page[SessionView]。不修改业务数据。
        异常：当前为 NotImplementedError，子任务 3 实现。
        """
        raise NotImplementedError("CourseService.list_sessions 尚未实现")

    def get_session_by_request(self, actor: Actor, request_id: str) -> SessionView:
        """按本人原排课或取消请求核实结果，返回课次的当前 SessionView。

        不写数据；无记录或不可见抛 NotFoundError，操作类型不匹配抛 ConflictError。
        查不到不能证明原提交失败；其余异常按设计第 4.1 节。当前为 NotImplementedError。
        """
        raise NotImplementedError("CourseService.get_session_by_request 尚未实现")

    def complete_session(self, actor: Actor, session_id: int) -> SessionView:
        """本课教练或管理员结束已到结束时间且没有待处理预约的课次。

        返回 SessionView；同事务更新课次状态，重复完成返回当前结果。
        尚未结束、有 reserved/checked_in 预约或已取消时抛 InvalidState。
        其余异常按设计第 4.1 节；当前为 NotImplementedError。
        """
        raise NotImplementedError("CourseService.complete_session 尚未实现")

    def cancel_session(self, actor: Actor, session_id: int, request_id: str) -> SessionView:
        """取消课次并释放预约占用。

        返回：SessionView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError，子任务 3 实现。
        """
        raise NotImplementedError("CourseService.cancel_session 尚未实现")
