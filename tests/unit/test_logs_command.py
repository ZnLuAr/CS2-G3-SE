"""LOG-04：本机日志命令复用公共查询输入。"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from src.cmd import logs
from src.errors.business import InputCancelled, ResourceError
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


def _patch_common(monkeypatch, tmp_path, settings=None):
    settings = settings or SimpleNamespace(
        log=SimpleNamespace(directory=tmp_path, backup_count=0),
        timezone_name="Asia/Shanghai",
    )
    monkeypatch.setattr(logs, "load_config", lambda _: settings)
    monkeypatch.setattr(logs, "prompt_log_query", lambda _: LogQuery())


def test_logs_command_returns_2_without_config_argument(capsys):
    """缺少 --config 时按参数错误返回 2。"""
    assert logs.main([]) == 2
    assert "--config" in capsys.readouterr().err


def test_logs_command_returns_1_when_snapshot_cannot_be_read(monkeypatch, tmp_path, capsys):
    """读取快照抛 GymError 时输出提示并返回 1，不进入交互。"""
    _patch_common(monkeypatch, tmp_path)
    prompted = []
    monkeypatch.setattr(logs, "read_log_snapshot", lambda *_, **__: (_ for _ in ()).throw(
        ResourceError("日志目录不可读"),
    ))
    monkeypatch.setattr(logs, "prompt_log_query", lambda _: prompted.append(1))
    assert logs.main(["--config", "config.json"]) == 1
    assert prompted == [] and "日志目录不可读" in capsys.readouterr().out


def test_logs_command_pages_through_one_snapshot_and_refreshes_on_confirm(monkeypatch, tmp_path):
    """翻页始终查询打开时的同一份快照；确认刷新后才重新读取。"""
    _patch_common(monkeypatch, tmp_path)
    first = LogSnapshot(captured_at=datetime.now(timezone.utc), entries=(), skipped_lines=0)
    second = LogSnapshot(captured_at=datetime.now(timezone.utc), entries=(), skipped_lines=0)
    reads, queried, confirmed = [], [], []

    def fake_read(*_, **__):
        reads.append(1)
        return first if len(reads) == 1 else second

    def fake_query(snapshot, query):
        queried.append(snapshot)
        return SimpleNamespace(items=[], total=0, page=1, page_size=20)

    def fake_browse(fetch, render):
        fetch(SimpleNamespace(page=1, page_size=20))
        fetch(SimpleNamespace(page=2, page_size=20))

    monkeypatch.setattr(logs, "read_log_snapshot", fake_read)
    monkeypatch.setattr(logs, "query_log_snapshot", fake_query)
    monkeypatch.setattr(logs.prompts, "prompt_confirm", lambda _: confirmed.append(1) or len(confirmed) == 1)
    monkeypatch.setattr("src.ui.cli.menus.browse_pages", fake_browse)

    assert logs.main(["--config", "config.json"]) == 0
    assert len(reads) == 2
    # 第一轮两页都查第一份快照；确认刷新后第二轮查第二份。
    assert queried[:2] == [first, first] and queried[2] is second


def test_logs_command_cancel_is_normal_exit(monkeypatch, tmp_path):
    """用户取消输入按正常退出返回 0。"""
    _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(
        logs, "read_log_snapshot",
        lambda *_, **__: LogSnapshot(captured_at=datetime.now(timezone.utc), entries=(), skipped_lines=0),
    )
    monkeypatch.setattr(
        logs, "prompt_log_query",
        lambda _: (_ for _ in ()).throw(InputCancelled()),
    )
    assert logs.main(["--config", "config.json"]) == 0
