"""REPORT-01～04：实际 SQL 的分类、分页与课次口径。"""

from dataclasses import fields
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from src.db.payment_repo import PaymentRepository
from src.db.report_repo import ReportRepository
from src.errors.storage import StorageError
from src.models.contracts import DateWindow, PageRequest, SessionQuery


START = datetime(2026, 10, 20, tzinfo=timezone.utc)
WINDOW = DateWindow(start=START, end=START + timedelta(days=1))
TODAY = date(2026, 10, 21)


def test_empty_reports_have_stable_decimal_and_zero_fields(report_db):
    repo = ReportRepository(report_db)
    revenue = repo.revenue(WINDOW)
    assert revenue.total_payment_count == 0
    assert revenue.total_amount == Decimal("0.00")
    assert [(row.sale_kind, row.payment_count, row.total_amount) for row in revenue.breakdowns] == [
        ("gym_card", 0, Decimal("0.00")), ("lesson_package", 0, Decimal("0.00")),
    ]
    stats = repo.membership_stats(START, business_date=TODAY)
    assert all(getattr(stats, field.name) == 0 for field in fields(stats)
               if field.name not in {"as_of", "business_date"})
    assert repo.session_stats(SessionQuery()).total == 0
    assert repo.coach_stats(WINDOW, PageRequest()).items == []


def test_revenue_classifies_actual_payments_once_with_half_open_window(report_db):
    report_db.execute(text(
        "INSERT INTO sale_orders (id, kind) VALUES (1, 'lesson_package'), (2, 'gym_card'), "
        "(3, 'lesson_package')"
    ))
    payments = PaymentRepository(report_db)
    for order, amount, at in ((1, "100.10", START), (2, "0.20", START), (3, "900.00", WINDOW.end)):
        payments.create(order, 1, Decimal(amount), "cash", at, 1)
    revenue = ReportRepository(report_db).revenue(WINDOW)
    assert revenue.total_payment_count == 2
    assert revenue.total_amount == Decimal("100.30")
    assert [row.total_amount for row in revenue.breakdowns] == [Decimal("0.20"), Decimal("100.10")]
    # 无销售项目/赠卡连接也可统计，订单包含多项权益不会扩大付款行数。
    assert sum(row.payment_count for row in revenue.breakdowns) == 2


def test_membership_classification_is_exclusive_and_access_is_distinct(report_db):
    report_db.execute(text("INSERT INTO members VALUES (1, 'active'), (2, 'active'), (3, 'archived')"))
    report_db.execute(text("""
        INSERT INTO gym_cards VALUES
        (1, 1, 'duration', 'active'), (2, 1, 'duration', 'active'),
        (3, 2, 'duration', 'active'), (4, 2, 'duration', 'void'),
        (5, 1, 'visit', 'active'), (6, 2, 'visit', 'active'),
        (7, 2, 'visit', 'void'), (8, 3, 'visit', 'active')
    """))
    report_db.execute(text("""
        INSERT INTO duration_gym_cards VALUES
        (1, '2026-10-01', '2026-10-22'), (2, '2026-10-22', '2026-10-25'),
        (3, '2026-10-01', '2026-10-21'), (4, '2026-10-22', '2026-10-25')
    """))
    report_db.execute(text("INSERT INTO visit_gym_cards VALUES (5, 3), (6, 0), (7, 8), (8, 2)"))
    report_db.execute(text("""
        INSERT INTO lesson_packages VALUES
        (1, 'active', '2026-10-01', NULL, 5, 2),
        (2, 'active', '2026-10-22', NULL, 0, 0),
        (3, 'active', '2026-10-01', '2026-10-21', 0, 0),
        (4, 'void', '2026-10-22', NULL, 7, 2),
        (5, 'active', '2026-10-01', NULL, 0, 0),
        (6, 'active', '2026-10-01', NULL, 4, 4),
        (7, 'active', '2026-10-22', NULL, 10, 1),
        (8, 'active', '2026-10-01', '2026-10-21', 6, 1)
    """))
    stats = ReportRepository(report_db).membership_stats(START, business_date=TODAY)
    assert (stats.active_member_profiles, stats.archived_member_profiles) == (2, 1)
    assert (stats.valid_duration_gym_card_count, stats.future_duration_gym_cards,
            stats.expired_duration_gym_cards) == (1, 1, 1)
    assert (stats.usable_visit_gym_card_count, stats.exhausted_visit_gym_cards,
            stats.void_gym_cards, stats.remaining_visit_entries) == (2, 1, 2, 5)
    assert stats.members_with_gym_access == 2
    assert (stats.active_lesson_package_count, stats.future_lesson_packages,
            stats.expired_lesson_packages, stats.void_lesson_packages,
            stats.exhausted_lesson_packages) == (2, 2, 2, 1, 1)
    assert (stats.remaining_lessons, stats.reserved_lessons, stats.available_lessons) == (25, 8, 3)


def seed_sessions(session):
    session.execute(text("INSERT INTO coaches VALUES (1, 'First'), (2, 'Second'), (3, 'Empty')"))
    session.execute(text("""
        INSERT INTO course_sessions VALUES
        (1, 'private', 1, 1, '2026-10-20 10:00:00', '2026-10-20 11:00:00', 'completed'),
        (2, 'private', 1, 2, '2026-10-20 10:00:00', '2026-10-20 11:00:00', 'scheduled'),
        (3, 'private', 2, 1, '2026-10-21 00:00:00', '2026-10-21 01:00:00', 'completed'),
        (4, 'private', 2, 1, '2026-10-20 13:00:00', '2026-10-20 14:00:00', 'completed'),
        (5, 'private', 2, 1, '2026-10-22 00:00:00', '2026-10-22 01:00:00', 'scheduled')
    """))
    session.execute(text("""
        INSERT INTO bookings VALUES
        (1, 1, 'completed'), (2, 1, 'completed'), (3, 1, 'no_show'), (4, 1, 'cancelled'),
        (5, 2, 'checked_in'), (6, 2, 'completed'), (7, 2, 'reserved'),
        (8, 3, 'completed'), (9, 5, 'completed')
    """))


def test_session_counts_rate_and_stable_pagination(report_db):
    seed_sessions(report_db)
    repo = ReportRepository(report_db)
    page = repo.session_stats(SessionQuery(window=WINDOW, paging=PageRequest(page_size=2)))
    assert page.total == 3
    assert [row.session_id for row in page.items] == [4, 2]
    assert all(row.attendance_rate is None for row in page.items)
    second_page = repo.session_stats(SessionQuery(
        window=WINDOW, paging=PageRequest(page=2, page_size=2),
    ))
    row = second_page.items[0]
    assert row.session_id == 1
    assert (row.completed_count, row.no_show_count, row.cancelled_count) == (2, 1, 1)
    assert row.attendance_rate == Decimal(2) / Decimal(3)
    assert row.starts_at.tzinfo == timezone.utc


@pytest.mark.parametrize("query, expected", [
    (SessionQuery(coach_id=1), [2, 1]),
    (SessionQuery(room_id=2), [2]),
    (SessionQuery(status="completed", window=WINDOW), [4, 1]),
    (SessionQuery(kind="private", coach_id=2, room_id=1, status="completed", window=WINDOW), [4]),
])
def test_session_query_filters_count_and_data_together(report_db, query, expected):
    seed_sessions(report_db)
    page = ReportRepository(report_db).session_stats(query)
    assert page.total == len(expected)
    assert [row.session_id for row in page.items] == expected


def test_session_batch_ignores_ui_page_and_retains_snapshot_time(report_db):
    seed_sessions(report_db)
    repo = ReportRepository(report_db)
    query = SessionQuery(window=WINDOW, paging=PageRequest(page=100, page_size=1))
    assert [row.session_id for row in repo.session_stats_batch(query, limit=2)] == [1, 2]
    assert [row.session_id for row in repo.session_stats_batch(query, after_id=2)] == [4]
    future = repo.session_stats_batch(SessionQuery(), after_id=4)
    assert future[0].attendance_rate is None
    report_db.info["report_as_of"] = datetime(2026, 10, 20, 11, tzinfo=timezone.utc)
    assert repo.session_stats_batch(query, limit=1)[0].attendance_rate == Decimal(2) / Decimal(3)
    report_db.info["report_as_of"] -= timedelta(microseconds=1)
    assert repo.session_stats_batch(query, limit=1)[0].attendance_rate is None


def test_coach_aggregation_counts_distinct_completed_sessions_and_completed_bookings(report_db):
    seed_sessions(report_db)
    repo = ReportRepository(report_db)
    page = repo.coach_stats(WINDOW, PageRequest(page_size=2))
    assert page.total == 3
    assert [(row.coach_id, row.completed_sessions, row.attended_members) for row in page.items] == [
        (1, 1, 2), (2, 1, 0),
    ]
    page2 = repo.coach_stats(WINDOW, PageRequest(page=2, page_size=2))
    assert [(row.coach_id, row.completed_sessions, row.attended_members) for row in page2.items] == [
        (3, 0, 0),
    ]
    assert [row.coach_id for row in repo.coach_stats_batch(WINDOW, after_id=1, limit=1)] == [2]
    assert [row.coach_id for row in repo.coach_stats_batch(WINDOW, after_id=2)] == [3]


def test_storage_errors_are_converted_to_safe_business_storage_error(report_db):
    report_db.execute(text("DROP TABLE payments"))
    with pytest.raises(StorageError, match="查询经营报表失败"):
        ReportRepository(report_db).revenue(WINDOW)
