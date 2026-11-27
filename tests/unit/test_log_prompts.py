"""LOG-04：日志查询输入校验与菜单操作名登记。"""

from __future__ import annotations

from types import SimpleNamespace

from src.logging import Operation
from src.ui.cli.log_prompts import prompt_log_query
from src.ui.cli.menus import auth_menu


def test_overlong_operation_is_rejected_at_input_and_prompts_again(monkeypatch, capsys):
    monkeypatch.setattr("src.ui.cli.log_prompts.prompts.prompt_confirm", lambda _: False)
    monkeypatch.setattr("src.ui.cli.log_prompts.prompts.prompt_int", lambda *_, **__: 0)
    answers = iter(["op" * 40, "auth.login", ""])
    monkeypatch.setattr(
        "src.ui.cli.log_prompts.prompts.prompt_text", lambda *_, **__: next(answers),
    )
    monkeypatch.setattr(
        "src.ui.cli.log_prompts.prompts.prompt_optional_text", lambda _: None,
    )

    query = prompt_log_query("Asia/Shanghai")

    assert query.operation == "auth.login"
    assert query.request_id is None
    assert "操作名称必须是 1～64 个字符" in capsys.readouterr().out


def test_overlong_request_id_is_rejected_at_input_and_prompts_again(monkeypatch, capsys):
    monkeypatch.setattr("src.ui.cli.log_prompts.prompts.prompt_confirm", lambda _: False)
    monkeypatch.setattr("src.ui.cli.log_prompts.prompts.prompt_int", lambda *_, **__: 0)
    answers = iter(["", "r" * 65, "request-1"])
    monkeypatch.setattr(
        "src.ui.cli.log_prompts.prompts.prompt_text", lambda *_, **__: next(answers),
    )
    monkeypatch.setattr(
        "src.ui.cli.log_prompts.prompts.prompt_optional_text", lambda _: None,
    )

    query = prompt_log_query("Asia/Shanghai")

    assert query.request_id == "request-1"
    assert "请求编号必须是 1～64 个字符" in capsys.readouterr().out


def test_invalid_actor_id_prompts_again(monkeypatch, capsys):
    monkeypatch.setattr("src.ui.cli.log_prompts.prompts.prompt_confirm", lambda _: False)
    monkeypatch.setattr("src.ui.cli.log_prompts.prompts.prompt_int", lambda *_, **__: 0)
    monkeypatch.setattr("src.ui.cli.log_prompts.prompts.prompt_text", lambda *_, **__: "")
    answers = iter(["abc", "0", "7"])
    monkeypatch.setattr(
        "src.ui.cli.log_prompts.prompts.prompt_optional_text", lambda _: next(answers),
    )

    assert prompt_log_query("Asia/Shanghai").actor_id == 7
    assert capsys.readouterr().out.count("请输入正整数编号") == 2


def test_auth_menu_registers_separate_activate_and_deactivate_actions():
    names = (
        "create_account", "get_account", "list_accounts",
        "deactivate_account", "activate_account",
        "link_profile", "relink_profile", "query_logs",
    )
    handler = SimpleNamespace(**{name: (lambda: None) for name in names})

    items = auth_menu(handler)

    assert [item.key for item in items] == ["1", "2", "3", "4", "5", "6", "7", "8"]
    assert [item.operation for item in items] == [
        Operation.ACCOUNT_CREATE.value,
        Operation.ACCOUNT_QUERY.value,
        Operation.ACCOUNT_QUERY.value,
        Operation.ACCOUNT_DEACTIVATE.value,
        Operation.ACCOUNT_ACTIVATE.value,
        Operation.ACCOUNT_LINK.value,
        Operation.ACCOUNT_LINK.value,
        Operation.LOG_QUERY.value,
    ]
    assert items[3].action is handler.deactivate_account
    assert items[4].action is handler.activate_account
