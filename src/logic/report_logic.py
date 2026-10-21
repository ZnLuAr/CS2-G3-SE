"""报表用例：每次调用使用独立 Session，所有读取共用同一事务快照。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from src.errors.storage import StorageError
from src.errors.business import ResourceError
from src.models.contracts import (
    Actor, CoachStatsView, CsvExport, DateWindow, MembershipStats, Page, PageRequest,
    PaymentQuery, PaymentView, RevenueView, SessionQuery, SessionStatsView,
)
from src.services.report_service import ReportService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

T = TypeVar("T")


class ReportLogic:
    def __init__(
        self, session_factory: Callable[[], Session], report_service: ReportService,
    ) -> None:
        self._session_factory = session_factory
        self._report_service = report_service

    def _read(self, action: Callable[[Session], T], *, export: bool = False) -> T:
        try:
            # 引擎使用 REPEATABLE READ；关闭 Session 会回滚读取事务并释放身份锁。
            with self._session_factory() as session:
                return action(session)
        except (SQLAlchemyError, StorageError) as exc:
            if export:
                raise ResourceError("导出读取快照失败") from exc
            raise StorageError("读取收款或报表失败") from exc

    def get_payment(self, actor: Actor, payment_id: int) -> PaymentView:
        return self._read(lambda session: self._report_service.get_payment(session, actor, payment_id))

    def list_payments(self, actor: Actor, query: PaymentQuery) -> Page[PaymentView]:
        return self._read(lambda session: self._report_service.list_payments(session, actor, query))

    def revenue(self, actor: Actor, window: DateWindow) -> RevenueView:
        return self._read(lambda session: self._report_service.revenue(session, actor, window))

    def membership_stats(self, actor: Actor) -> MembershipStats:
        return self._read(lambda session: self._report_service.membership_stats(session, actor))

    def session_stats(self, actor: Actor, query: SessionQuery) -> Page[SessionStatsView]:
        return self._read(lambda session: self._report_service.session_stats(session, actor, query))

    def coach_stats(self, actor: Actor, window: DateWindow, paging: PageRequest) -> Page[CoachStatsView]:
        return self._read(lambda session: self._report_service.coach_stats(session, actor, window, paging))

    def export_payments(self, actor: Actor, query: PaymentQuery) -> CsvExport:
        return self._read(lambda session: self._report_service.export_payments(session, actor, query), export=True)

    def export_revenue(self, actor: Actor, window: DateWindow) -> CsvExport:
        return self._read(lambda session: self._report_service.export_revenue(session, actor, window), export=True)

    def export_memberships(self, actor: Actor, as_of: datetime) -> CsvExport:
        return self._read(lambda session: self._report_service.export_memberships(session, actor, as_of), export=True)

    def export_sessions(self, actor: Actor, query: SessionQuery) -> CsvExport:
        return self._read(lambda session: self._report_service.export_sessions(session, actor, query), export=True)

    def export_coaches(self, actor: Actor, window: DateWindow) -> CsvExport:
        return self._read(lambda session: self._report_service.export_coaches(session, actor, window), export=True)
