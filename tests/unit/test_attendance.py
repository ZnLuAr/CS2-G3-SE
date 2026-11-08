"""ATT-01、ATT-04 的签到状态、持久化及 CLI 验收。"""

from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from src.db.booking_repo import BookingRepository
from src.db.course_repo import SessionRepository
from src.errors import (
    AuthenticationError, InvalidInputError, InvalidState, NotFoundError,
    OutcomeUnknownError, PermissionDenied, StorageError,
)
from src.logic import attendance_logic
from src.logic.attendance_logic import AttendanceLogic
from src.models.contracts import Actor
from src.services import attendance_service
from src.services.attendance_service import AttendanceService
from src.ui.cli.app import invoke_action
from src.ui.cli.handlers.attendance import AttendanceHandler
from src.ui.cli.menus import attendance_menu


START = datetime(2026, 11, 8, 8, tzinfo=timezone.utc)
END = START + timedelta(hours=1)
MEMBER = Actor(account_id=1, role="member", member_id=1, coach_id=None)
COACH = Actor(account_id=2, role="coach", member_id=None, coach_id=1)
DESK = Actor(account_id=3, role="receptionist", member_id=None, coach_id=None)
ADMIN = Actor(account_id=4, role="admin", member_id=None, coach_id=None)


@pytest.fixture
def attendance(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.connection.driver_connection.executescript("""
            CREATE TABLE members (
                id INTEGER PRIMARY KEY, name TEXT, phone TEXT, status TEXT,
                archived_at TEXT, created_at TEXT DEFAULT '2026-11-01', updated_at TEXT DEFAULT '2026-11-01'
            );
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY, name TEXT, description TEXT, kind TEXT, duration_minutes INTEGER,
                is_active BOOLEAN, created_at TEXT DEFAULT '2026-11-01', updated_at TEXT DEFAULT '2026-11-01'
            );
            CREATE TABLE coaches (
                id INTEGER PRIMARY KEY, name TEXT, phone TEXT, is_active BOOLEAN,
                created_at TEXT DEFAULT '2026-11-01', updated_at TEXT DEFAULT '2026-11-01'
            );
            CREATE TABLE rooms (
                id INTEGER PRIMARY KEY, name TEXT, location TEXT, is_active BOOLEAN,
                created_at TEXT DEFAULT '2026-11-01', updated_at TEXT DEFAULT '2026-11-01'
            );
            CREATE TABLE course_sessions (
                id INTEGER PRIMARY KEY, course_id INTEGER, coach_id INTEGER, room_id INTEGER, course_name TEXT,
                kind TEXT, starts_at TEXT, ends_at TEXT, capacity INTEGER, status TEXT,
                created_at TEXT DEFAULT '2026-11-01', updated_at TEXT DEFAULT '2026-11-01'
            );
            CREATE TABLE bookings (
                id INTEGER PRIMARY KEY, member_id INTEGER, session_id INTEGER, lesson_package_id INTEGER,
                status TEXT, booked_at TEXT, checked_in_at TEXT, closed_at TEXT,
                created_at TEXT DEFAULT '2026-11-01', updated_at TEXT DEFAULT '2026-11-01'
            );
            CREATE TABLE lesson_packages (id INTEGER PRIMARY KEY, remaining_lessons INTEGER, reserved_lessons INTEGER);
            CREATE TABLE gym_entries (id INTEGER PRIMARY KEY, booking_id INTEGER);
            INSERT INTO members (id, name, status) VALUES (1, '合成会员', 'active');
            INSERT INTO courses (id, name, kind, duration_minutes, is_active) VALUES (1, '私教', 'private', 60, 1);
            INSERT INTO coaches (id, name, is_active) VALUES (1, '合成教练', 1);
            INSERT INTO rooms (id, name, is_active) VALUES (1, '训练室', 1);
            INSERT INTO course_sessions (id, course_id, coach_id, room_id, course_name, kind,
                                         starts_at, ends_at, capacity, status)
                VALUES (1, 1, 1, 1, '私教', 'private', '2026-11-08 08:00:00', '2026-11-08 09:00:00', 1, 'scheduled');
            INSERT INTO bookings (id, member_id, session_id, lesson_package_id, status, booked_at)
                VALUES (1, 1, 1, 1, 'reserved', '2026-11-07 08:00:00');
            INSERT INTO lesson_packages VALUES (1, 4, 1);
            INSERT INTO gym_entries VALUES (1, 1);
        """)
    sessions = sessionmaker(engine)
    auth = Mock()
    auth.verify_actor.side_effect = lambda session, actor: actor
    clock = Mock()
    clock.now.return_value = START
    monkeypatch.setattr(attendance_service, "datetime", clock)
    try:
        yield AttendanceLogic(sessions, AttendanceService(auth)), sessions, clock.now
    finally:
        engine.dispose()


@pytest.mark.parametrize("actor", [MEMBER, COACH, DESK, ADMIN])
def test_check_in_at_start_and_retry_keeps_original_time(attendance, actor):
    logic, sessions, now = attendance
    first = logic.check_in(actor, 1)
    now.return_value = START + timedelta(minutes=20)
    assert logic.check_in(actor, 1) == first
    assert first.status == "checked_in"
    assert first.checked_in_at == START
    assert first.member_name == "合成会员"
    assert (first.session.occupied_count, first.session.available_count) == (1, 0)
    with sessions() as session:
        assert BookingRepository(session).get(1) == first
        assert session.execute(text("SELECT remaining_lessons, reserved_lessons FROM lesson_packages")).one() == (4, 1)
        assert session.execute(text("SELECT id, booking_id FROM gym_entries")).all() == [(1, 1)]


@pytest.mark.parametrize("at", [START - timedelta(microseconds=1), END, END + timedelta(minutes=1)])
def test_check_in_rejects_outside_window(attendance, at):
    logic, sessions, now = attendance
    now.return_value = at
    with pytest.raises(InvalidState):
        logic.check_in(MEMBER, 1)
    with sessions() as session:
        assert BookingRepository(session).get(1).status == "reserved"


def test_correction_records_actual_time_once_and_clears_it_on_undo(attendance, capsys):
    logic, sessions, now = attendance
    now.return_value = END
    added = logic.correct_attendance(COACH, 1, True)
    assert added.checked_in_at == END
    event = json.loads(capsys.readouterr().err)
    assert (event["operation"], event["actor_id"], event["result_id"]) == ("attendance.correct", 2, 1)
    assert event["attendance_change"] == {
        "before": "reserved", "after": "checked_in", "before_checked_in_at": None,
        "after_checked_in_at": END.isoformat(), "corrected_at": END.isoformat(),
    }
    now.return_value = END + timedelta(minutes=5)
    assert logic.correct_attendance(COACH, 1, True) == added
    assert capsys.readouterr().err == ""
    removed = logic.correct_attendance(ADMIN, 1, False)
    assert (removed.status, removed.checked_in_at) == ("reserved", None)
    event = json.loads(capsys.readouterr().err)
    assert event["attendance_change"]["before_checked_in_at"] == END.isoformat()
    assert event["attendance_change"]["after_checked_in_at"] is None
    assert event["attendance_change"]["corrected_at"] == now.return_value.isoformat()
    with sessions() as session:
        assert BookingRepository(session).get(1) == removed
        assert session.execute(text("SELECT remaining_lessons, reserved_lessons FROM lesson_packages")).one() == (4, 1)
        assert session.execute(text("SELECT id, booking_id FROM gym_entries")).all() == [(1, 1)]


@pytest.mark.parametrize("status", ["cancelled", "completed", "no_show"])
def test_terminal_booking_cannot_be_changed(attendance, status):
    logic, sessions, _ = attendance
    with sessions.begin() as session:
        session.execute(text("UPDATE bookings SET status = :status WHERE id = 1"), {"status": status})
    with pytest.raises(InvalidState):
        logic.check_in(MEMBER, 1)
    with pytest.raises(InvalidState):
        logic.correct_attendance(ADMIN, 1, True)


def test_closed_session_has_no_available_seats(attendance):
    _, sessions, _ = attendance
    with sessions.begin() as session:
        session.execute(text("UPDATE bookings SET status = 'cancelled'"))
        session.execute(text("UPDATE course_sessions SET status = 'cancelled'"))
        view = SessionRepository(session).get(1)
        assert (view.occupied_count, view.available_count) == (0, 0)


def test_correction_scope_and_invalid_inputs(attendance):
    logic, _, now = attendance
    other_coach = Actor(account_id=5, role="coach", member_id=None, coach_id=2)
    other_member = Actor(account_id=6, role="member", member_id=2, coach_id=None)
    for actor in (DESK, MEMBER, other_coach):
        with pytest.raises(PermissionDenied):
            logic.correct_attendance(actor, 1, True)
    for actor in (other_member, other_coach):
        with pytest.raises(NotFoundError):
            logic.check_in(actor, 1)
    with pytest.raises(InvalidInputError):
        logic.correct_attendance(ADMIN, 1, 1)
    with pytest.raises(InvalidInputError):
        logic.check_in(MEMBER, True)
    now.return_value = START - timedelta(microseconds=1)
    with pytest.raises(InvalidState):
        logic.correct_attendance(COACH, 1, True)


def test_write_failure_rolls_back_without_audit(attendance, monkeypatch, capsys):
    logic, sessions, _ = attendance
    original = BookingRepository.set_state

    def fail_after_update(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise OperationalError(None, None, RuntimeError("test failure"))

    monkeypatch.setattr(BookingRepository, "set_state", fail_after_update)
    with pytest.raises(StorageError):
        logic.correct_attendance(COACH, 1, True)
    with sessions() as session:
        assert BookingRepository(session).get(1).status == "reserved"
    assert capsys.readouterr().err == ""


def test_committed_correction_survives_closed_log_output(attendance, monkeypatch):
    logic, sessions, _ = attendance
    closed_output = StringIO()
    closed_output.close()
    monkeypatch.setattr(attendance_logic, "sys", Mock(stderr=closed_output))
    changed = logic.correct_attendance(COACH, 1, True)
    with sessions() as session:
        assert BookingRepository(session).get(1) == changed


@pytest.mark.parametrize("answers", [["q"], ["1", "q"], ["1", "1", "q"], ["1", "1", "n"]])
def test_cli_cancel_does_not_write(monkeypatch, answers):
    logic = Mock()
    handler = AttendanceHandler(logic, lambda: COACH, timezone_name="Asia/Shanghai")
    monkeypatch.setattr("builtins.input", Mock(side_effect=answers))
    correction = attendance_menu(handler)[1]
    assert invoke_action(correction.action, operation=correction.operation).action == "continue"
    logic.correct_attendance.assert_not_called()


def test_cli_uses_real_logic_and_displays_booking(attendance, monkeypatch, capsys):
    logic, _, _ = attendance
    handler = AttendanceHandler(logic, lambda: COACH, timezone_name="Asia/Shanghai")
    monkeypatch.setattr("builtins.input", Mock(side_effect=["1", "y", "1", "2", "y"]))
    signup, correction = attendance_menu(handler)
    for item in (signup, correction):
        assert invoke_action(item.action, operation=item.operation).action == "continue"
    output = capsys.readouterr().out
    assert "合成会员" in output
    assert "2026-11-08 16:00" in output
    assert len(attendance_menu(AttendanceHandler(logic, lambda: DESK, timezone_name="Asia/Shanghai"))) == 1


@pytest.mark.parametrize("error, action, message", [
    (InvalidState("超出签到时间"), "continue", "超出签到时间"),
    (AuthenticationError("请重新登录"), "login", "请重新登录"),
    (StorageError("保存签到失败"), "exit", "保存签到失败"),
    (RuntimeError("internal details"), "exit", "签到操作失败，请稍后重试"),
    (OutcomeUnknownError("核实签到结果", record_id=1), "verify", "核实签到结果"),
])
def test_cli_keeps_safe_error_actions_before_shared_error_handler_is_available(error, action, message):
    result = invoke_action(Mock(side_effect=error), operation="attendance.checkin")
    assert (result.message, result.action) == (message, action)
    if action == "verify":
        assert result.record_id == 1
