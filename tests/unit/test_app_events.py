"""SYS-06/LOG-02：启动与退出事件按实际结果记录。"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, Mock

import pytest

from src.app import App
from src.config import AppSettings, DatabaseConfig, LogConfig
from src.db import connection
from src.errors.storage import StorageError
from src.logging import close_logging


@pytest.fixture
def settings(tmp_path):
    return AppSettings(
        database=DatabaseConfig(
            host="localhost", port=3306, database="events_test", username="test", password="",
        ),
        log=LogConfig(directory=tmp_path),
    )


@pytest.fixture
def worker(monkeypatch):
    value = Mock()
    monkeypatch.setattr("src.tasks.worker.PeriodicWorker", Mock(return_value=value))
    return value


@pytest.fixture
def engine(monkeypatch, worker):
    value = MagicMock()
    monkeypatch.setattr(connection, "create_engine", lambda *_: value)
    monkeypatch.setattr(connection, "check_connection", lambda *_: None)
    monkeypatch.setattr(connection, "check_schema", lambda *_, **__: None)
    monkeypatch.setattr(connection, "create_session_factory", lambda *_: Mock())
    return value


@pytest.fixture
def events(monkeypatch):
    recorded = []

    def record(level, *, operation, outcome, **_):
        recorded.append((level, operation, outcome))
        return True

    monkeypatch.setattr("src.app.log_event", record)
    yield recorded
    close_logging()


def test_start_success_is_logged_after_all_resources_are_ready(settings, engine, worker, events):
    order = []

    def start_worker():
        # worker 启动时装配已完成，start 的成功日志尚未写入；
        # 若把 app.start 提前到装配之前，这里会看到事件而不是空列表。
        assert events == []
        order.append("worker.start")

    worker.start.side_effect = start_worker
    app = App(settings)
    app.start()
    try:
        assert order == ["worker.start"]
        assert events == [(logging.INFO, "app.start", "success")]
    finally:
        app.close()


def test_start_failure_logs_failed_and_reraises(settings, engine, events, monkeypatch):
    monkeypatch.setattr(
        connection, "check_connection", Mock(side_effect=StorageError("连接检查失败")),
    )
    app = App(settings)
    with pytest.raises(StorageError):
        app.start()
    assert events == [(logging.ERROR, "app.start", "failed")]
    app._engine = None


def test_close_logs_failed_when_database_release_fails(settings, engine, events, monkeypatch):
    app = App(settings)
    app.start()
    monkeypatch.setattr(
        connection, "close_engine", Mock(side_effect=StorageError("关闭数据库资源失败")),
    )
    with pytest.raises(StorageError):
        app.close()
    assert events == [
        (logging.INFO, "app.start", "success"),
        (logging.ERROR, "app.exit", "failed"),
    ]
    app._engine = None


def test_close_logs_success_after_database_release(settings, engine, events):
    app = App(settings)
    app.start()
    app.close()
    assert events == [
        (logging.INFO, "app.start", "success"),
        (logging.INFO, "app.exit", "success"),
    ]
