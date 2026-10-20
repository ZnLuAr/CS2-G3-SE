"""ReportLogic use-case entry points."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        CoachStatsView,
        CsvExport,
        DateWindow,
        MembershipStats,
        Page,
        PageRequest,
        PaymentQuery,
        PaymentView,
        RevenueView,
        SessionStatsView,
        SessionQuery,
    )
    from src.services.report_service import ReportService


class ReportLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        report_service: ReportService,
    ) -> None:
        self._session_factory = session_factory
        self._report_service = report_service

    def get_payment(self, actor: Actor, payment_id: int) -> PaymentView:
        raise NotImplementedError

    def list_payments(self, actor: Actor, query: PaymentQuery) -> Page[PaymentView]:
        raise NotImplementedError

    def revenue(self, actor: Actor, window: DateWindow) -> RevenueView:
        raise NotImplementedError

    def membership_stats(self, actor: Actor) -> MembershipStats:
        raise NotImplementedError

    def session_stats(self, actor: Actor, query: SessionQuery) -> Page[SessionStatsView]:
        raise NotImplementedError

    def coach_stats(self, actor: Actor, window: DateWindow, paging: PageRequest) -> Page[CoachStatsView]:
        raise NotImplementedError

    def export_payments(self, actor: Actor, query: PaymentQuery) -> CsvExport:
        raise NotImplementedError

    def export_revenue(self, actor: Actor, window: DateWindow) -> CsvExport:
        raise NotImplementedError

    def export_memberships(self, actor: Actor, as_of: datetime) -> CsvExport:
        raise NotImplementedError

    def export_sessions(self, actor: Actor, query: SessionQuery) -> CsvExport:
        raise NotImplementedError

    def export_coaches(self, actor: Actor, window: DateWindow) -> CsvExport:
        raise NotImplementedError
