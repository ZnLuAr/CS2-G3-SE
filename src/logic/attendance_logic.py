"""AttendanceLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        BookingView,
        ConsumptionView,
    )
    from src.services.attendance_service import AttendanceService


class AttendanceLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        attendance_service: AttendanceService,
    ) -> None:
        self._session_factory = session_factory
        self._attendance_service = attendance_service

    def check_in(self, actor: Actor, booking_id: int) -> BookingView:
        raise NotImplementedError

    def correct_attendance(self, actor: Actor, booking_id: int, present: bool) -> BookingView:
        raise NotImplementedError

    def complete(self, actor: Actor, booking_id: int) -> ConsumptionView:
        raise NotImplementedError

    def mark_no_show(self, actor: Actor, booking_id: int) -> BookingView:
        raise NotImplementedError
