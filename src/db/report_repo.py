"""会员权益、实收与课次报表的 SQL 聚合。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.errors.storage import StorageError
from src.models.contracts import (
    CoachStatsView,
    DateWindow,
    MembershipStats,
    Page,
    PageRequest,
    RevenueBreakdownView,
    RevenueView,
    SessionQuery,
    SessionStatsView,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _utc_input(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_output(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _session_filters(query: SessionQuery) -> tuple[str, dict[str, Any]]:
    clauses = ["1 = 1"]
    params: dict[str, Any] = {}
    for name in ("kind", "coach_id", "room_id", "status"):
        value = getattr(query, name)
        if value is not None:
            clauses.append(f"s.{name} = :{name}")
            params[name] = value
    if query.window is not None:
        clauses.extend(("s.starts_at >= :window_start", "s.starts_at < :window_end"))
        params.update(
            window_start=_utc_input(query.window.start),
            window_end=_utc_input(query.window.end),
        )
    return " AND ".join(clauses), params


_SESSION_COUNTS = """
    SELECT session_id,
        SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) AS reserved_count,
        SUM(CASE WHEN status = 'checked_in' THEN 1 ELSE 0 END) AS checked_in_count,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count,
        SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) AS no_show_count,
        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count
    FROM bookings GROUP BY session_id
"""

_SESSION_SELECT = """
    SELECT s.id AS session_id, s.starts_at, s.ends_at,
        COALESCE(b.reserved_count, 0) AS reserved_count,
        COALESCE(b.checked_in_count, 0) AS checked_in_count,
        COALESCE(b.completed_count, 0) AS completed_count,
        COALESCE(b.no_show_count, 0) AS no_show_count,
        COALESCE(b.cancelled_count, 0) AS cancelled_count
    FROM course_sessions s
    LEFT JOIN (""" + _SESSION_COUNTS + """) b ON b.session_id = s.id
"""

_COACH_SELECT = """
    SELECT c.id AS coach_id, c.name AS coach_name,
        COUNT(DISTINCT s.id) AS completed_sessions,
        COUNT(b.id) AS attended_members
    FROM coaches c
    LEFT JOIN course_sessions s ON s.coach_id = c.id AND s.status = 'completed'
        AND s.starts_at >= :window_start AND s.starts_at < :window_end
    LEFT JOIN bookings b ON b.session_id = s.id AND b.status = 'completed'
"""


class ReportRepository:
    """报表数据查询；只使用传入会话，不提交、不输出提示。

    聚合与分页使用当前快照；数据库异常转为 StorageError。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def _rows(self, sql: str, params: dict[str, Any]) -> list[Any]:
        try:
            result = self._session.execute(text(sql), params)
            try:
                return result.mappings().all()
            finally:
                result.close()
        except SQLAlchemyError as exc:
            raise StorageError("查询经营报表失败") from exc

    def revenue(self, window: DateWindow) -> RevenueView:
        """汇总时间范围内的实收，空数据返回零值。

        返回：按订单销售类型分类的实际付款金额。"""
        rows = self._rows(
            "SELECT o.kind AS sale_kind, COUNT(*) AS payment_count, "
            "SUM(p.amount) AS total_amount FROM payments p "
            "JOIN sale_orders o ON o.id = p.sale_order_id "
            "WHERE p.paid_at >= :window_start AND p.paid_at < :window_end "
            "GROUP BY o.kind",
            {"window_start": _utc_input(window.start),
             "window_end": _utc_input(window.end)},
        )
        indexed = {row["sale_kind"]: row for row in rows}
        breakdowns = []
        for kind in ("gym_card", "lesson_package"):
            row = indexed.get(kind)
            breakdowns.append(RevenueBreakdownView(
                sale_kind=kind,
                payment_count=int(row["payment_count"]) if row else 0,
                total_amount=(
                    Decimal(str(row["total_amount"])).quantize(Decimal("0.01"))
                    if row else Decimal("0.00")
                ),
            ))
        return RevenueView(
            window=window,
            total_payment_count=sum(item.payment_count for item in breakdowns),
            total_amount=sum((item.total_amount for item in breakdowns), Decimal("0.00")),
            breakdowns=tuple(breakdowns),
        )

    def membership_stats(
        self, as_of: datetime, *, business_date: date,
    ) -> MembershipStats:
        """统计当前快照；as_of 与门店 business_date 由服务传入，不回放历史。

        返回：当前快照下互斥的卡、课包分类及余额。"""
        params = {"business_date": business_date}
        members = self._rows("""
            SELECT
                COALESCE(SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END), 0)
                    AS active_member_profiles,
                COALESCE(SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END), 0)
                    AS archived_member_profiles
            FROM members
        """, {})[0]
        cards = self._rows("""
            SELECT
                COALESCE(SUM(CASE WHEN g.status = 'void' THEN 1 ELSE 0 END), 0)
                    AS void_gym_cards,
                COALESCE(SUM(CASE WHEN g.status = 'active' AND g.kind = 'duration'
                    AND d.valid_from <= :business_date AND d.valid_until > :business_date
                    THEN 1 ELSE 0 END), 0) AS valid_duration_gym_card_count,
                COALESCE(SUM(CASE WHEN g.status = 'active' AND g.kind = 'duration'
                    AND d.valid_from > :business_date THEN 1 ELSE 0 END), 0)
                    AS future_duration_gym_cards,
                COALESCE(SUM(CASE WHEN g.status = 'active' AND g.kind = 'duration'
                    AND d.valid_until <= :business_date THEN 1 ELSE 0 END), 0)
                    AS expired_duration_gym_cards,
                COALESCE(SUM(CASE WHEN g.status = 'active' AND g.kind = 'visit'
                    AND v.remaining_entries > 0 THEN 1 ELSE 0 END), 0)
                    AS usable_visit_gym_card_count,
                COALESCE(SUM(CASE WHEN g.status = 'active' AND g.kind = 'visit'
                    AND v.remaining_entries = 0 THEN 1 ELSE 0 END), 0)
                    AS exhausted_visit_gym_cards,
                COALESCE(SUM(CASE WHEN g.status = 'active' AND g.kind = 'visit'
                    THEN v.remaining_entries ELSE 0 END), 0) AS remaining_visit_entries,
                COUNT(DISTINCT CASE WHEN g.status = 'active' AND (
                    (g.kind = 'duration' AND d.valid_from <= :business_date
                        AND d.valid_until > :business_date)
                    OR (g.kind = 'visit' AND v.remaining_entries > 0)
                ) THEN g.member_id ELSE NULL END) AS members_with_gym_access
            FROM gym_cards g
            LEFT JOIN duration_gym_cards d ON d.gym_card_id = g.id
            LEFT JOIN visit_gym_cards v ON v.gym_card_id = g.id
        """, params)[0]
        # 先按状态和日期分类，再判断余额，防止未来/过期空课包重复计数。
        packages = self._rows("""
            SELECT
                COALESCE(SUM(CASE WHEN category = 'active' THEN 1 ELSE 0 END), 0)
                    AS active_lesson_package_count,
                COALESCE(SUM(CASE WHEN category = 'future' THEN 1 ELSE 0 END), 0)
                    AS future_lesson_packages,
                COALESCE(SUM(CASE WHEN category = 'expired' THEN 1 ELSE 0 END), 0)
                    AS expired_lesson_packages,
                COALESCE(SUM(CASE WHEN category = 'void' THEN 1 ELSE 0 END), 0)
                    AS void_lesson_packages,
                COALESCE(SUM(CASE WHEN category = 'exhausted' THEN 1 ELSE 0 END), 0)
                    AS exhausted_lesson_packages,
                COALESCE(SUM(CASE WHEN status = 'active' THEN remaining_lessons ELSE 0 END), 0)
                    AS remaining_lessons,
                COALESCE(SUM(CASE WHEN status = 'active' THEN reserved_lessons ELSE 0 END), 0)
                    AS reserved_lessons,
                COALESCE(SUM(CASE WHEN category IN ('active', 'exhausted')
                    THEN remaining_lessons - reserved_lessons ELSE 0 END), 0)
                    AS available_lessons
            FROM (
                SELECT status, remaining_lessons, reserved_lessons,
                    CASE
                        WHEN status = 'void' THEN 'void'
                        WHEN valid_from > :business_date THEN 'future'
                        WHEN valid_until IS NOT NULL AND valid_until <= :business_date
                            THEN 'expired'
                        WHEN remaining_lessons = 0 THEN 'exhausted'
                        ELSE 'active'
                    END AS category
                FROM lesson_packages
            ) classified
        """, params)[0]
        counts = {key: int(value) for row in (members, cards, packages)
                  for key, value in row.items()}
        return MembershipStats(as_of=as_of, business_date=business_date, **counts)

    def session_stats(self, query: SessionQuery, *, as_of: datetime) -> Page[SessionStatsView]:
        """应用 SessionQuery 的全部筛选字段，再按 starts_at、session_id 降序稳定分页。

        as_of 为服务固定的带时区统计时刻，用于判断课次是否已经结束。
        返回：分页内每个课次的预约状态数量与已结算到课率。"""
        where, params = _session_filters(query)
        total = self._rows(
            f"SELECT COUNT(*) AS total FROM course_sessions s WHERE {where}", params,
        )[0]["total"]
        rows = self._rows(
            _SESSION_SELECT + f" WHERE {where} "
            "ORDER BY s.starts_at DESC, s.id DESC LIMIT :limit OFFSET :offset",
            {**params, "limit": query.paging.page_size,
             "offset": (query.paging.page - 1) * query.paging.page_size},
        )
        return Page(
            items=self._session_views(rows, as_of=as_of), total=int(total),
            page=query.paging.page, page_size=query.paging.page_size,
        )

    def coach_stats(self, window: DateWindow, paging: PageRequest) -> Page[CoachStatsView]:
        """按 coach_id 升序稳定分页汇总各教练已完成课次与到课人次。

        返回：包含零业绩教练的稳定分页结果。"""
        total = self._rows("SELECT COUNT(*) AS total FROM coaches", {})[0]["total"]
        rows = self._rows(
            _COACH_SELECT + " GROUP BY c.id, c.name ORDER BY c.id ASC "
            "LIMIT :limit OFFSET :offset",
            {"window_start": _utc_input(window.start),
             "window_end": _utc_input(window.end), "limit": paging.page_size,
             "offset": (paging.page - 1) * paging.page_size},
        )
        return Page(
            items=[CoachStatsView(**row) for row in rows], total=int(total),
            page=paging.page, page_size=paging.page_size,
        )

    def _session_views(self, rows: list[Any], *, as_of: datetime) -> list[SessionStatsView]:
        views = []
        for row in rows:
            denominator = row["completed_count"] + row["no_show_count"]
            rate = None
            if (
                _utc_output(row["ends_at"]) <= as_of
                and row["reserved_count"] == 0 and row["checked_in_count"] == 0
                and denominator > 0
            ):
                rate = Decimal(row["completed_count"]) / Decimal(denominator)
            views.append(SessionStatsView(
                session_id=row["session_id"], starts_at=_utc_output(row["starts_at"]),
                reserved_count=int(row["reserved_count"]),
                checked_in_count=int(row["checked_in_count"]),
                completed_count=int(row["completed_count"]),
                no_show_count=int(row["no_show_count"]),
                cancelled_count=int(row["cancelled_count"]), attendance_rate=rate,
            ))
        return views

    def session_stats_batch(
        self, query: SessionQuery, *, as_of: datetime, after_id: int = 0, limit: int = 500,
    ) -> list[SessionStatsView]:
        """按课次主键游标读取导出批次；所有批次复用服务传入的 as_of 和筛选。"""
        where, params = _session_filters(query)
        return self._session_views(self._rows(
            _SESSION_SELECT + f" WHERE {where} AND s.id > :after_id "
            "ORDER BY s.id ASC LIMIT :limit",
            {**params, "after_id": after_id, "limit": limit},
        ), as_of=as_of)

    def coach_stats_batch(
        self, window: DateWindow, *, after_id: int = 0, limit: int = 500,
    ) -> list[CoachStatsView]:
        """按教练主键游标读取汇总批次，复用当前读取快照。"""
        rows = self._rows(
            _COACH_SELECT + " WHERE c.id > :after_id GROUP BY c.id, c.name "
            "ORDER BY c.id ASC LIMIT :limit",
            {"window_start": _utc_input(window.start),
             "window_end": _utc_input(window.end),
             "after_id": after_id, "limit": limit},
        )
        return [CoachStatsView(**row) for row in rows]
