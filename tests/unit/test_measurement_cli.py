"""体测交互的取消、类型转换、分页与角色菜单。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.errors.business import InputCancelled
from src.models.contracts import Actor, MeasurementComparison, MeasurementView, Page
from src.ui.cli.handlers.measurement import MeasurementHandler
from src.ui.cli.menus import measurement_menu


def _actor(role="coach"):
    return Actor(
        account_id=1,
        role=role,
        member_id=4 if role == "member" else None,
        coach_id=2 if role == "coach" else None,
    )


def _measurement(measurement_id=7):
    return MeasurementView(
        id=measurement_id,
        member_id=4,
        coach_id=2,
        measured_at=datetime(2026, 10, 20, 2, tzinfo=timezone.utc),
        created_at=datetime(2026, 10, 20, 3, tzinfo=timezone.utc),
        height_cm=Decimal("175.00"),
        weight_kg=Decimal("65.50"),
        body_fat_pct=None,
    )


def _input(monkeypatch, values):
    monkeypatch.setattr("builtins.input", Mock(side_effect=values))


@pytest.mark.parametrize(
    "answers",
    [
        ["q"],
        ["4", "q"],
        ["4", "2026-10-20 10:00", "q"],
        ["4", "2026-10-20 10:00", "175", "65.5", "q"],
        ["4", "2026-10-20 10:00", "175", "65.5", "n", "q"],
    ],
)
def test_cancel_record_does_not_call_write_use_case(monkeypatch, answers):
    logic = Mock()
    handler = MeasurementHandler(logic, _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, answers)
    with pytest.raises(InputCancelled):
        handler.record()
    logic.record.assert_not_called()


def test_declining_confirmation_does_not_write(monkeypatch):
    logic = Mock()
    handler = MeasurementHandler(logic, _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, ["4", "2026-10-20 10:00", "175", "65.5", "n", "n"])
    handler.record()
    logic.record.assert_not_called()


@pytest.mark.parametrize("body_fat_answers, expected", [(["n"], None), (["y", "18.25"], Decimal("18.25"))])
def test_record_converts_local_time_and_decimal_input(monkeypatch, capsys, body_fat_answers, expected):
    logic = Mock()
    logic.record.return_value = _measurement()
    actor = _actor()
    handler = MeasurementHandler(logic, lambda: actor, timezone_name="Asia/Shanghai")
    _input(
        monkeypatch,
        ["invalid", "4", "2026-10-20 10:00", "175", "65.500", "65.50", *body_fat_answers, "y"],
    )
    handler.record()
    called_actor, data = logic.record.call_args.args
    assert called_actor == actor
    assert data.measured_at == datetime(2026, 10, 20, 2, tzinfo=timezone.utc)
    assert data.height_cm == Decimal("175.00")
    assert data.weight_kg == Decimal("65.50")
    assert data.body_fat_pct == expected
    assert "编号：7" in capsys.readouterr().out


def test_member_history_preserves_scope_and_filters_between_pages(monkeypatch):
    actor = _actor("member")
    queries = []

    def fetch(called_actor, query):
        assert called_actor == actor
        queries.append(query)
        return Page(items=[_measurement()], total=21, page=query.paging.page, page_size=20)

    logic = Mock(list_measurements=Mock(side_effect=fetch))
    handler = MeasurementHandler(logic, lambda: actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, ["y", "2026-10-01 00:00", "2026-11-01 00:00", "n", "p", "0"])
    handler.list_measurements()
    assert [query.paging.page for query in queries] == [1, 2, 1]
    assert all(query.member_id == 4 for query in queries)
    assert all(query.window == queries[0].window for query in queries)
    assert queries[0].window.start == datetime(2026, 9, 30, 16, tzinfo=timezone.utc)


def test_compare_passes_ids_and_displays_nullable_delta(monkeypatch, capsys):
    logic = Mock()
    logic.compare.return_value = MeasurementComparison(
        before=_measurement(7),
        after=_measurement(8),
        height_delta_cm=Decimal("0.00"),
        weight_delta_kg=Decimal("-1.00"),
        body_fat_delta_pct=None,
    )
    handler = MeasurementHandler(logic, _actor, timezone_name="Asia/Shanghai")
    _input(monkeypatch, ["7", "8"])
    handler.compare()
    assert logic.compare.call_args.args[1:] == (7, 8)
    output = capsys.readouterr().out
    assert "体重变化（千克）：-1.00" in output
    assert "体脂率变化（百分点）：—" in output


@pytest.mark.parametrize("role, count", [("member", 3), ("coach", 4), ("admin", 0), ("receptionist", 0)])
def test_measurement_menu_follows_current_role(role, count):
    handler = MeasurementHandler(Mock(), lambda: _actor(role), timezone_name="Asia/Shanghai")
    items = measurement_menu(handler)
    assert len(items) == count
    assert len({item.key for item in items}) == count
    assert any(item.action == handler.record for item in items) == (role == "coach")
