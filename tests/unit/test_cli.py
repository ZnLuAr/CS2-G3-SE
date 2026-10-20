"""CLI 输入、参数和脱敏展示。"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

import pytest

from main import parse_args
from src.errors.business import InputCancelled
from src.models.contracts import MemberView, Page
from src.ui.cli.formatters import format_member, format_members
from src.ui.cli.prompts import prompt_confirm, prompt_decimal, prompt_int, prompt_text


def test_parse_args_keeps_cli_default_and_config():
    assert parse_args([]).tui is False
    options = parse_args(["--tui", "--config", "custom.json"])
    assert options.tui is True
    assert options.config_path == "custom.json"



def test_prompt_text_cancel_and_decimal_integer_validation(monkeypatch):
    monkeypatch.setattr("builtins.input", mock.Mock(side_effect=["", "  ok  "]))
    assert prompt_text("值：") == "ok"
    monkeypatch.setattr("builtins.input", mock.Mock(side_effect=["x", "2"]))
    assert prompt_int("数：", minimum=1, maximum=3) == 2
    monkeypatch.setattr("builtins.input", mock.Mock(side_effect=["1.234", "2.50"]))
    assert prompt_decimal("金额：", minimum=Decimal("0")) == Decimal("2.50")
    monkeypatch.setattr("builtins.input", mock.Mock(return_value="q"))
    with pytest.raises(InputCancelled):
        prompt_confirm("继续？")



def test_formatter_masks_phone_and_reports_page():
    now = datetime(2026, 10, 19, tzinfo=timezone.utc)
    member = MemberView(
        id=1,
        name="张三",
        phone="13812345678",
        status="active",
        archived_at=None,
        created_at=now,
        updated_at=now,
    )
    text = format_member(member, timezone_name="Asia/Shanghai")
    assert "138****5678" in text
    assert "12345678" not in text
    page = Page(items=[member], total=1, page=1, page_size=20)
    assert "第 1/1 页，共 1 条" in format_members(page, timezone_name="Asia/Shanghai")
