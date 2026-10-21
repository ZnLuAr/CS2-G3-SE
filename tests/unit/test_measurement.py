"""体测边界、授权 SQL 和事务；SQLite 验证查询语义，行锁由 MySQL 集成验证。"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table, create_engine, select
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.db.booking_repo import BookingRepository
from src.db.measurement_repo import MeasurementRepository
from src.db.member_repo import MemberRepository
from src.errors import InvalidInputError, InvalidState, NotFoundError, OutcomeUnknownError, PermissionDenied, StorageError
from src.logic.measurement_logic import MeasurementLogic
from src.models.contracts import Actor, DateWindow, MeasurementInput, MeasurementQuery, PageRequest
from src.services.measurement_service import MeasurementService


NOW = datetime(2026, 10, 21, 8, 0, tzinfo=timezone.utc)
COACH = Actor(account_id=2, role="coach", member_id=None, coach_id=20)
MEMBER = Actor(account_id=1, role="member", member_id=10, coach_id=None)


def stored(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def measurement(**changes):
    return replace(MeasurementInput(
        member_id=10, measured_at=NOW - timedelta(days=1), height_cm=Decimal("170.00"),
        weight_kg=Decimal("60.00"), body_fat_pct=Decimal("20.00"),
    ), **changes)


@pytest.fixture
def db():
    metadata = MetaData()
    members = Table("members", metadata,
        Column("id", Integer, primary_key=True), Column("name", String), Column("phone", String),
        Column("status", String), Column("archived_at", DateTime),
        Column("created_at", DateTime), Column("updated_at", DateTime),
    )
    sessions = Table("course_sessions", metadata,
        Column("id", Integer, primary_key=True), Column("coach_id", Integer),
        Column("status", String), Column("ends_at", DateTime),
    )
    bookings = Table("bookings", metadata,
        Column("id", Integer, primary_key=True), Column("member_id", Integer),
        Column("session_id", Integer), Column("status", String),
        Column("booked_at", DateTime), Column("closed_at", DateTime),
    )
    measurements = Table("body_measurements", metadata,
        Column("id", Integer, primary_key=True), Column("member_id", Integer), Column("coach_id", Integer),
        Column("measured_at", DateTime), Column("created_at", DateTime),
        Column("height_cm", Numeric(6, 2)), Column("weight_kg", Numeric(6, 2)),
        Column("body_fat_pct", Numeric(5, 2)),
    )
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    with Session(engine) as session:
        session.execute(members.insert(), [{
            "id": member_id, "name": "Member", "phone": None, "status": "active", "archived_at": None,
            "created_at": stored(NOW), "updated_at": stored(NOW),
        } for member_id in (10, 11)])
        session.execute(sessions.insert(), {
            "id": 30, "coach_id": 20, "status": "scheduled", "ends_at": stored(NOW + timedelta(hours=1)),
        })
        session.execute(bookings.insert(), {
            "id": 40, "member_id": 10, "session_id": 30, "status": "reserved",
            "booked_at": stored(NOW - timedelta(days=2)), "closed_at": None,
        })
        session.commit()
        yield SimpleNamespace(
            engine=engine, session=session, members=members, sessions=sessions,
            bookings=bookings, measurements=measurements,
        )
    engine.dispose()


@pytest.fixture
def service(monkeypatch):
    class ClockMeta(type):
        def __instancecheck__(cls, value):
            return isinstance(value, datetime)

    class Clock(datetime, metaclass=ClockMeta):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else stored(NOW)

    monkeypatch.setattr("src.services.measurement_service.datetime", Clock)
    auth = SimpleNamespace(verify_actor=lambda session, actor: actor)
    return MeasurementService(auth)


def add(db, *, created_at=NOW, measured_at=None, member_id=10, coach_id=20):
    return MeasurementRepository(db.session).create(
        measurement(member_id=member_id, measured_at=measured_at or created_at), coach_id,
        created_at=created_at,
    )


def test_record_current_booking_and_numeric_boundaries(db, service):
    result = service.record(db.session, COACH, measurement(
        measured_at=NOW, height_cm=Decimal("100.00"), weight_kg=Decimal("150.00"), body_fat_pct=Decimal("0"),
    ))
    assert result.created_at == NOW
    assert result.measured_at == NOW
    assert result.height_cm == Decimal("100.00")
    assert result.weight_kg == Decimal("150.00")
    assert result.body_fat_pct == Decimal("0.00")
    assert db.session.in_transaction()
    db.session.rollback()
    assert db.session.scalar(select(db.measurements.c.id)) is None


@pytest.mark.parametrize("changes", [
    {"height_cm": Decimal("99.99")}, {"height_cm": Decimal("250.01")},
    {"weight_kg": Decimal("29.99")}, {"weight_kg": Decimal("150.01")},
    {"body_fat_pct": Decimal("100.01")}, {"body_fat_pct": Decimal("-0.01")},
    {"height_cm": Decimal("NaN")}, {"weight_kg": Decimal("Infinity")},
    {"height_cm": True}, {"member_id": True}, {"member_id": 0},
    {"measured_at": NOW.replace(tzinfo=None)}, {"measured_at": NOW + timedelta(microseconds=1)},
])
def test_invalid_record_does_not_insert(db, service, changes):
    with pytest.raises(InvalidInputError):
        service.record(db.session, COACH, measurement(**changes))
    assert db.session.scalar(select(db.measurements.c.id)) is None


def test_record_quantizes_and_normalizes_timezone(db, service):
    result = service.record(db.session, COACH, measurement(
        height_cm=Decimal("170.005"), body_fat_pct=None,
        measured_at=NOW.astimezone(timezone(timedelta(hours=8))),
    ))
    assert result.height_cm == Decimal("170.01")
    assert result.measured_at == NOW
    assert result.body_fat_pct is None


@pytest.mark.parametrize("booking_status,session_status,ends_delta,closed_delta", [
    ("cancelled", "scheduled", 1, -1), ("completed", "scheduled", 1, -1),
    ("no_show", "scheduled", 1, -1), ("reserved", "cancelled", 1, None),
    ("reserved", "scheduled", 0, None), ("reserved", "scheduled", -1, None),
])
def test_record_requires_current_booking(db, service, booking_status, session_status, ends_delta, closed_delta):
    db.session.execute(db.bookings.update().values(
        status=booking_status, closed_at=None if closed_delta is None else stored(NOW + timedelta(hours=closed_delta)),
    ))
    db.session.execute(db.sessions.update().values(
        status=session_status, ends_at=stored(NOW + timedelta(hours=ends_delta)),
    ))
    with pytest.raises(PermissionDenied):
        service.record(db.session, COACH, measurement())


def test_record_checks_verified_actor_and_archived_member(db, service):
    service._auth = SimpleNamespace(verify_actor=lambda session, actor: MEMBER)
    with pytest.raises(PermissionDenied):
        service.record(db.session, COACH, measurement())
    service._auth = SimpleNamespace(verify_actor=lambda session, actor: actor)
    db.session.execute(db.members.update().where(db.members.c.id == 10).values(status="archived"))
    with pytest.raises(InvalidState):
        service.record(db.session, COACH, measurement())


def test_member_scope_is_applied_to_detail_and_query(db, service):
    own, other = add(db), add(db, member_id=11)
    assert service.get_measurement(db.session, MEMBER, own.id) == own
    with pytest.raises(NotFoundError):
        service.get_measurement(db.session, MEMBER, other.id)
    with pytest.raises(PermissionDenied):
        service.list_measurements(db.session, MEMBER, MeasurementQuery(member_id=11))


@pytest.mark.parametrize("role", ["admin", "receptionist"])
def test_staff_cannot_read_detail_list_or_comparison(db, service, role):
    actor = Actor(account_id=99, role=role, member_id=None, coach_id=None)
    for method, args in [
        (service.get_measurement, (1,)),
        (service.list_measurements, (MeasurementQuery(member_id=10),)),
        (service.compare, (1, 2)),
    ]:
        with pytest.raises(PermissionDenied):
            method(db.session, actor, *args)


def test_coach_cancel_cutoff_uses_created_at_for_detail_and_total(db, service):
    cutoff = NOW - timedelta(hours=1)
    db.session.execute(db.bookings.update().values(status="cancelled", closed_at=stored(cutoff)))
    visible = add(db, created_at=cutoff, measured_at=NOW - timedelta(days=1))
    hidden = add(db, created_at=cutoff + timedelta(microseconds=1), measured_at=NOW - timedelta(days=2))
    page = service.list_measurements(db.session, COACH, MeasurementQuery(member_id=10))
    assert page.total == 1
    assert [item.id for item in page.items] == [visible.id]
    with pytest.raises(NotFoundError):
        service.get_measurement(db.session, COACH, hidden.id)
    with pytest.raises(NotFoundError):
        service.compare(db.session, COACH, hidden.id, visible.id)


def test_coach_session_end_cutoff_and_rebooking_restore_history(db, service):
    cutoff = NOW - timedelta(hours=1)
    db.session.execute(db.sessions.update().values(ends_at=stored(cutoff), status="completed"))
    visible = add(db, created_at=cutoff)
    hidden = add(db, created_at=cutoff + timedelta(microseconds=1))
    future = add(db, created_at=NOW + timedelta(microseconds=1))
    page = service.list_measurements(db.session, COACH, MeasurementQuery(member_id=10))
    assert [item.id for item in page.items] == [visible.id]
    db.session.execute(db.sessions.insert(), {
        "id": 31, "coach_id": 20, "status": "scheduled", "ends_at": stored(NOW + timedelta(days=2)),
    })
    db.session.execute(db.bookings.insert(), {
        "id": 41, "member_id": 10, "session_id": 31, "status": "reserved",
        "booked_at": stored(NOW), "closed_at": None,
    })
    page = service.list_measurements(db.session, COACH, MeasurementQuery(member_id=10))
    assert {item.id for item in page.items} == {visible.id, hidden.id}
    assert future.id not in {item.id for item in page.items}


def test_coach_without_history_gets_empty_page_and_future_booking_cannot_grant_access(db, service):
    add(db)
    db.session.execute(db.bookings.update().values(booked_at=stored(NOW + timedelta(days=1))))
    page = service.list_measurements(db.session, COACH, MeasurementQuery(member_id=10))
    assert page.items == [] and page.total == 0
    page = service.list_measurements(db.session, COACH, MeasurementQuery(member_id=11))
    assert page.items == [] and page.total == 0


def test_paging_and_half_open_window_share_total(db, service):
    start = NOW - timedelta(days=3)
    first, second = add(db, measured_at=start), add(db, measured_at=start)
    add(db, measured_at=NOW)
    query = MeasurementQuery(
        member_id=10, window=DateWindow(start=start, end=NOW),
        paging=PageRequest(page=1, page_size=1),
    )
    page = service.list_measurements(db.session, MEMBER, query)
    assert page.total == 2 and page.items[0].id == second.id
    page = service.list_measurements(db.session, MEMBER, replace(query, paging=PageRequest(page=2, page_size=1)))
    assert page.total == 2 and page.items[0].id == first.id


@pytest.mark.parametrize("paging", [PageRequest(page=0), PageRequest(page=True), PageRequest(page_size=0), PageRequest(page_size=101)])
def test_invalid_paging(db, service, paging):
    with pytest.raises(InvalidInputError):
        service.list_measurements(db.session, MEMBER, MeasurementQuery(member_id=10, paging=paging))


@pytest.mark.parametrize("paging", [
    PageRequest(page=10**100, page_size=100),
    PageRequest(page=2**63, page_size=1),
    PageRequest(page=2**63 - 1, page_size=2),
])
def test_paging_overflow_is_rejected_before_database_access(service, paging):
    session = Mock()
    with pytest.raises(InvalidInputError):
        service.list_measurements(session, MEMBER, MeasurementQuery(member_id=10, paging=paging))
    session.execute.assert_not_called()


def test_largest_supported_page_offset_returns_empty_page(db, service):
    page = service.list_measurements(db.session, MEMBER, MeasurementQuery(
        member_id=10, paging=PageRequest(page=2**63 - 1, page_size=1),
    ))
    assert page.items == [] and page.total == 0
    assert page.page == 2**63 - 1


@pytest.mark.parametrize("measured_at", [
    datetime(999, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    datetime(1000, 1, 1, tzinfo=timezone(timedelta(hours=8))),
    datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=8))),
    datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone(timedelta(hours=-8))),
])
def test_record_time_outside_database_range_does_not_insert(db, service, measured_at):
    with pytest.raises(InvalidInputError, match="数据库可用范围"):
        service.record(db.session, COACH, measurement(measured_at=measured_at))
    assert db.session.scalar(select(db.measurements.c.id)) is None


@pytest.mark.parametrize("window", [
    DateWindow(
        start=datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=8))), end=NOW,
    ),
    DateWindow(
        start=datetime(1000, 1, 1, tzinfo=timezone(timedelta(hours=8))), end=NOW,
    ),
    DateWindow(
        start=NOW,
        end=datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone(timedelta(hours=-8))),
    ),
])
def test_query_time_outside_database_range_is_rejected_before_sql(service, window):
    session = Mock()
    with pytest.raises(InvalidInputError, match="数据库可用范围"):
        service.list_measurements(session, MEMBER, MeasurementQuery(member_id=10, window=window))
    session.execute.assert_not_called()


def test_database_time_lower_boundary_is_valid_after_utc_conversion(db, service):
    measured_at = datetime(1000, 1, 1, 8, tzinfo=timezone(timedelta(hours=8)))
    result = service.record(db.session, COACH, measurement(measured_at=measured_at))
    assert result.measured_at == datetime(1000, 1, 1, tzinfo=timezone.utc)
    page = service.list_measurements(db.session, MEMBER, MeasurementQuery(
        member_id=10,
        window=DateWindow(start=measured_at, end=measured_at + timedelta(seconds=1)),
    ))
    assert page.total == 1 and page.items[0].id == result.id


def test_comparison_stable_order_and_optional_fat(db, service):
    first = add(db)
    second = MeasurementRepository(db.session).create(measurement(body_fat_pct=None), 20, created_at=NOW)
    # 测量时刻相同，编号决定比较和列表共用的稳定先后顺序。
    db.session.execute(db.measurements.update().where(db.measurements.c.id == second.id).values(measured_at=stored(NOW)))
    result = service.compare(db.session, MEMBER, first.id, second.id)
    assert result.body_fat_delta_pct is None
    assert result.height_delta_cm == 0
    for before, after in [(first.id, first.id), (second.id, first.id)]:
        with pytest.raises(InvalidInputError):
            service.compare(db.session, MEMBER, before, after)


def test_repository_rejects_ambiguous_scope(db):
    repo = MeasurementRepository(db.session)
    for member, coach in [(None, None), (10, 20)]:
        with pytest.raises(ValueError):
            repo.get(1, scope_member_id=member, scope_coach_id=coach, as_of=NOW)


def test_dependent_repositories_emit_mysql_locking_current_reads():
    session = Mock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    assert MemberRepository(session).lock(10) is None
    member_statement = session.execute.call_args.args[0]
    assert "FOR UPDATE" in str(member_statement.compile(dialect=mysql.dialect()))
    session.execute.return_value.first.return_value = None
    assert not BookingRepository(session).has_current_coaching_booking(10, 20, at=NOW)
    booking_statement = session.execute.call_args.args[0]
    assert "FOR UPDATE" in str(booking_statement.compile(dialect=mysql.dialect()))


def test_logic_commits_success_and_logs_only_identifiers(db, service, monkeypatch):
    events = []
    monkeypatch.setattr("src.logic.measurement_logic.log_event", lambda *args, **kwargs: events.append(kwargs))
    logic = MeasurementLogic(lambda: Session(db.engine), service)
    result = logic.record(COACH, measurement())
    assert db.session.scalar(select(db.measurements.c.id)) == result.id
    assert events == [{"operation": "measurement.record", "outcome": "success", "actor_id": 2, "result_id": result.id}]


def test_logic_rolls_back_and_closes_after_service_failure(db):
    sessions = []

    def factory():
        session = Session(db.engine)
        sessions.append(session)
        return session

    def fail(session, actor, data):
        MeasurementRepository(session).create(data, 20, created_at=NOW)
        raise PermissionDenied("拒绝录入")

    logic = MeasurementLogic(factory, SimpleNamespace(record=fail))
    with pytest.raises(PermissionDenied):
        logic.record(COACH, measurement())
    assert db.session.scalar(select(db.measurements.c.id)) is None
    assert not sessions[0].in_transaction()


def test_logic_unknown_commit_retains_record_id(db, service, monkeypatch):
    session = Session(db.engine)
    monkeypatch.setattr(session, "commit", Mock(side_effect=OSError("connection lost")))
    with pytest.raises(OutcomeUnknownError) as caught:
        MeasurementLogic(lambda: session, service).record(COACH, measurement())
    assert caught.value.record_id is not None
    assert not session.in_transaction()


def test_logic_audit_failure_keeps_committed_record(db, service, monkeypatch, capsys):
    monkeypatch.setattr("src.logic.measurement_logic.log_event", Mock(side_effect=RuntimeError("private")))
    result = MeasurementLogic(lambda: Session(db.engine), service).record(COACH, measurement())
    assert db.session.scalar(select(db.measurements.c.id)) == result.id
    assert "private" not in capsys.readouterr().err


def test_logic_maps_database_failure_to_safe_storage_error(db):
    service = SimpleNamespace(get_measurement=Mock(side_effect=SQLAlchemyError("private SQL data")))
    with pytest.raises(StorageError) as caught:
        MeasurementLogic(lambda: Session(db.engine), service).get_measurement(MEMBER, 1)
    assert str(caught.value) == "查询体测记录失败"


@pytest.mark.parametrize("window", [
    DateWindow(start=NOW, end=NOW), DateWindow(start=NOW, end=NOW - timedelta(seconds=1)),
    DateWindow(start=NOW.replace(tzinfo=None), end=NOW),
])
def test_invalid_window(db, service, window):
    with pytest.raises(InvalidInputError):
        service.list_measurements(db.session, MEMBER, MeasurementQuery(member_id=10, window=window))


def test_comparison_delta_uses_after_minus_before(db, service):
    before = add(db, measured_at=NOW - timedelta(days=2))
    after = MeasurementRepository(db.session).create(
        measurement(weight_kg=Decimal("58.25"), body_fat_pct=Decimal("17.50")), 20, created_at=NOW,
    )
    comparison = service.compare(db.session, MEMBER, before.id, after.id)
    assert comparison.weight_delta_kg == Decimal("-1.75")
    assert comparison.body_fat_delta_pct == Decimal("-2.50")
