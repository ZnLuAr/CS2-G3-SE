"""预约服务；事务由 ReservationLogic 管理。"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.booking_repo import BookingRepository
from src.db.course_repo import SessionRepository
from src.db.lesson_package_repo import LessonPackageRepository
from src.db.member_repo import MemberRepository
from src.db.operation_repo import OperationRepository
from src.db.tables import gym_entries
from src.db.support import payload_hash, utc_now
from src.errors.business import (
    CapacityExceeded, CardNotEligible, ConflictError, InsufficientCredits,
    InvalidInputError, InvalidState, NotFoundError, PermissionDenied,
    ScheduleConflict,
)
from src.models.contracts import (
    Actor, BookingInput, BookingQuery, BookingView, DateWindow, Page,
)
from src.services.auth_service import AuthService
from src.services.course_booking_rules import (
    ensure_replay, positive_id, request_uuid,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _active(booking) -> bool:
    return booking.status in ("reserved", "checked_in")


def _book_permission(actor: Actor, member_id: int) -> None:
    if actor.role in ("receptionist", "admin"):
        return
    if actor.role == "member" and actor.member_id == member_id:
        return
    raise PermissionDenied("只能为自己预约课次")


def _cancel_permission(actor: Actor, view: BookingView) -> None:
    if actor.role in ("receptionist", "admin"):
        return
    if actor.role == "member" and actor.member_id == view.member_id:
        return
    raise PermissionDenied("只能取消自己的预约")


def _visible(actor: Actor, view: BookingView) -> None:
    if actor.role in ("receptionist", "admin"):
        return
    if actor.role == "member":
        if actor.member_id is None or view.member_id != actor.member_id:
            raise NotFoundError("预约不存在")
        return
    if actor.role == "coach":
        if actor.coach_id is None or view.session.coach.id != actor.coach_id:
            raise NotFoundError("预约不存在")
        return
    raise PermissionDenied("当前角色不能查看预约")


class BookingService:
    """预约服务；actor 来自可信登录会话。"""

    def __init__(self, auth: AuthService, *, timezone_name: str) -> None:
        self._auth = auth
        try:
            self._timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise InvalidInputError("门店时区配置无效") from exc
        self._timezone_name = timezone_name

    def book(self, session: Session, actor: Actor, data: BookingInput, request_id: str) -> BookingView:
        request_id = request_uuid(request_id)
        if not isinstance(data, BookingInput):
            raise InvalidInputError("预约输入格式不正确")
        positive_id(data.member_id, "会员编号")
        positive_id(data.session_id, "课次编号")
        positive_id(data.lesson_package_id, "课包编号")
        payload = payload_hash({
            "member_id": data.member_id, "session_id": data.session_id,
            "lesson_package_id": data.lesson_package_id,
        })
        current = self._auth.verify_actor(session, actor)
        _book_permission(current, data.member_id)
        operations = OperationRepository(session)
        existing = operations.get_by_request(request_id)
        if existing is not None:
            ensure_replay(existing, actor_id=current.account_id, operation="book", payload=payload)
            view = BookingRepository(session).get(existing.result_id)
            if view is None:
                raise ConflictError("原预约记录不存在")
            _visible(current, view)
            return view

        member = MemberRepository(session).lock(data.member_id)
        if member is None:
            raise NotFoundError("会员不存在")
        if member.status != "active":
            raise InvalidState("会员档案已归档，不能预约")
        course_session = SessionRepository(session).lock(data.session_id)
        if course_session is None:
            raise NotFoundError("课次不存在")
        if course_session.status != "scheduled":
            raise InvalidState("课次已取消或已完成")
        now = utc_now()
        if course_session.starts_at <= now:
            raise InvalidState("课次已开始，不能预约")
        package = LessonPackageRepository(session).lock(data.lesson_package_id)
        if package is None:
            raise CardNotEligible("私教课包不存在或不可用")
        if package.member_id != data.member_id:
            raise CardNotEligible("私教课包不属于该会员")
        if package.status != "active":
            raise CardNotEligible("私教课包已作废")
        class_date = course_session.starts_at.astimezone(self._timezone).date()
        if class_date < package.valid_from:
            raise CardNotEligible("私教课包尚未生效")
        if package.valid_until is not None and class_date >= package.valid_until:
            raise CardNotEligible("上课日期不在私教课包有效期内")

        repo = BookingRepository(session)
        if repo.find_for_member_session(data.member_id, data.session_id) is not None:
            raise ConflictError("该会员已预约过此课次")
        if repo.count_occupied(data.session_id) >= course_session.capacity:
            raise CapacityExceeded("课次已满员")
        if repo.has_member_conflict(
            data.member_id,
            DateWindow(start=course_session.starts_at, end=course_session.ends_at),
        ):
            raise ScheduleConflict("会员在该时段已有其他预约")
        if package.remaining_lessons - package.reserved_lessons < 1:
            raise InsufficientCredits("私教课节不足")

        LessonPackageRepository(session).reserve_one(data.lesson_package_id)
        view = repo.create(data, now)
        operations.create(
            request_id=request_id, actor_id=current.account_id,
            operation="book", payload_hash=payload, result_id=view.id,
        )
        return view

    def get_booking(self, session: Session, actor: Actor, booking_id: int) -> BookingView:
        positive_id(booking_id, "预约编号")
        current = self._auth.verify_actor(session, actor)
        view = BookingRepository(session).get(booking_id)
        if view is None:
            raise NotFoundError("预约不存在")
        _visible(current, view)
        return view

    def get_booking_by_request(self, session: Session, actor: Actor, request_id: str) -> BookingView:
        request_id = request_uuid(request_id)
        current = self._auth.verify_actor(session, actor)
        record = OperationRepository(session).get_by_request(request_id)
        if record is None:
            raise NotFoundError("没有该请求编号的记录")
        if record.actor_id != current.account_id and current.role != "admin":
            raise NotFoundError("没有该请求编号的记录")
        if record.operation not in ("book", "cancel_booking"):
            raise ConflictError("该请求编号属于其他操作")
        view = BookingRepository(session).get(record.result_id)
        if view is None:
            raise NotFoundError("预约不存在")
        _visible(current, view)
        return view

    def cancel(self, session: Session, actor: Actor, booking_id: int, request_id: str) -> BookingView:
        request_id = request_uuid(request_id)
        positive_id(booking_id, "预约编号")
        payload = payload_hash({"booking_id": booking_id})
        current = self._auth.verify_actor(session, actor)
        repo = BookingRepository(session)
        view = repo.get(booking_id)
        if view is None:
            raise NotFoundError("预约不存在")
        _cancel_permission(current, view)
        existing = OperationRepository(session).get_by_request(request_id)
        if existing is not None:
            ensure_replay(existing, actor_id=current.account_id, operation="cancel_booking", payload=payload)
            replay = repo.get(existing.result_id)
            if replay is None:
                raise ConflictError("原取消记录不存在")
            _visible(current, replay)
            return replay

        # 锁顺序：会员 → 课次 → 课包 → 预约。
        if MemberRepository(session).lock(view.member_id) is None:
            raise NotFoundError("会员不存在")
        course_session = SessionRepository(session).lock(view.session.id)
        if course_session is None:
            raise NotFoundError("课次不存在")
        if course_session.status == "cancelled":
            raise InvalidState("课次已取消")
        package = LessonPackageRepository(session).lock(view.lesson_package_id)
        if package is None:
            raise NotFoundError("私教课包不存在")
        locked = repo.lock(booking_id)
        if locked is None:
            raise NotFoundError("预约不存在")
        if locked.status != "reserved":
            raise InvalidState("已签到、已完成或已取消的预约不能取消")
        now = utc_now()
        if course_session.starts_at <= now:
            raise InvalidState("课次已开始，不能取消预约")
        if session.execute(
            select(gym_entries.c.id).where(
                gym_entries.c.booking_id == booking_id
            ).with_for_update().limit(1)
        ).first() is not None:
            raise InvalidState("会员已凭该预约入场，不能取消")
        LessonPackageRepository(session).release_one(locked.lesson_package_id)
        result = repo.set_state(
            locked.id, status="cancelled", checked_in_at=None, closed_at=now,
        )
        OperationRepository(session).create(
            request_id=request_id, actor_id=current.account_id,
            operation="cancel_booking", payload_hash=payload, result_id=result.id,
        )
        return result

    def list_bookings(self, session: Session, actor: Actor, query: BookingQuery) -> Page[BookingView]:
        if not isinstance(query, BookingQuery):
            raise InvalidInputError("预约查询格式不正确")
        current = self._auth.verify_actor(session, actor)
        scope_member_id = None
        scope_coach_id = None
        if current.role == "member":
            if current.member_id is None:
                raise PermissionDenied("当前账号未关联会员档案")
            if query.member_id is not None and query.member_id != current.member_id:
                raise PermissionDenied("会员只能查看自己的预约")
            scope_member_id = current.member_id
        elif current.role == "coach":
            if current.coach_id is None:
                raise PermissionDenied("当前账号未关联教练档案")
            scope_coach_id = current.coach_id
        return BookingRepository(session).list(
            query, scope_member_id=scope_member_id, scope_coach_id=scope_coach_id,
        )

    def reserve_for_waitlist(self, session: Session, data: BookingInput, booked_at: datetime) -> BookingView:
        """候补递补写入；Logic 已持有会员、课次和课包锁。"""
        repo = BookingRepository(session)
        LessonPackageRepository(session).reserve_one(data.lesson_package_id)
        return repo.create(data, booked_at)

    def cancel_for_session(self, session: Session, booking_id: int, closed_at: datetime) -> BookingView:
        """课次取消内部使用：关闭开放预约并释放课包占用。"""
        repo = BookingRepository(session)
        booking = repo.lock(booking_id)
        if booking is None:
            raise NotFoundError("预约不存在")
        if booking.status == "cancelled":
            view = repo.get(booking_id)
            if view is None:
                raise NotFoundError("预约不存在")
            return view
        if booking.status not in ("reserved", "checked_in"):
            raise InvalidState("已完成或缺席的预约不能随课次取消")
        LessonPackageRepository(session).release_one(booking.lesson_package_id)
        return repo.set_state(
            booking.id, status="cancelled", checked_in_at=None, closed_at=closed_at,
        )
