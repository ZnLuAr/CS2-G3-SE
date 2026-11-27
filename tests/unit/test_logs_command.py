"""LOG-04：本机日志命令复用公共查询输入。"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from src.cmd import logs
from src.models.contracts import LogQuery, LogSnapshot


def test_logs_command_uses_shared_query_prompt(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        log=SimpleNamespace(directory=tmp_path, backup_count=0),
        timezone_name="Asia/Shanghai",
    )
    snapshot = LogSnapshot(
        captured_at=datetime.now(timezone.utc), entries=(), skipped_lines=0,
    )
    prompts: list[str] = []

    monkeypatch.setattr(logs, "load_config", lambda _: settings)
    monkeypatch.setattr(logs, "read_log_snapshot", lambda *_, **__: snapshot)
    monkeypatch.setattr(
        logs, "prompt_log_query",
        lambda timezone_name: prompts.append(timezone_name) or LogQuery(),
    )
    monkeypatch.setattr(logs.prompts, "prompt_confirm", lambda *_: False)
    monkeypatch.setattr("src.ui.cli.menus.browse_pages", lambda *_, **__: None)

    assert logs.main(["--config", "config.json"]) == 0
    assert prompts == ["Asia/Shanghai"]
