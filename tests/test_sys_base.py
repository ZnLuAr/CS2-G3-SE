from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import tempfile
from unittest import mock

import pytest

from main import parse_args
from src.config import load_config
from src.models.contracts import MemberView, Page
from src.ui.cli.formatters import format_member, format_members
from src.ui.cli.prompts import prompt_confirm, prompt_decimal, prompt_int, prompt_text
from src.errors.business import InputCancelled


def _config(path: Path, *, password: str = "file-pass") -> Path:
    path.write_text(json.dumps({
        "database": {"host": "localhost", "port": 3306, "database": "gym", "username": "u", "password": password},
        "timezone_name": "Asia/Shanghai",
    }), encoding="utf-8")
    return path


def test_parse_args_keeps_cli_default_and_config():
    assert parse_args([]).tui is False
    options = parse_args(["--tui", "--config", "custom.json"])
    assert options.tui is True
    assert options.config_path == "custom.json"


def test_load_config_environment_empty_password_overrides_file(monkeypatch):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=Path.cwd(), encoding="utf-8", delete=False
    ) as file:
        path = Path(file.name)
    try:
        _config(path)
        monkeypatch.setenv("DB_PASSWORD", "")
        settings = load_config(str(path))
        assert settings.database.password == ""
        assert settings.log.directory == (Path.cwd() / "logs").resolve()
    finally:
        path.unlink(missing_ok=True)


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
    member = MemberView(id=1, account_id=None, name="张三", phone="13812345678", is_active=True)
    text = format_member(member, timezone_name="Asia/Shanghai")
    assert "138****5678" in text
    assert "12345678" not in text
    page = Page(items=[member], total=1, page=1, page_size=20)
    assert "第 1/1 页，共 1 条" in format_members(page, timezone_name="Asia/Shanghai")
