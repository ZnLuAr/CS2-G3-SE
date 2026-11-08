"""签到与到场更正业务规则。"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.db.booking_repo import BookingRepository
from src.db.course_repo import SessionRepository
from src.db.member_repo import MemberRepository
from src.errors import InvalidInputError, InvalidState, NotFoundError, PermissionDenied, StorageError
from src.models.contracts import Actor, AttendanceChange, BookingView, ConsumptionView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.booking import Booking
    from src.models.course import CourseSession


ATTENDANCE_CHANGE_KEY = "attendance.correct.change"


class AttendanceService:
    """签到与消课服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    Logic 持有事务，服务复核当前身份、课次与预约。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def check_in(self, session: Session, actor: Actor, booking_id: int) -> BookingView:
        """确认预约会员到场。

        锁定预约后生成当前时刻；会员可从课次开始时刻起自行签到，本课教练、前台或管理员可代为签到。
        普通签到时间为 starts_at <= now < ends_at；本课教练或管理员课后补签使用 correct_attendance。
        按当前状态设计，取消、完成或缺席后不能签到；越过状态边界抛 InvalidState。

        返回：BookingView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：无权查看的预约抛 NotFoundError，超出时间或状态边界抛 InvalidState。
        """
        actor = self._auth.verify_actor(session, actor)
        repository = BookingRepository(session)
        booking, course_session = self._lock_booking(session, repository, actor, booking_id)
        if actor.role == "coach" and actor.coach_id != course_session.coach_id:
            raise NotFoundError("预约不存在")
        now = datetime.now(timezone.utc)
        if not course_session.starts_at <= now < course_session.ends_at:
            raise InvalidState("普通签到仅在开课后、下课前办理")
        self._require_open(booking, course_session)
        if booking.status == "checked_in":
            return self._current_view(repository, booking, course_session)
        return repository.set_state(
            booking_id, status="checked_in", checked_in_at=now, closed_at=None,
        )

    def correct_attendance(
        self, session: Session, actor: Actor, booking_id: int, present: bool,
    ) -> BookingView:
        """由本课教练或管理员更正会员的到场选择。

        present=True 为未结算预约补签，时间记录实际操作时刻；允许下课后办理。
        present=False 将已签到记录改回 reserved，并清空签到时间；相同选择返回当前记录。
        到场更正保持课包余额，合法原预约按其上课日期资格处理。
        取消、完成或缺席状态拒绝更正，抛 InvalidState；结算后不可冲正。
        无更正权限抛 PermissionDenied，目标不是布尔值时抛 InvalidInputError。
        返回 BookingView，将实际变更交给 Logic 在提交后记录。
        """
        actor = self._auth.verify_actor(session, actor)
        if actor.role not in {"coach", "admin"}:
            raise PermissionDenied("仅本课教练或管理员可以更正到场状态")
        if type(present) is not bool:
            raise InvalidInputError("到场状态必须是布尔值")
        repository = BookingRepository(session)
        booking, course_session = self._lock_booking(session, repository, actor, booking_id)
        if actor.role == "coach" and actor.coach_id != course_session.coach_id:
            raise PermissionDenied("仅本课教练或管理员可以更正到场状态")
        now = datetime.now(timezone.utc)
        if now < course_session.starts_at:
            raise InvalidState("开课前不能更正到场状态")
        self._require_open(booking, course_session)
        target = "checked_in" if present else "reserved"
        if booking.status == target:
            return self._current_view(repository, booking, course_session)
        result = repository.set_state(
            booking_id, status=target, checked_in_at=now if present else None, closed_at=None,
        )
        session.info[ATTENDANCE_CHANGE_KEY] = AttendanceChange(
            before="reserved" if present else "checked_in",
            after=target,
            before_checked_in_at=booking.checked_in_at,
            after_checked_in_at=result.checked_in_at,
            corrected_at=now,
        )
        return result

    @staticmethod
    def _lock_booking(
        session: Session, repository: BookingRepository, actor: Actor, booking_id: int,
    ) -> tuple[Booking, CourseSession]:
        if type(booking_id) is not int or not 1 <= booking_id <= 2**63 - 1:
            raise InvalidInputError("预约编号必须是有效的正整数")
        targets = repository.find_lock_targets(booking_id)
        if targets is None:
            raise NotFoundError("预约不存在")
        member_id, session_id = targets
        if actor.role == "member" and actor.member_id != member_id:
            raise NotFoundError("预约不存在")
        member = MemberRepository(session).lock(member_id)
        course_session = SessionRepository(session).lock(session_id)
        booking = repository.lock(booking_id)
        if member is None or course_session is None or booking is None:
            raise NotFoundError("预约不存在")
        if (booking.member_id, booking.session_id) != targets:
            raise InvalidState("预约归属已变化，请重新查询")
        return booking, course_session

    @staticmethod
    def _require_open(booking: Booking, course_session: CourseSession) -> None:
        if course_session.status != "scheduled" or booking.status not in {"reserved", "checked_in"}:
            raise InvalidState("课次或预约已经关闭")

    @staticmethod
    def _current_view(
        repository: BookingRepository, booking: Booking, course_session: CourseSession,
    ) -> BookingView:
        view = repository.get(booking.id)
        if view is None:
            raise StorageError("预约记录不存在")
        # 普通查询可能仍使用等待锁前的快照，预约状态和时间以锁定读为准。
        return replace(
            view, status=booking.status, booked_at=booking.booked_at,
            lesson_package_id=booking.lesson_package_id, checked_in_at=booking.checked_in_at,
            closed_at=booking.closed_at,
            session=replace(view.session, status=course_session.status, updated_at=course_session.updated_at),
        )

    def complete(self, session: Session, actor: Actor, booking_id: int) -> ConsumptionView:
        """本课教练或管理员在下课后登记消课，扣除 1 节私教并释放 1 节占用。

        按会员、课次、课包、预约顺序取得锁后生成当前时刻，须大于或等于 ends_at；否则抛 InvalidState。
        已完成预约通过锁定当前读取得原消课记录；重复消课返回原 ConsumptionView，不扣门禁次数。
        原预约的课包日期资格按上课日期确定；结算时复核占用与余额不变量。
        界面须在调用前确认结算；完成后不退还课节，也不修改签到状态。

        返回：ConsumptionView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AttendanceService.complete 尚未实现")

    def mark_no_show(self, session: Session, actor: Actor, booking_id: int) -> BookingView:
        """本课教练或管理员在下课后将 reserved 预约登记为缺席，释放 1 节占用。

        按会员、课次、课包、预约顺序取得锁后生成当前时刻，须大于或等于 ends_at；否则抛 InvalidState。
        不扣私教节数、不创建消费记录；重复处理返回当前 BookingView。
        界面须先确认；标记缺席后不可补签。

        返回：BookingView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AttendanceService.mark_no_show 尚未实现")
