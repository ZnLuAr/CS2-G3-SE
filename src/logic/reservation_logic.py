"""ReservationLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        BookingInput,
        BookingQuery,
        BookingView,
        Page,
        SessionView,
        WaitlistInput,
        WaitlistQuery,
        WaitlistSummaryView,
        WaitlistView,
    )
    from src.services.booking_service import BookingService
    from src.services.course_service import CourseService
    from src.services.notification_service import NotificationService
    from src.services.waitlist_service import WaitlistService


class ReservationLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        booking_service: BookingService,
        course_service: CourseService,
        notification_service: NotificationService,
        waitlist_service: WaitlistService,
    ) -> None:
        self._session_factory = session_factory
        self._booking_service = booking_service
        self._course_service = course_service
        self._notification_service = notification_service
        self._waitlist_service = waitlist_service

    def cancel_session(self, actor: Actor, session_id: int, request_id: str) -> SessionView:
        raise NotImplementedError

    def book(self, actor: Actor, data: BookingInput, request_id: str) -> BookingView:
        raise NotImplementedError

    def cancel(self, actor: Actor, booking_id: int, request_id: str) -> BookingView:
        raise NotImplementedError

    def get_booking(self, actor: Actor, booking_id: int) -> BookingView:
        raise NotImplementedError

    def get_booking_by_request(self, actor: Actor, request_id: str) -> BookingView:
        raise NotImplementedError

    def list_bookings(self, actor: Actor, query: BookingQuery) -> Page[BookingView]:
        raise NotImplementedError

    def join_waitlist(self, actor: Actor, data: WaitlistInput, request_id: str) -> WaitlistView:
        raise NotImplementedError

    def leave_waitlist(self, actor: Actor, waitlist_id: int) -> WaitlistView:
        raise NotImplementedError

    def get_waitlist(self, actor: Actor, waitlist_id: int) -> WaitlistView:
        raise NotImplementedError

    def get_waitlist_by_request(self, actor: Actor, request_id: str) -> WaitlistView:
        raise NotImplementedError

    def list_waitlist(self, actor: Actor, query: WaitlistQuery) -> Page[WaitlistView]:
        raise NotImplementedError

    def get_waitlist_summary(self, actor: Actor, session_id: int) -> WaitlistSummaryView:
        raise NotImplementedError

    def reconcile_waitlists(self) -> None:
        raise NotImplementedError
