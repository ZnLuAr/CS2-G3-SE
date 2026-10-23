"""课程与预约 CLI 处理器、格式化和菜单测试。

处理器测试替换 `prompts` 的输入函数，检查“问什么、传什么、确认取消后是否
调用写服务”；不启动完整 CLI，也不依赖数据库。完整菜单循环由基础框架模块
实现后另行联调。
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from src.errors.business import PermissionDenied
from src.models.contracts import (
    BookingView,
    CoachView,
    CourseView,
    Page,
    RoomView,
    SessionView,
)
from src.ui.cli import formatters, prompts
from src.ui.cli.handlers.booking import BookingHandler
from src.ui.cli.handlers.course import CourseHandler
from src.ui.cli.menus import booking_menu, course_menu
from tests.conftest import ADMIN, COACH, MEMBER, RECEPTION

UTC = timezone.utc
START = datetime(2026, 12, 1, 6, 0, tzinfo=UTC)


def _session_view(session_id: int = 1) -> SessionView:
    return SessionView(
        id=session_id,
        course_id=1,
        course_name="私教体验课",
        kind="private",
        coach_id=1,
        coach_name="李教练",
        room_id=1,
        room_name="A 教室",
        starts_at=START,
        ends_at=datetime(2026, 12, 1, 7, 0, tzinfo=UTC),
        capacity=1,
        occupied_count=0,
        available_count=1,
        status="scheduled",
    )


def _booking_view(booking_id: int = 1, *, status: str = "reserved") -> BookingView:
    return BookingView(
        id=booking_id,
        member_id=1,
        member_name="张三",
        membership_id=1,
        session=_session_view(),
        status=status,
        booked_at=datetime(2026, 10, 1, tzinfo=UTC),
        checked_in_at=None,
        closed_at=None,
    )


class RecordingCourseService:
    """记录处理器传给课程服务的参数，并返回固定 View。"""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def create_coach(self, actor, data):
        self.calls.append(("create_coach", actor, data))
        return CoachView(
            id=9, account_id=data.account_id, name=data.name,
            specialty=data.specialty, is_active=True,
        )

    def update_coach(self, actor, coach_id, data):
        self.calls.append(("update_coach", actor, coach_id, data))
        return CoachView(
            id=coach_id, account_id=2, name=data.name,
            specialty=data.specialty, is_active=True,
        )

    def get_coach(self, actor, coach_id):
        self.calls.append(("get_coach", actor, coach_id))
        return CoachView(
            id=coach_id, account_id=2, name="李教练",
            specialty="力量训练", is_active=True,
        )

    def list_coaches(self, actor, query):
        self.calls.append(("list_coaches", actor, query))
        return Page(items=[], total=0, page=1, page_size=20)

    def set_coach_active(self, actor, coach_id, active):
        self.calls.append(("set_coach_active", actor, coach_id, active))
        return CoachView(
            id=coach_id, account_id=2, name="李教练",
            specialty="力量训练", is_active=active,
        )

    def create_course(self, actor, data):
        self.calls.append(("create_course", actor, data))
        return CourseView(
            id=7, name=data.name, kind="private",
            duration_minutes=data.duration_minutes, is_active=True,
        )

    def update_course(self, actor, course_id, data):
        self.calls.append(("update_course", actor, course_id, data))
        return CourseView(
            id=course_id, name=data.name, kind="private",
            duration_minutes=data.duration_minutes, is_active=True,
        )

    def get_course(self, actor, course_id):
        self.calls.append(("get_course", actor, course_id))
        return CourseView(
            id=course_id, name="私教体验课", kind="private",
            duration_minutes=60, is_active=True,
        )

    def list_courses(self, actor, query):
        self.calls.append(("list_courses", actor, query))
        return Page(items=[], total=0, page=1, page_size=20)

    def set_course_active(self, actor, course_id, active):
        self.calls.append(("set_course_active", actor, course_id, active))
        return CourseView(
            id=course_id, name="私教体验课", kind="private",
            duration_minutes=60, is_active=active,
        )

    def create_room(self, actor, data):
        self.calls.append(("create_room", actor, data))
        return RoomView(id=3, name=data.name, capacity=data.capacity, is_active=True)

    def update_room(self, actor, room_id, data):
        self.calls.append(("update_room", actor, room_id, data))
        return RoomView(id=room_id, name=data.name, capacity=data.capacity, is_active=True)

    def get_room(self, actor, room_id):
        self.calls.append(("get_room", actor, room_id))
        return RoomView(id=room_id, name="A 教室", capacity=4, is_active=True)

    def list_rooms(self, actor, query):
        self.calls.append(("list_rooms", actor, query))
        return Page(items=[], total=0, page=1, page_size=20)

    def set_room_active(self, actor, room_id, active):
        self.calls.append(("set_room_active", actor, room_id, active))
        return RoomView(id=room_id, name="A 教室", capacity=4, is_active=active)

    def create_session(self, actor, data, request_id):
        self.calls.append(("create_session", actor, data, request_id))
        return _session_view(2)

    def get_session(self, actor, session_id):
        self.calls.append(("get_session", actor, session_id))
        return _session_view(session_id)

    def list_sessions(self, actor, query):
        self.calls.append(("list_sessions", actor, query))
        return Page(items=[], total=0, page=1, page_size=20)

    def get_session_by_request(self, actor, request_id):
        self.calls.append(("get_session_by_request", actor, request_id))
        return _session_view()

    def complete_session(self, actor, session_id):
        self.calls.append(("complete_session", actor, session_id))
        return _session_view(session_id)

    def cancel_session(self, actor, session_id, request_id):
        self.calls.append(("cancel_session", actor, session_id, request_id))
        view = _session_view(session_id)
        return SessionView(
            id=view.id, course_id=view.course_id, course_name=view.course_name,
            kind=view.kind, coach_id=view.coach_id, coach_name=view.coach_name,
            room_id=view.room_id, room_name=view.room_name,
            starts_at=view.starts_at, ends_at=view.ends_at,
            capacity=view.capacity, occupied_count=view.occupied_count,
            available_count=view.available_count, status="cancelled",
        )


class RecordingBookingService:
    """记录处理器传给预约服务的参数，并返回固定 View。"""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def book(self, actor, data, request_id):
        self.calls.append(("book", actor, data, request_id))
        return _booking_view(5)

    def get_booking(self, actor, booking_id):
        self.calls.append(("get_booking", actor, booking_id))
        return _booking_view(booking_id)

    def get_booking_by_request(self, actor, request_id):
        self.calls.append(("get_booking_by_request", actor, request_id))
        return _booking_view()

    def cancel(self, actor, booking_id, request_id):
        self.calls.append(("cancel", actor, booking_id, request_id))
        return _booking_view(booking_id, status="cancelled")

    def list_bookings(self, actor, query):
        self.calls.append(("list_bookings", actor, query))
        return Page(items=[], total=0, page=1, page_size=20)


@pytest.fixture()
def course_cli(monkeypatch) -> tuple[CourseHandler, RecordingCourseService]:
    service = RecordingCourseService()
    handler = CourseHandler(service, lambda: ADMIN, timezone_name="Asia/Shanghai")
    return handler, service


@pytest.fixture()
def booking_cli() -> tuple[BookingHandler, RecordingBookingService]:
    service = RecordingBookingService()
    handler = BookingHandler(
        service,
        lambda: MEMBER,
        RecordingCourseService(),
        SimpleNamespace(),
        timezone_name="Asia/Shanghai",
    )
    return handler, service


def test_create_course_passes_input_and_prints_result(monkeypatch, capsys, course_cli) -> None:
    """创建课程时把名称、固定私教类型和时长交给服务，并打印编号。"""
    handler, service = course_cli
    monkeypatch.setattr(prompts, "prompt_text", lambda label, **kwargs: "拉伸课")
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: 45)
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: True)

    handler.create_course()

    assert len(service.calls) == 1
    _, actor, data = service.calls[0]
    assert actor == ADMIN
    assert data.name == "拉伸课"
    assert data.kind == "private"
    assert data.duration_minutes == 45
    assert "课程 #7：拉伸课" in capsys.readouterr().out


def test_create_session_generates_request_id_and_capacity_one(
    monkeypatch, capsys, course_cli,
) -> None:
    """排课时按顺序采集三个编号和起止时间，容量固定为 1 并生成请求编号。"""
    handler, service = course_cli
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: 1)
    monkeypatch.setattr(
        prompts, "prompt_datetime",
        lambda label, **kwargs: START,
    )
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: True)

    handler.create_session()

    assert len(service.calls) == 1
    _, _, data, request_id = service.calls[0]
    assert data.capacity == 1
    assert data.course_id == 1
    assert data.coach_id == 1
    assert data.room_id == 1
    assert request_id
    assert "课次 #2" in capsys.readouterr().out


def test_set_coach_active_toggles_current_state(monkeypatch, capsys, course_cli) -> None:
    """处理器先读取当前状态，再把相反状态交给服务。"""
    handler, service = course_cli
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: 1)
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: True)

    handler.set_coach_active()

    assert [call[0] for call in service.calls] == ["get_coach", "set_coach_active"]
    assert service.calls[1][3] is False
    assert "状态：停用" in capsys.readouterr().out


def test_cancel_session_confirm_false_does_not_call_write_service(
    monkeypatch, capsys, course_cli,
) -> None:
    """确认取消时返回，不调用 cancel_session。"""
    handler, service = course_cli
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: 1)
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: False)

    handler.cancel_session()

    assert [call[0] for call in service.calls] == ["get_session"]
    assert "已取消操作" in capsys.readouterr().out


def test_list_sessions_builds_date_window_and_filters(monkeypatch, course_cli) -> None:
    """课表查询把门店日期转成当天窗口，并传递教练、场地和状态筛选。"""
    handler, service = course_cli
    answers = iter(["2026-12-01", "1", "", "scheduled"])
    monkeypatch.setattr(
        prompts, "prompt_text", lambda label, **kwargs: next(answers)
    )

    handler.list_sessions()

    _, _, query = service.calls[0]
    assert query.coach_id == 1
    assert query.room_id is None
    assert query.status == "scheduled"
    assert query.window.start == datetime(2026, 12, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert query.window.end == datetime(2026, 12, 2, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_member_booking_uses_own_member_id(monkeypatch, booking_cli) -> None:
    """会员预约时不再询问会员编号，自动使用当前身份关联的会员。"""
    handler, service = booking_cli
    numbers = iter([1, 1])
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: next(numbers))
    monkeypatch.setattr(prompts, "prompt_member_id", lambda: pytest.fail("不应询问会员编号"))
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: True)

    handler.book()

    _, actor, data, request_id = service.calls[0]
    assert actor == MEMBER
    assert data.member_id == 1
    assert data.session_id == 1
    assert data.membership_id == 1
    assert request_id


def test_staff_booking_prompts_for_member_id(monkeypatch) -> None:
    """前台代约时询问目标会员编号，并把前台身份交给服务做权限检查。"""
    service = RecordingBookingService()
    handler = BookingHandler(
        service, lambda: RECEPTION, RecordingCourseService(),
        SimpleNamespace(), timezone_name="Asia/Shanghai",
    )
    monkeypatch.setattr(prompts, "prompt_member_id", lambda: 1)
    numbers = iter([1, 1])
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: next(numbers))
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: True)

    handler.book()

    _, actor, data, _ = service.calls[0]
    assert actor == RECEPTION
    assert data.member_id == 1


def test_booking_cancel_confirm_false_does_not_call_service(
    monkeypatch, capsys, booking_cli,
) -> None:
    """取消预约时确认否定，只读取详情，不调用 cancel。"""
    handler, service = booking_cli
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: 1)
    monkeypatch.setattr(prompts, "prompt_confirm", lambda label: False)

    handler.cancel()

    assert [call[0] for call in service.calls] == ["get_booking"]
    assert "已取消操作" in capsys.readouterr().out


def test_course_and_booking_menus_have_unique_keys_and_actions(course_cli, booking_cli) -> None:
    """菜单项键唯一、文字非空，每个操作都指向处理器方法。"""
    course_handler, _ = course_cli
    booking_handler, _ = booking_cli
    course_items = course_menu(course_handler)
    booking_items = booking_menu(booking_handler)

    assert len(course_items) == 21
    assert len(booking_items) == 5
    assert len({item.key for item in course_items}) == 21
    assert len({item.key for item in booking_items}) == 5
    assert all(item.label and callable(item.action) for item in course_items + booking_items)


def test_session_formatter_converts_to_store_timezone_and_labels_status() -> None:
    """课次按门店时区显示，状态和余位使用中文。"""
    text = formatters.format_session(_session_view(), timezone_name="Asia/Shanghai")
    assert "2026-12-01 14:00–15:00" in text
    assert "已排课" in text
    assert "0/1 人" in text


def test_booking_formatter_includes_member_card_and_status() -> None:
    """预约展示会员、会员卡和中文状态。"""
    text = formatters.format_booking(_booking_view(), timezone_name="Asia/Shanghai")
    assert "张三" in text
    assert "会员卡 #1" in text
    assert "已预约" in text
    assert "2026-12-01 14:00–15:00" in text


def test_page_formatters_keep_empty_page_information() -> None:
    """空列表仍展示 total 和页码，不退化成裸列表或 None。"""
    page = Page(items=[], total=0, page=1, page_size=20)
    text = formatters.format_sessions(page, timezone_name="Asia/Shanghai")
    assert "暂无课次记录" in text
    assert "共 0 条" in text
    assert "第 1 页" in text


def test_coach_cannot_book_from_handler() -> None:
    """教练身份在处理器层就得到明确拒绝，不进入输入和写服务。"""
    handler = BookingHandler(
        RecordingBookingService(), lambda: COACH, RecordingCourseService(),
        SimpleNamespace(), timezone_name="Asia/Shanghai",
    )
    with pytest.raises(PermissionDenied):
        handler.book()


def test_get_room_lists_scheduled_sessions(monkeypatch, capsys, course_cli) -> None:
    """查看场地详情后会列出该场地的已排课次，日期可留空。"""
    handler, service = course_cli
    monkeypatch.setattr(prompts, "prompt_int", lambda label, **kwargs: 1)
    monkeypatch.setattr(prompts, "prompt_text", lambda label, **kwargs: "")

    handler.get_room()

    assert [call[0] for call in service.calls] == ["get_room", "list_sessions"]
    _, _, query = service.calls[1]
    assert query.room_id == 1
    assert query.status == "scheduled"
    assert query.window is None
    assert "场地 #1" in capsys.readouterr().out
