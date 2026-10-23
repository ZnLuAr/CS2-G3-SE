"""收款查询、经营统计和 CSV 导出；复用调用方的数据库会话。"""

from __future__ import annotations

import csv
import io
from dataclasses import fields
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import wraps
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError

from src.db.payment_repo import PaymentRepository
from src.db.report_repo import ReportRepository
from src.errors.business import InvalidInputError, NotFoundError, PermissionDenied, ResourceError
from src.models.contracts import (
    Actor, CoachStatsView, CsvExport, DateWindow, MembershipStats, Page, PageRequest,
    PaymentQuery, PaymentView, RevenueView, SessionQuery, SessionStatsView,
)
from src.models.payment import Payment
from src.services.auth_service import AuthService
from src.errors.storage import StorageError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_EXPORT_LIMIT = 10_000
_BATCH_SIZE = 500
_MAX_ID = 2**63 - 1


def _positive_id(value: int) -> None:
    if type(value) is not int or not 1 <= value <= _MAX_ID:
        raise InvalidInputError("编号必须为 BIGINT 范围内的正整数")


def _window(window: DateWindow) -> None:
    if not isinstance(window, DateWindow):
        raise InvalidInputError("时间范围格式不合法")
    endpoints = []
    for value in (window.start, window.end):
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise InvalidInputError("时间范围必须包含时区")
        try:
            utc = value.astimezone(timezone.utc)
        except (OverflowError, ValueError) as exc:
            raise InvalidInputError("时间范围超出数据库可用范围") from exc
        if utc.year < 1000:
            raise InvalidInputError("时间范围超出数据库可用范围")
        endpoints.append(utc)
    if endpoints[0] >= endpoints[1]:
        raise InvalidInputError("开始时间必须早于结束时间")


def _paging(paging: PageRequest) -> None:
    if (
        not isinstance(paging, PageRequest)
        or type(paging.page) is not int or not 1 <= paging.page <= _MAX_ID
        or type(paging.page_size) is not int or not 1 <= paging.page_size <= 100
        or (paging.page - 1) * paging.page_size > _MAX_ID
    ):
        raise InvalidInputError("分页参数不合法，每页为 1 至 100 条")


def _payment_query(query: PaymentQuery, *, paging: bool = True) -> None:
    if not isinstance(query, PaymentQuery):
        raise InvalidInputError("收款查询格式不合法")
    if query.window is not None:
        _window(query.window)
    if query.member_id is not None:
        _positive_id(query.member_id)
    if query.method is not None and query.method not in ("cash", "card", "transfer"):
        raise InvalidInputError("收款方式不合法")
    if paging:
        _paging(query.paging)


def _session_query(query: SessionQuery, *, paging: bool = True) -> None:
    if not isinstance(query, SessionQuery):
        raise InvalidInputError("课次查询格式不合法")
    if query.window is not None:
        _window(query.window)
    for value in (query.coach_id, query.room_id):
        if value is not None:
            _positive_id(value)
    if query.kind is not None and query.kind != "private":
        raise InvalidInputError("课程类型不合法")
    if query.status is not None and query.status not in ("scheduled", "completed", "cancelled"):
        raise InvalidInputError("课次状态不合法")
    if paging:
        _paging(query.paging)


def _payment_view(payment: Payment) -> PaymentView:
    return PaymentView(
        id=payment.id, sale_order_id=payment.sale_order_id, member_id=payment.member_id,
        amount=payment.amount, method=payment.method, paid_at=payment.paid_at,
        operator_id=payment.operator_id,
    )


def _export_resources(method):
    @wraps(method)
    def export(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except (SQLAlchemyError, StorageError) as exc:
            raise ResourceError("导出读取快照失败") from exc
    return export


class ReportService:
    """先复核当前身份，再在同一事务快照中读取授权数据。"""

    def __init__(self, auth: AuthService, *, timezone_name: str) -> None:
        self._auth = auth
        self._timezone_name = timezone_name
        self._zone = ZoneInfo(timezone_name)

    def _authorize(self, session: Session, actor: Actor, *, payments: bool = False) -> None:
        actor = self._auth.verify_actor(session, actor)
        roles = ("admin", "receptionist") if payments else ("admin",)
        if actor.role not in roles:
            raise PermissionDenied("当前角色无权查询此报表")

    def get_payment(self, session: Session, actor: Actor, payment_id: int) -> PaymentView:
        """前台或管理员按编号查收款；不存在抛 NotFoundError。"""
        self._authorize(session, actor, payments=True)
        _positive_id(payment_id)
        payment = PaymentRepository(session).get(payment_id)
        if payment is None:
            raise NotFoundError("收款记录不存在")
        return _payment_view(payment)

    def list_payments(self, session: Session, actor: Actor, query: PaymentQuery) -> Page[PaymentView]:
        """前台或管理员筛选流水；返回稳定分页，空结果为 Page。"""
        self._authorize(session, actor, payments=True)
        _payment_query(query)
        records, total = PaymentRepository(session).list(query)
        return Page(
            items=[_payment_view(record) for record in records], total=total,
            page=query.paging.page, page_size=query.paging.page_size,
        )

    def revenue(self, session: Session, actor: Actor, window: DateWindow) -> RevenueView:
        """管理员汇总 [start, end) 内实收，按两种销售类型分类。"""
        self._authorize(session, actor)
        _window(window)
        return ReportRepository(session).revenue(window)

    def membership_stats(self, session: Session, actor: Actor) -> MembershipStats:
        """管理员统计当前快照；服务生成统计时刻和门店业务日期。"""
        self._authorize(session, actor)
        as_of = datetime.now(timezone.utc)
        return ReportRepository(session).membership_stats(
            as_of, business_date=as_of.astimezone(self._zone).date(),
        )

    def session_stats(self, session: Session, actor: Actor, query: SessionQuery) -> Page[SessionStatsView]:
        """管理员按全部筛选条件查询课次统计及已结算到课率。"""
        self._authorize(session, actor)
        _session_query(query)
        return ReportRepository(session).session_stats(query, as_of=datetime.now(timezone.utc))

    def coach_stats(
        self, session: Session, actor: Actor, window: DateWindow, paging: PageRequest,
    ) -> Page[CoachStatsView]:
        """管理员分页统计教练完成课次和到课人次。"""
        self._authorize(session, actor)
        _window(window)
        _paging(paging)
        return ReportRepository(session).coach_stats(window, paging)

    @staticmethod
    def _csv(filename: str, headers: list[str], rows: list[list[object]]) -> CsvExport:
        if len(rows) > _EXPORT_LIMIT:
            raise InvalidInputError("导出超过 10000 行，请缩小筛选范围")
        try:
            stream = io.StringIO(newline="")
            writer = csv.writer(stream, lineterminator="\r\n")
            writer.writerow(headers)
            for row in rows:
                values = []
                for value in row:
                    if value is None:
                        value = ""
                    elif isinstance(value, datetime):
                        value = value.isoformat()
                    elif isinstance(value, date):
                        value = value.isoformat()
                    elif isinstance(value, Decimal):
                        value = format(value, "f")
                    elif isinstance(value, str):
                        # 包含前导空白的公式也需转义，数值列保持数值语义。
                        if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
                            value = "'" + value
                    values.append(value)
                writer.writerow(values)
            content = ("\ufeff" + stream.getvalue()).encode("utf-8")
        except (UnicodeError, csv.Error, OSError, ValueError) as exc:
            raise ResourceError("CSV 编码失败") from exc
        return CsvExport(filename=filename, content=content, row_count=len(rows))

    @staticmethod
    def _check_limit(rows: list[object]) -> None:
        if len(rows) > _EXPORT_LIMIT:
            raise InvalidInputError("导出超过 10000 行，请缩小筛选范围")

    @_export_resources
    def export_payments(self, session: Session, actor: Actor, query: PaymentQuery) -> CsvExport:
        """管理员按当前筛选，以主键游标分批导出，最多 10000 行。"""
        self._authorize(session, actor)
        _payment_query(query, paging=False)
        repository = PaymentRepository(session)
        rows = []
        after_id = 0
        while True:
            batch = repository.list_batch(
                query, after_id=after_id, limit=min(_BATCH_SIZE, _EXPORT_LIMIT + 1 - len(rows)),
            )
            if not batch:
                break
            rows.extend([
                p.id, p.sale_order_id, p.member_id, p.amount, p.method, p.paid_at, p.operator_id,
            ] for p in batch)
            self._check_limit(rows)
            after_id = batch[-1].id
        return self._csv(
            "payments.csv",
            ["id", "sale_order_id", "member_id", "amount", "method", "paid_at", "operator_id"],
            rows,
        )

    @_export_resources
    def export_revenue(self, session: Session, actor: Actor, window: DateWindow) -> CsvExport:
        """管理员导出销售种类实收明细；空数据保留表头。"""
        result = self.revenue(session, actor, window)
        rows = [
            [window.start, window.end, item.sale_kind, item.payment_count, item.total_amount]
            for item in result.breakdowns if item.payment_count
        ]
        return self._csv(
            "revenue.csv", ["start", "end", "sale_kind", "payment_count", "total_amount"], rows,
        )

    @_export_resources
    def export_memberships(self, session: Session, actor: Actor) -> CsvExport:
        """管理员导出当前权益快照，沿用屏幕统计的身份、时刻和业务日期口径。"""
        result = self.membership_stats(session, actor)
        names = [field.name for field in fields(MembershipStats)]
        rows = [[getattr(result, name) for name in names]]
        if not any(getattr(result, name) for name in names[2:]):
            rows = []
        return self._csv("memberships.csv", names, rows)

    @_export_resources
    def export_sessions(self, session: Session, actor: Actor, query: SessionQuery) -> CsvExport:
        """管理员以同一快照、全部筛选条件导出课次统计。"""
        self._authorize(session, actor)
        _session_query(query, paging=False)
        as_of = datetime.now(timezone.utc)
        repository = ReportRepository(session)
        rows = []
        after_id = 0
        while True:
            batch = repository.session_stats_batch(
                query, as_of=as_of, after_id=after_id,
                limit=min(_BATCH_SIZE, _EXPORT_LIMIT + 1 - len(rows)),
            )
            if not batch:
                break
            rows.extend([
                item.session_id, item.starts_at, item.reserved_count, item.checked_in_count,
                item.completed_count, item.no_show_count, item.cancelled_count, item.attendance_rate,
            ] for item in batch)
            self._check_limit(rows)
            after_id = batch[-1].session_id
        return self._csv(
            "sessions.csv",
            ["session_id", "starts_at", "reserved_count", "checked_in_count",
             "completed_count", "no_show_count", "cancelled_count", "attendance_rate"],
            rows,
        )

    @_export_resources
    def export_coaches(self, session: Session, actor: Actor, window: DateWindow) -> CsvExport:
        """管理员以教练主键游标导出授课统计，姓名按文本公式规则转义。"""
        self._authorize(session, actor)
        _window(window)
        repository = ReportRepository(session)
        rows = []
        after_id = 0
        while True:
            batch = repository.coach_stats_batch(
                window, after_id=after_id, limit=min(_BATCH_SIZE, _EXPORT_LIMIT + 1 - len(rows)),
            )
            if not batch:
                break
            rows.extend([
                item.coach_id, item.coach_name, item.completed_sessions, item.attended_members,
            ] for item in batch)
            self._check_limit(rows)
            after_id = batch[-1].coach_id
        return self._csv(
            "coaches.csv", ["coach_id", "coach_name", "completed_sessions", "attended_members"], rows,
        )
