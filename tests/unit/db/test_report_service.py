"""报表权限、列表结构、游标导出和资源生命周期。"""

import csv
import io
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.db.payment_repo import PaymentRepository
from src.errors import AuthenticationError, InvalidInputError, NotFoundError, PermissionDenied, StorageError
from src.errors.business import ResourceError
from src.logic.report_logic import ReportLogic
from src.models.contracts import Actor, DateWindow, MembershipStats, PageRequest, PaymentQuery, SessionQuery
from src.models.payment import Payment
from src.services.report_service import ReportService


ADMIN = Actor(account_id=1, role="admin", member_id=None, coach_id=None)
FRONT = replace(ADMIN, role="receptionist")
MEMBER = replace(ADMIN, role="member", member_id=8)
COACH = replace(ADMIN, role="coach", coach_id=9)
START = datetime(2026, 10, 20, tzinfo=timezone.utc)
WINDOW = DateWindow(start=START, end=START + timedelta(days=1))


@pytest.fixture
def service():
    auth = Mock()
    auth.verify_actor.side_effect = lambda session, actor: actor
    return ReportService(auth, timezone_name="Asia/Shanghai")


def csv_rows(export):
    assert export.content.startswith(b"\xef\xbb\xbf")
    return list(csv.reader(io.StringIO(export.content.decode("utf-8-sig"))))


@pytest.mark.parametrize("actor", [MEMBER, COACH])
def test_private_roles_cannot_query_payments_or_reports(service, report_db, actor):
    with pytest.raises(PermissionDenied):
        service.list_payments(report_db, actor, PaymentQuery())
    with pytest.raises(PermissionDenied):
        service.revenue(report_db, actor, WINDOW)


def test_front_desk_can_query_payment_views_but_not_export(service, report_db):
    payment = PaymentRepository(report_db).create(7, 8, Decimal("12.30"), "cash", START, 1)
    result = service.list_payments(report_db, FRONT, PaymentQuery())
    assert (result.total, result.items[0].sale_order_id, result.items[0].amount) == (1, 7, Decimal("12.30"))
    assert service.get_payment(report_db, FRONT, payment.id) == result.items[0]
    assert service._auth.verify_actor.call_count == 2
    assert not hasattr(result.items[0], "membership_id")
    with pytest.raises(PermissionDenied):
        service.export_payments(report_db, FRONT, PaymentQuery())
    with pytest.raises(NotFoundError):
        service.get_payment(report_db, ADMIN, 999)


def test_authentication_failure_is_preserved(service, report_db):
    service._auth.verify_actor.side_effect = AuthenticationError("账号失效")
    with pytest.raises(AuthenticationError):
        service.export_payments(report_db, ADMIN, PaymentQuery())


@pytest.mark.parametrize("query", [
    PaymentQuery(member_id=True), PaymentQuery(member_id=2**63),
    PaymentQuery(method="cash' OR 1=1"),
    PaymentQuery(paging=PageRequest(page=True)),
    PaymentQuery(paging=PageRequest(page_size=101)),
    PaymentQuery(paging=PageRequest(page=2**63)),
    PaymentQuery(window=DateWindow(start=START, end=START)),
    PaymentQuery(window=DateWindow(start=START.replace(tzinfo=None), end=WINDOW.end)),
    PaymentQuery(window=DateWindow(start=datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=8))), end=WINDOW.end)),
])
def test_invalid_payment_queries_are_project_errors(service, report_db, query):
    with pytest.raises(InvalidInputError):
        service.list_payments(report_db, ADMIN, query)


def test_fall_back_window_uses_utc_order_and_half_open_bounds(service, report_db):
    zone = ZoneInfo("America/New_York")
    window = DateWindow(
        start=datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0),
        end=datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1),
    )
    repository = PaymentRepository(report_db)
    included = repository.create(
        1, 8, Decimal("12.30"), "cash", datetime(2026, 11, 1, 6, tzinfo=timezone.utc), 1,
    )
    repository.create(2, 8, Decimal("20.00"), "cash", window.end, 1)
    result = service.list_payments(report_db, ADMIN, PaymentQuery(window=window))
    assert result.total == 1
    assert [item.id for item in result.items] == [included.id]


def test_fall_back_window_rejects_utc_reverse_order(service, report_db):
    zone = ZoneInfo("America/New_York")
    window = DateWindow(
        start=datetime(2026, 11, 1, 1, 15, tzinfo=zone, fold=1),
        end=datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0),
    )
    with pytest.raises(InvalidInputError, match="开始时间必须早于结束时间"):
        service.list_payments(report_db, ADMIN, PaymentQuery(window=window))


@pytest.mark.parametrize("query", [SessionQuery(kind="group"), SessionQuery(coach_id=False),
                                         SessionQuery(room_id=-1), SessionQuery(status="deleted")])
def test_invalid_session_filters_are_project_errors(service, report_db, query):
    with pytest.raises(InvalidInputError):
        service.session_stats(report_db, ADMIN, query)


def test_all_empty_exports_keep_headers(service, report_db):
    exports = [
        service.export_payments(report_db, ADMIN, PaymentQuery()),
        service.export_revenue(report_db, ADMIN, WINDOW),
        service.export_memberships(report_db, ADMIN),
        service.export_sessions(report_db, ADMIN, SessionQuery()),
        service.export_coaches(report_db, ADMIN, WINDOW),
    ]
    for export in exports:
        assert export.row_count == 0
        assert len(csv_rows(export)) == 1
    assert csv_rows(exports[2])[0] == [field.name for field in fields(MembershipStats)]


def test_payment_export_uses_all_filtered_rows_ignoring_ui_page(service, report_db):
    repo = PaymentRepository(report_db)
    for order in range(1, 505):
        repo.create(order, 8, Decimal("0.10"), "cash", START, 1)
    repo.create(505, 8, Decimal("90.00"), "card", START, 1)
    export = service.export_payments(report_db, ADMIN, PaymentQuery(
        method="cash", paging=PageRequest(page=2, page_size=1),
    ))
    rows = csv_rows(export)
    assert export.row_count == 504
    assert len(rows) == 505
    assert [int(row[0]) for row in rows[1:]] == list(range(1, 505))
    assert all(row[4] == "cash" for row in rows[1:])


@pytest.mark.parametrize("count", [10_000, 10_001])
def test_export_limit_is_exact_and_never_truncates(service, report_db, monkeypatch, count):
    def batch(repository, query, *, after_id=0, limit=500):
        return [Payment(id=index, sale_order_id=index, member_id=8, amount=Decimal("1.00"),
                        method="cash", paid_at=START, operator_id=1, created_at=START)
                for index in range(after_id + 1, min(count + 1, after_id + limit + 1))]
    monkeypatch.setattr(PaymentRepository, "list_batch", batch)
    if count == 10_001:
        with pytest.raises(InvalidInputError, match="10000"):
            service.export_payments(report_db, ADMIN, PaymentQuery())
    else:
        result = service.export_payments(report_db, ADMIN, PaymentQuery())
        assert result.row_count == 10_000
        assert csv_rows(result)[-1][0] == "10000"


def test_csv_handles_formulas_unicode_missing_values_and_negative_numbers(service, report_db):
    report_db.execute(text("INSERT INTO coaches VALUES (1, ' =SUM(1,2)'), (2, '@危险教练')"))
    export = service.export_coaches(report_db, ADMIN, WINDOW)
    rows = csv_rows(export)
    assert [row[1] for row in rows[1:]] == ["' =SUM(1,2)", "'@危险教练"]
    assert csv_rows(service._csv("x.csv", ["number", "missing"], [[Decimal("-2.50"), None]]))[1] == ["-2.50", ""]
    with pytest.raises(ResourceError):
        service._csv("x.csv", ["text"], [["\ud800"]])


def test_current_membership_export_generates_its_own_utc_time(service, report_db):
    report_db.execute(text("INSERT INTO members VALUES (1, 'active')"))
    before = datetime.now(timezone.utc)
    export = ReportLogic(lambda: report_db, service).export_memberships(ADMIN)
    row = csv_rows(export)[1]
    stamp = datetime.fromisoformat(row[0])
    assert before <= stamp <= datetime.now(timezone.utc)
    assert row[1] == stamp.astimezone(service._zone).date().isoformat()


def test_session_export_keeps_one_time_across_batches(service, report_db, monkeypatch):
    report_db.execute(text("""
        INSERT INTO course_sessions VALUES
        (1, 'private', 1, 1, '2026-10-20 10:00:00', '2026-10-20 11:00:00', 'completed'),
        (2, 'private', 1, 1, '2026-10-20 10:00:00', '2026-10-20 11:00:00', 'completed')
    """))
    report_db.execute(text("INSERT INTO bookings VALUES (1, 1, 'completed'), (2, 2, 'completed')"))
    before_end = datetime(2026, 10, 20, 10, 59, 59, tzinfo=timezone.utc)

    class AdvancingClock(datetime):
        reads = 0

        @classmethod
        def now(cls, tz):
            current = before_end + timedelta(seconds=2 * cls.reads)
            cls.reads += 1
            return current.astimezone(tz)

    monkeypatch.setattr("src.services.report_service.datetime", AdvancingClock)
    monkeypatch.setattr("src.services.report_service._BATCH_SIZE", 1)
    export = service.export_sessions(report_db, ADMIN, SessionQuery())
    rows = csv_rows(export)
    assert export.row_count == 2
    assert [row[0] for row in rows[1:]] == ["1", "2"]
    assert [row[-1] for row in rows[1:]] == ["", ""]
    assert AdvancingClock.reads == 1


def test_export_snapshot_failure_uses_resource_error(service, report_db, monkeypatch):
    def fail(*args, **kwargs):
        raise StorageError("数据库失败")
    monkeypatch.setattr(PaymentRepository, "list_batch", fail)
    with pytest.raises(ResourceError, match="快照"):
        service.export_payments(report_db, ADMIN, PaymentQuery())


@pytest.mark.parametrize("fail", [False, True])
def test_read_logic_closes_and_rolls_back_on_all_exits(fail):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE changes (id INTEGER)"))
    class TrackedSession(Session):
        closed = False
        def close(self):
            self.closed = True
            super().close()
    session = TrackedSession(engine)
    def read(current, actor, query):
        current.execute(text("INSERT INTO changes VALUES (1)"))
        if fail:
            raise PermissionDenied("拒绝")
        return "result"
    logic = ReportLogic(lambda: session, SimpleNamespace(list_payments=read))
    if fail:
        with pytest.raises(PermissionDenied):
            logic.list_payments(ADMIN, PaymentQuery())
    else:
        assert logic.list_payments(ADMIN, PaymentQuery()) == "result"
    assert session.closed
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM changes")).scalar_one() == 0
    engine.dispose()


def test_export_logic_maps_session_factory_failure():
    def fail():
        raise StorageError("连接失败")
    logic = ReportLogic(fail, Mock())
    with pytest.raises(ResourceError):
        logic.export_payments(ADMIN, PaymentQuery())
