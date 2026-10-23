"""预约与课次取消的用例入口；负责会话、事务和操作日志。"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from src.db.booking_repo import BookingRepository
from src.db.connection import transaction
from src.db.support import utc_now
from src.errors import StorageError
from src.logging import Operation, Outcome, log_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.services.booking_service import BookingService
    from src.services.course_service import CourseService
    from src.services.notification_service import NotificationService
    from src.services.waitlist_service import WaitlistService

T = TypeVar("T")


def _log(operation: str, actor: object, result_id: int | None = None, request_id: str | None = None) -> None:
    try:
        log_event(
            logging.INFO, operation=operation, outcome=Outcome.SUCCESS.value,
            actor_id=getattr(actor, "account_id", None), request_id=request_id, result_id=result_id,
        )
    except Exception:
        print("操作日志记录失败", file=sys.stderr)


class ReservationLogic:
    def __init__(
        self, session_factory: Callable[[], Session], booking_service: BookingService,
        course_service: CourseService, notification_service: NotificationService,
        waitlist_service: WaitlistService,
    ) -> None:
        self._session_factory = session_factory
        self._booking_service = booking_service
        self._course_service = course_service
        self._notification_service = notification_service
        self._waitlist_service = waitlist_service

    def _read(self, action: Callable[[Session], T]) -> T:
        try:
            with self._session_factory() as session, transaction(session):
                return action(session)
        except SQLAlchemyError as exc:
            raise StorageError("查询预约失败") from exc

    def _write(self, action: Callable[[Session], T], *, operation: str,
               actor: object, request_id: str) -> T:
        try:
            with self._session_factory() as session, transaction(session, request_id=request_id):
                result = action(session)
        except SQLAlchemyError as exc:
            raise StorageError("保存预约失败") from exc
        _log(operation, actor, getattr(result, "id", None), request_id)
        return result

    def cancel_session(self, actor, session_id, request_id):
        def action(session: Session):
            view = self._course_service.cancel_session(session, actor, session_id, request_id)
            # 同一事务内关闭所有仍开放的预约并释放课包占用。
            now = utc_now()
            for booking in BookingRepository(session).list_open_for_session(session_id):
                self._booking_service.cancel_for_session(session, booking.id, now)
            return view

        return self._write(action, operation=Operation.SESSION_CANCEL.value,
                           actor=actor, request_id=request_id)

    def book(self, actor, data, request_id):
        return self._write(
            lambda s: self._booking_service.book(s, actor, data, request_id),
            operation=Operation.BOOKING_CREATE.value, actor=actor, request_id=request_id,
        )

    def cancel(self, actor, booking_id, request_id):
        return self._write(
            lambda s: self._booking_service.cancel(s, actor, booking_id, request_id),
            operation=Operation.BOOKING_CANCEL.value, actor=actor, request_id=request_id,
        )

    def get_booking(self, actor, booking_id):
        return self._read(lambda s: self._booking_service.get_booking(s, actor, booking_id))

    def get_booking_by_request(self, actor, request_id):
        return self._read(lambda s: self._booking_service.get_booking_by_request(s, actor, request_id))

    def list_bookings(self, actor, query):
        return self._read(lambda s: self._booking_service.list_bookings(s, actor, query))

    # 候补扩展由 WAI 模块实现；本模块保留入口。
    def join_waitlist(self, actor, data, request_id):
        raise NotImplementedError

    def leave_waitlist(self, actor, waitlist_id):
        raise NotImplementedError

    def get_waitlist(self, actor, waitlist_id):
        raise NotImplementedError

    def get_waitlist_by_request(self, actor, request_id):
        raise NotImplementedError

    def list_waitlist(self, actor, query):
        raise NotImplementedError

    def get_waitlist_summary(self, actor, session_id):
        raise NotImplementedError

    def reconcile_waitlists(self) -> None:
        raise NotImplementedError
