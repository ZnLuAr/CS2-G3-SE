"""课程/预约 CLI 菜单与处理器的最小测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.models.contracts import CourseView
from src.ui.cli import prompts
from src.ui.cli.handlers.booking import BookingHandler
from src.ui.cli.handlers.course import CourseHandler
from src.ui.cli.menus import booking_menu, course_menu


def _stub_handler(role: str) -> SimpleNamespace:
    names = [
        "create_coach", "update_coach", "get_coach", "list_coaches", "set_coach_active",
        "create_course", "update_course", "get_course", "list_courses", "set_course_active",
        "create_room", "update_room", "get_room", "list_rooms", "set_room_active",
        "create_session", "get_session", "list_sessions", "get_session_by_request",
        "complete_session", "cancel_session",
        "book", "get_booking", "get_booking_by_request", "cancel", "list_bookings",
    ]
    return SimpleNamespace(current_role=role, **{name: (lambda: None) for name in names})


def test_course_menu_filters_admin_and_member_entries():
    admin = course_menu(_stub_handler("admin"))
    member = course_menu(_stub_handler("member"))
    assert "1" in {item.key for item in admin}
    assert "6" in {item.key for item in admin}
    assert "1" not in {item.key for item in member}
    assert "18" in {item.key for item in member}
    assert all(item.operation and callable(item.action) for item in admin + member)


def test_booking_menu_hides_booking_for_coach():
    coach = booking_menu(_stub_handler("coach"))
    member = booking_menu(_stub_handler("member"))
    assert {item.key for item in coach} == {"2", "5"}
    assert "1" in {item.key for item in member}


def test_create_course_handler_passes_private_template(monkeypatch):
    calls = []

    class Logic:
        def create_course(self, actor, data):
            calls.append((actor, data))
            return CourseView(
                id=7, name=data.name, description=data.description, kind="private",
                duration_minutes=data.duration_minutes, is_active=True,
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            )

    actor = object()
    handler = CourseHandler(Logic(), lambda: actor, timezone_name="Asia/Shanghai")
    monkeypatch.setattr(prompts, "prompt_text", lambda label, **kwargs: "拉伸课")
    monkeypatch.setattr(prompts, "prompt_optional_text", lambda label: None)
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: 45)
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: True)

    handler.create_course()

    assert len(calls) == 1
    _, data = calls[0]
    assert data.kind == "private"
    assert data.duration_minutes == 45
    assert data.name == "拉伸课"


def test_member_booking_uses_own_member_id(monkeypatch):
    calls = []

    class Logic:
        def book(self, actor, data, request_id):
            calls.append((actor, data, request_id))
            return SimpleNamespace()

    actor = SimpleNamespace(role="member", member_id=1, account_id=3, coach_id=None)
    handler = BookingHandler(
        Logic(), lambda: actor, SimpleNamespace(), SimpleNamespace(),
        timezone_name="Asia/Shanghai",
    )
    numbers = iter([1, 1])
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: next(numbers))
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: True)
    monkeypatch.setattr(prompts, "prompt_member_id", lambda: pytest.fail("会员不应被询问编号"))
    monkeypatch.setattr("src.ui.cli.handlers.booking.formatters.format_booking", lambda *a, **k: "ok")

    handler.book()

    assert calls[0][1].member_id == 1
    assert calls[0][1].session_id == 1
    assert calls[0][1].lesson_package_id == 1
    assert calls[0][2]
