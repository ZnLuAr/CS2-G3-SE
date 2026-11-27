"""AUTH-04/LOG-04：账号菜单处理器按固定动作调用用例。"""

from __future__ import annotations

from datetime import datetime, timezone

from src.models.contracts import (
    AccountView,
    Actor,
    LogQuery,
    LogSnapshot,
    Page,
    PageRequest,
)
from src.ui.cli.handlers.auth import AuthHandler

ACTOR = Actor(account_id=1, role="admin", member_id=None, coach_id=None)
VIEW = AccountView(
    id=5, username="member_2", role="member", is_active=True,
    member_id=None, coach_id=None,
)


class FakeLogic:
    def __init__(self) -> None:
        self.active_calls: list[bool] = []
        self.query_calls: list[tuple[LogQuery, LogSnapshot]] = []
        self.opened: LogSnapshot | None = None

    def set_account_active(self, actor, account_id, active):
        self.active_calls.append(active)
        return VIEW

    def open_log_snapshot(self, actor):
        self.opened = LogSnapshot(
            captured_at=datetime.now(timezone.utc), entries=(), skipped_lines=0,
        )
        return self.opened

    def query_logs(self, actor, query, *, snapshot):
        self.query_calls.append((query, snapshot))
        return Page(items=[], total=0, page=query.paging.page, page_size=query.paging.page_size)


def _handler(logic: FakeLogic) -> AuthHandler:
    return AuthHandler(
        logic, lambda: ACTOR, lambda actor: None, lambda: None,
        timezone_name="Asia/Shanghai",
    )


def test_menu_actions_do_not_ask_for_action_type(monkeypatch):
    logic = FakeLogic()
    handler = _handler(logic)
    monkeypatch.setattr("src.ui.cli.handlers.auth.prompts.prompt_int", lambda *_, **__: 5)
    monkeypatch.setattr("src.ui.cli.handlers.auth.prompts.prompt_confirm", lambda *_: True)

    handler.deactivate_account()
    handler.activate_account()

    assert logic.active_calls == [False, True]


def test_query_logs_uses_shared_prompt_and_same_snapshot(monkeypatch):
    logic = FakeLogic()
    handler = _handler(logic)
    captured: list[LogQuery] = []
    timezone_names: list[str] = []

    def prompt(timezone_name: str) -> LogQuery:
        # 公共输入入口应按配置的时区解释时间范围，不能丢掉该参数。
        timezone_names.append(timezone_name)
        captured.append(LogQuery())
        return captured[-1]

    def browse(fetch, format_page, **_):
        fetch(PageRequest())

    monkeypatch.setattr("src.ui.cli.handlers.auth.prompt_log_query", prompt)
    monkeypatch.setattr("src.ui.cli.menus.browse_pages", browse)
    monkeypatch.setattr("src.ui.cli.handlers.auth.prompts.prompt_confirm", lambda *_: False)

    handler.query_logs()

    assert timezone_names == ["Asia/Shanghai"]
    assert len(captured) == 1
    assert len(logic.query_calls) == 1
    assert logic.query_calls[0][0].paging == PageRequest()
    # 翻页查询必须使用打开时取得的同一份快照，不能每次重新读取。
    assert logic.query_calls[0][1] is logic.opened
