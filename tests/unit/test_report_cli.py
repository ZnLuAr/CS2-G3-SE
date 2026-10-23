"""收款筛选、统计分页及 CSV 新文件保存交互。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.errors.business import InputCancelled, ResourceError
from src.models.contracts import Actor, CoachStatsView, CsvExport, Page, PaymentView, SessionStatsView
from src.ui.cli.handlers.report import ReportHandler
from src.ui.cli.menus import report_menu


def _actor(role="admin"):
    return Actor(account_id=1, role=role, member_id=None, coach_id=None)


def _input(monkeypatch, values):
    monkeypatch.setattr("builtins.input", Mock(side_effect=values))


def _csv():
    return CsvExport(filename="payments.csv", content="\ufeffid,金额\r\n7,199.00\r\n".encode("utf-8"), row_count=1)


def test_payment_filters_are_validated_and_unchanged_between_pages(monkeypatch, capsys):
    actor = _actor("receptionist")
    queries = []
    payment = PaymentView(
        id=7,
        sale_order_id=3,
        member_id=4,
        amount=Decimal("199.00"),
        method="cash",
        paid_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        operator_id=1,
    )

    def fetch(called_actor, query):
        assert called_actor == actor
        queries.append(query)
        return Page(items=[payment], total=21, page=query.paging.page, page_size=20)

    logic = Mock(list_payments=Mock(side_effect=fetch))
    handler = ReportHandler(logic, lambda: actor, timezone_name="Asia/Shanghai")
    _input(
        monkeypatch,
        ["0", "bad", "4", "9", "1", "y", "2026-10-01 00:00", "2026-11-01 00:00", "n", "0"],
    )
    handler.list_payments()
    assert [query.paging.page for query in queries] == [1, 2]
    assert all(query.member_id == 4 and query.method == "cash" for query in queries)
    assert all(query.window == queries[0].window for query in queries)
    assert queries[0].window.start == datetime(2026, 9, 30, 16, tzinfo=timezone.utc)
    assert "销售单编号：3" in capsys.readouterr().out


@pytest.mark.parametrize("action", ["get_payment", "list_payments", "revenue", "session_stats", "coach_stats"])
def test_cancel_before_query_does_not_call_logic(monkeypatch, action):
    logic = Mock()
    handler = ReportHandler(logic, _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, ["q"])
    with pytest.raises(InputCancelled):
        getattr(handler, action)()
    assert not logic.mock_calls


@pytest.mark.parametrize(
    "action, answers",
    [
        ("export_payments", ["", "0", "n"]),
        ("export_revenue", ["2026-10-01 00:00", "2026-11-01 00:00"]),
        ("export_memberships", []),
        ("export_sessions", ["", "", "n", "0"]),
        ("export_coaches", ["2026-10-01 00:00", "2026-11-01 00:00"]),
    ],
)
def test_all_exports_save_service_bytes_after_confirmation(monkeypatch, tmp_path, action, answers):
    logic = Mock()
    getattr(logic, action).return_value = _csv()
    handler = ReportHandler(logic, _actor, timezone_name="Asia/Shanghai")
    target = tmp_path / "report.csv"
    _input(monkeypatch, [*answers, str(target), "y"])
    getattr(handler, action)()
    assert target.read_bytes() == _csv().content
    assert getattr(logic, action).call_count == 1
    assert getattr(logic, action).call_args.args[0] == _actor()
    if action == "export_memberships":
        logic.export_memberships.assert_called_once_with(_actor())


def test_export_does_not_overwrite_existing_file(monkeypatch, tmp_path):
    target = tmp_path / "existing.csv"
    target.write_bytes(b"user content")
    handler = ReportHandler(Mock(), _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, [str(target), "y"])
    with pytest.raises(ResourceError, match="已存在"):
        handler._save_export(_csv())
    assert target.read_bytes() == b"user content"


@pytest.mark.parametrize("choice", ["n", "q"])
def test_cancel_export_leaves_no_output(monkeypatch, tmp_path, choice):
    target = tmp_path / "cancelled.csv"
    handler = ReportHandler(Mock(), _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, [str(target), choice])
    if choice == "q":
        with pytest.raises(InputCancelled):
            handler._save_export(_csv())
    else:
        handler._save_export(_csv())
    assert not target.exists()


def test_missing_export_directory_becomes_resource_error(monkeypatch, tmp_path):
    handler = ReportHandler(Mock(), _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, [str(tmp_path / "missing" / "report.csv"), "y"])
    with pytest.raises(ResourceError, match="保存失败"):
        handler._save_export(_csv())


def test_invalid_export_path_becomes_resource_error(monkeypatch):
    handler = ReportHandler(Mock(), _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, ["invalid\0path.csv", "y"])
    with pytest.raises(ResourceError, match="保存失败"):
        handler._save_export(_csv())


def test_session_stats_preserve_room_coach_status_and_window(monkeypatch, capsys):
    queries = []

    def fetch(actor, query):
        queries.append(query)
        return Page(items=[SessionStatsView(
            session_id=8,
            starts_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
            reserved_count=0,
            checked_in_count=0,
            completed_count=1,
            no_show_count=1,
            cancelled_count=0,
            attendance_rate=Decimal("0.50"),
        )], total=21, page=query.paging.page, page_size=20)

    logic = Mock(session_stats=Mock(side_effect=fetch))
    handler = ReportHandler(logic, _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, ["2", "3", "y", "2026-10-01 00:00", "2026-11-01 00:00", "2", "n", "0"])
    handler.session_stats()
    assert [query.paging.page for query in queries] == [1, 2]
    assert all(query.coach_id == 2 and query.room_id == 3 and query.status == "completed" for query in queries)
    assert queries[0].window == queries[1].window
    assert "出勤率：50.00%" in capsys.readouterr().out


def test_coach_stats_pagination_uses_the_original_window(monkeypatch, capsys):
    calls = []

    def fetch(actor, window, paging):
        calls.append((window, paging))
        return Page(items=[CoachStatsView(
            coach_id=2, coach_name="测试教练", completed_sessions=3, attended_members=5,
        )], total=21, page=paging.page, page_size=20)

    logic = Mock(coach_stats=Mock(side_effect=fetch))
    handler = ReportHandler(logic, _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, ["2026-10-01 00:00", "2026-11-01 00:00", "n", "0"])
    handler.coach_stats()
    assert [paging.page for _, paging in calls] == [1, 2]
    assert calls[0][0] == calls[1][0]
    assert "完成课次：3" in capsys.readouterr().out


@pytest.mark.parametrize("role, count", [("admin", 11), ("receptionist", 2), ("member", 0), ("coach", 0)])
def test_report_menu_limits_receptionist_to_payment_details(role, count):
    handler = ReportHandler(Mock(), lambda: _actor(role), timezone_name="Asia/Shanghai")
    items = report_menu(handler)
    assert len(items) == count
    assert len({item.key for item in items}) == count
    if role == "receptionist":
        assert [item.action for item in items] == [handler.get_payment, handler.list_payments]
