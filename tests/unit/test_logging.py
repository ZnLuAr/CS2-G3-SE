from __future__ import annotations

import json
import logging
from pathlib import Path

from src.config import AppSettings, DatabaseConfig, LogConfig
from src.errors.business import InvalidInputError
from src.logging import close_logging, configure_logging, log_event
from src.logging.snapshots import query_log_snapshot, read_log_snapshot
from src.models.contracts import LogQuery


def _settings(directory: Path) -> AppSettings:
    return AppSettings(
        database=DatabaseConfig(
            host="localhost", port=3306, database="gym", username="tester", password="",
        ),
        log=LogConfig(directory=directory, backup_count=0),
    )


def test_log_event_writes_safe_json_and_snapshot_can_filter(tmp_path):
    configure_logging(_settings(tmp_path))
    try:
        assert log_event(
            logging.INFO, operation="auth.login", outcome="success", actor_id=7,
        )
        assert log_event(
            logging.WARNING, operation="member.create", outcome="rejected",
            actor_id=7, error=InvalidInputError("输入不合法"),
        )
        assert log_event(
            logging.ERROR, operation="member.create", outcome="failed",
            error=RuntimeError("password=secret"),
        )
    finally:
        close_logging()

    raw = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "secret" not in raw
    assert "输入不合法" in raw
    lines = [json.loads(line) for line in raw.splitlines()]
    assert lines[0]["operation"] == "auth.login"
    assert lines[2]["error_message"] is None

    snapshot = read_log_snapshot(tmp_path, backup_count=0)
    assert len(snapshot.entries) == 3
    page = query_log_snapshot(snapshot, LogQuery(level="WARNING"))
    assert page.total == 1
    assert page.items[0].operation == "member.create"


def test_corrupt_line_is_counted_and_long_message_is_truncated(tmp_path):
    configure_logging(_settings(tmp_path))
    try:
        with (tmp_path / "app.log").open("a", encoding="utf-8") as output:
            output.write("{broken\n")
    finally:
        close_logging()
    snapshot = read_log_snapshot(tmp_path, backup_count=0)
    assert snapshot.skipped_lines == 1

    configure_logging(_settings(tmp_path))
    try:
        assert log_event(
            logging.ERROR, operation="app.start", outcome="failed",
            error=InvalidInputError("长" * 20000),
        )
    finally:
        close_logging()
    raw_lines = (tmp_path / "app.log").read_text(encoding="utf-8").splitlines()
    last = json.loads(raw_lines[-1])
    assert last["truncated"] is True
    assert len(raw_lines[-1].encode("utf-8")) <= 16 * 1024


def test_unicode_line_separator_stays_inside_one_event(tmp_path):
    """U+2028 等字符不是事件分隔符，不能把一条记录拆成损坏行。"""
    configure_logging(_settings(tmp_path))
    try:
        assert log_event(
            logging.INFO, operation="log.query", outcome="success",
            error=InvalidInputError("分隔符 仍在消息中"),
        )
    finally:
        close_logging()
    snapshot = read_log_snapshot(tmp_path, backup_count=0)
    assert snapshot.skipped_lines == 0
    assert len(snapshot.entries) == 1
    assert " " in snapshot.entries[0].error_message


def test_out_of_range_timestamp_is_skipped_instead_of_failing_snapshot(tmp_path):
    configure_logging(_settings(tmp_path))
    close_logging()
    with (tmp_path / "app.log").open("a", encoding="utf-8") as output:
        output.write(json.dumps({
            "timestamp": "0001-01-01T00:00:00+14:00",
            "level": "INFO",
            "operation": "app.start",
            "outcome": "success",
        }, ensure_ascii=False) + "\n")
        output.write(json.dumps({
            "timestamp": "2026-11-01T00:00:00+00:00",
            "level": "INFO",
            "operation": "app.exit",
            "outcome": "success",
        }, ensure_ascii=False) + "\n")
    snapshot = read_log_snapshot(tmp_path, backup_count=0)
    assert snapshot.skipped_lines == 1
    assert [entry.operation for entry in snapshot.entries] == ["app.exit"]


def test_overlong_operation_cannot_bypass_line_limit(tmp_path):
    configure_logging(_settings(tmp_path))
    try:
        assert log_event(
            logging.INFO, operation="op" * 20000, outcome="success",
        )
    finally:
        close_logging()
    raw_lines = (tmp_path / "app.log").read_text(encoding="utf-8").splitlines()
    last = json.loads(raw_lines[-1])
    assert len(raw_lines[-1].encode("utf-8")) <= 16 * 1024
    assert last["truncated"] is True
    assert len(last["operation"]) <= 64


def test_log_event_returns_false_and_reports_when_write_fails(tmp_path, capsys):
    """文件 handler 写入抛异常时 log_event 返回 False 并向 stderr 输出固定提示，不向外抛出。"""
    configure_logging(_settings(tmp_path))
    try:
        file_handler = logging.getLogger("gym.app").handlers[0]

        def broken_emit(record):
            raise OSError("磁盘已满")

        original_emit, file_handler.emit = file_handler.emit, broken_emit
        try:
            assert log_event(logging.INFO, operation="auth.login", outcome="success") is False
        finally:
            file_handler.emit = original_emit
    finally:
        close_logging()
    assert "操作日志记录失败" in capsys.readouterr().err


def test_rotation_keeps_backups_and_snapshot_reads_them_newest_first(tmp_path):
    """超过 max_bytes 时轮转为 app.log.N；快照读取当前文件与全部备份，最新条目排在最前。"""
    settings = AppSettings(
        database=DatabaseConfig(
            host="localhost", port=3306, database="gym", username="tester", password="",
        ),
        log=LogConfig(directory=tmp_path, backup_count=2, max_bytes=700),
    )
    configure_logging(settings)
    try:
        for index in range(12):
            assert log_event(
                logging.INFO, operation="auth.login", outcome="success", result_id=index,
            )
    finally:
        close_logging()
    names = sorted(
        p.name for p in tmp_path.iterdir()
        if p.name.startswith("app.log") and not p.name.endswith(".lock")
    )
    assert names == ["app.log", "app.log.1", "app.log.2"]
    # 期望值直接从三个文件里的记录推导，不依赖快照结果本身，这样快照漏读任何一份备份、
    # 或为空，都会与期望不一致。文件内按写入顺序（旧→新），备份编号越大越旧；
    # 快照按新→旧返回，所以把「app.log.2, app.log.1, app.log」依次拼接后反转。
    expected_ids = []
    for name in ("app.log.2", "app.log.1", "app.log"):
        for line in (tmp_path / name).read_text(encoding="utf-8").splitlines():
            expected_ids.append(json.loads(line)["result_id"])
    expected_ids.reverse()
    assert expected_ids, "轮转后三个文件不应全部为空"
    result_ids = [entry.result_id for entry in read_log_snapshot(tmp_path, backup_count=2).entries]
    assert result_ids == expected_ids
    # 备份有上限，最早的条目被丢弃；保留下来的严格按新到旧排列且没有空洞。
    assert result_ids[0] == 11 and len(result_ids) < 12
