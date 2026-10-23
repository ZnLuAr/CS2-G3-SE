"""课程、排课与预约模块的 v3 服务/Logic 单元测试。

使用 SQLite 内存库和假身份校验，不连接 MySQL；真实行锁与并发仍需
`initialized_mysql_database` 集成测试验证。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from src.db.tables import (
    coaches, course_sessions, courses, lesson_packages, members, metadata, rooms,
)
from src.errors.business import (
    CapacityExceeded, CardNotEligible, ConflictError, InvalidInputError,
    InvalidState, NotFoundError, PermissionDenied, ScheduleConflict,
)
from src.logic.course_logic import CourseLogic
from src.logic.reservation_logic import ReservationLogic
from src.models.contracts import (
    Actor, BookingInput, CourseInput, SessionInput, SessionQuery,
)
from src.services.booking_service import BookingService
from src.services.coach_service import CoachService
from src.services.course_service import CourseService
from src.services.room_service import RoomService

UTC = timezone.utc
ADMIN = Actor(account_id=1, role="admin", member_id=None, coach_id=None)
COACH = Actor(account_id=2, role="coach", member_id=None, coach_id=1)
MEMBER = Actor(account_id=3, role="member", member_id=1, coach_id=None)
RECEPTION = Actor(account_id=4, role="receptionist", member_id=None, coach_id=None)


class FakeAuth:
    def verify_actor(self, session, actor):
        return actor


@pytest.fixture()
def factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def quiet_log(monkeypatch):
    monkeypatch.setattr("src.logic.course_logic.log_event", lambda *a, **k: True)
    monkeypatch.setattr("src.logic.reservation_logic.log_event", lambda *a, **k: True)


@pytest.fixture()
def seed(factory):
    now = datetime.now(UTC).replace(tzinfo=None)
    with factory() as session:
        with session.begin():
            session.execute(insert(members).values(
                id=1, name="张三", phone=None, status="active",
                archived_at=None, created_at=now, updated_at=now,
            ))
            session.execute(insert(coaches).values(
                id=1, name="李教练", phone=None, is_active=True,
                created_at=now, updated_at=now,
            ))
            session.execute(insert(courses).values(
                id=1, name="私教体验课", description=None, kind="private",
                duration_minutes=60, is_active=True, created_at=now, updated_at=now,
            ))
            session.execute(insert(rooms).values(
                id=1, name="A 教室", location=None, is_active=True,
                created_at=now, updated_at=now,
            ))
            session.execute(insert(lesson_packages).values(
                id=1, member_id=1, product_id=1, purchase_sale_item_id=1,
                name="私教 20 节", total_lessons=20, remaining_lessons=20,
                reserved_lessons=0, valid_from=date(2026, 1, 1),
                valid_until=date(2027, 1, 1), status="active",
                created_at=now, updated_at=now,
            ))
    return {"now": now}


@pytest.fixture()
def logic(factory):
    auth = FakeAuth()
    course = CourseService(auth)
    course_logic = CourseLogic(
        factory, CoachService(auth), course, RoomService(auth),
    )
    booking = BookingService(auth, timezone_name="Asia/Shanghai")
    reservation = ReservationLogic(factory, booking, course, SimpleNamespace(), SimpleNamespace())
    return course_logic, reservation, booking


def _future(minutes: int = 0) -> datetime:
    return datetime.now(UTC) + timedelta(days=30, minutes=minutes)


def _session_input(**overrides) -> SessionInput:
    start = overrides.pop("starts_at", _future())
    values = {
        "course_id": 1, "coach_id": 1, "room_id": 1,
        "starts_at": start, "ends_at": start + timedelta(minutes=60),
    }
    values.update(overrides)
    return SessionInput(**values)


def _create_session(course_logic, actor=ADMIN, request_id=None, **overrides):
    return course_logic.create_session(
        actor, _session_input(**overrides), request_id or str(uuid4()),
    )


def test_course_session_lifecycle(logic, seed):
    course_logic, reservation, _ = logic
    course = course_logic.create_course(
        ADMIN, CourseInput(name="拉伸课", description="恢复", kind="private", duration_minutes=60)
    )
    assert course.name == "拉伸课"
    session = _create_session(course_logic, course_id=course.id)
    assert session.course.id == course.id
    assert session.course_name == "拉伸课"
    assert session.duration_minutes == 60
    assert session.capacity == 1
    assert session.available_count == 1
    assert course_logic.get_session(MEMBER, session.id).id == session.id
    assert course_logic.list_sessions(MEMBER, SessionQuery()).total == 1

    cancelled = reservation.cancel_session(ADMIN, session.id, str(uuid4()))
    assert cancelled.status == "cancelled"


def test_validation_and_conflict(logic, seed):
    course_logic, _, _ = logic
    with pytest.raises(InvalidInputError):
        course_logic.create_course(
            ADMIN, CourseInput(name=" ", description=None, kind="private", duration_minutes=60)
        )
    with pytest.raises(InvalidState):
        _create_session(course_logic, starts_at=datetime.now(UTC) - timedelta(minutes=1))
    with pytest.raises(InvalidInputError):
        _create_session(course_logic, ends_at=_future() + timedelta(minutes=30))
    first = _create_session(course_logic)
    with pytest.raises(ScheduleConflict):
        _create_session(course_logic, starts_at=first.starts_at + timedelta(minutes=30))
    with pytest.raises(PermissionDenied):
        _create_session(course_logic, actor=COACH)


def test_booking_and_cancel_reserve_release(logic, seed):
    course_logic, reservation, _ = logic
    session = _create_session(course_logic)
    booking = reservation.book(
        MEMBER, BookingInput(member_id=1, session_id=session.id, lesson_package_id=1),
        str(uuid4()),
    )
    assert booking.status == "reserved"
    assert booking.member_name == "张三"
    with course_logic._session_factory() as db:
        row = db.execute(lesson_packages.select().where(lesson_packages.c.id == 1)).mappings().one()
        assert row["reserved_lessons"] == 1
    with pytest.raises(ConflictError):
        reservation.book(
            MEMBER, BookingInput(member_id=1, session_id=session.id, lesson_package_id=1),
            str(uuid4()),
        )
    cancelled = reservation.cancel(MEMBER, booking.id, str(uuid4()))
    assert cancelled.status == "cancelled"
    with course_logic._session_factory() as db:
        row = db.execute(lesson_packages.select().where(lesson_packages.c.id == 1)).mappings().one()
        assert row["reserved_lessons"] == 0


def test_capacity_and_package_eligibility(logic, seed):
    course_logic, reservation, _ = logic
    session = _create_session(course_logic)
    with course_logic._session_factory() as db:
        from src.db.support import utc_now
        now = utc_now().replace(tzinfo=None)
        with db.begin():
            db.execute(insert(members).values(
                id=2, name="李四", phone=None, status="active",
                archived_at=None, created_at=now, updated_at=now,
            ))
            db.execute(insert(lesson_packages).values(
                id=2, member_id=2, product_id=1, purchase_sale_item_id=2,
                name="私教 20 节", total_lessons=20, remaining_lessons=20,
                reserved_lessons=0, valid_from=date(2026, 1, 1),
                valid_until=date(2027, 1, 1), status="active",
                created_at=now, updated_at=now,
            ))
    reservation.book(
        MEMBER, BookingInput(member_id=1, session_id=session.id, lesson_package_id=1),
        str(uuid4()),
    )
    with pytest.raises(CapacityExceeded):
        reservation.book(
            RECEPTION, BookingInput(member_id=2, session_id=session.id, lesson_package_id=2),
            str(uuid4()),
        )
    with pytest.raises(CardNotEligible):
        reservation.book(
            MEMBER, BookingInput(member_id=1, session_id=session.id, lesson_package_id=2),
            str(uuid4()),
        )


def test_cancel_session_closes_bookings(logic, seed):
    course_logic, reservation, _ = logic
    session = _create_session(course_logic)
    booking = reservation.book(
        MEMBER, BookingInput(member_id=1, session_id=session.id, lesson_package_id=1),
        str(uuid4()),
    )
    cancelled = reservation.cancel_session(ADMIN, session.id, str(uuid4()))
    assert cancelled.status == "cancelled"
    assert reservation.get_booking(MEMBER, booking.id).status == "cancelled"
    with course_logic._session_factory() as db:
        row = db.execute(lesson_packages.select().where(lesson_packages.c.id == 1)).mappings().one()
        assert row["reserved_lessons"] == 0


def test_session_visibility_and_complete(logic, seed):
    course_logic, reservation, _ = logic
    session = _create_session(course_logic)
    with pytest.raises(NotFoundError):
        course_logic.get_session(COACH, session.id + 999)
    assert course_logic.get_session(COACH, session.id).id == session.id
    with pytest.raises(InvalidState):
        course_logic.complete_session(ADMIN, session.id)
    # 直接插入一节已结束课次，验证完成条件。
    past = datetime.now(UTC) - timedelta(days=1)
    with course_logic._session_factory() as db:
        from src.db.support import to_db_utc
        with db.begin():
            session_id = db.execute(insert(course_sessions).values(
                course_id=1, coach_id=1, room_id=1, course_name="私教体验课",
                kind="private", starts_at=to_db_utc(past),
                ends_at=to_db_utc(past + timedelta(minutes=60)), capacity=1,
                status="scheduled", created_at=to_db_utc(past), updated_at=to_db_utc(past),
            )).inserted_primary_key[0]
    assert course_logic.complete_session(ADMIN, session_id).status == "completed"


def test_idempotency_and_valid_uuid(logic, seed):
    course_logic, reservation, _ = logic
    request_id = str(uuid4())
    data = _session_input()
    first = course_logic.create_session(ADMIN, data, request_id)
    second = course_logic.create_session(ADMIN, data, request_id)
    assert second.id == first.id
    with pytest.raises(ConflictError):
        course_logic.create_session(ADMIN, _session_input(starts_at=_future(minutes=90)), request_id)
    with pytest.raises(InvalidInputError):
        course_logic.create_session(ADMIN, _session_input(), "not-a-uuid")
