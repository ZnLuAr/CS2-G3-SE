"""验证关闭失败能够到达命令入口，且原故障和资源归属仍然保留。"""
from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

import main as entrypoint
from src.app import App
from src.cmd import db as db_command
from src.cmd import test as test_command
from src.config import AppSettings, DatabaseConfig
from src.db import connection
from src.errors.business import AuthenticationError, InvalidState
from src.errors.storage import StorageError
from src.models.contracts import Actor


@pytest.fixture
def settings():
    return AppSettings(database=DatabaseConfig(
        host="localhost", port=3306, database="cleanup_test", username="test", password="",
    ))


@pytest.fixture
def engine(monkeypatch, settings):
    value = MagicMock()
    monkeypatch.setattr("src.config.load_config", lambda *_: settings)
    monkeypatch.setattr(connection, "create_engine", lambda *_: value)
    monkeypatch.setattr(connection, "check_connection", lambda *_: None)
    monkeypatch.setattr(connection, "check_schema", lambda *_, **__: None)
    monkeypatch.setattr(connection, "create_session_factory", lambda *_: Mock())
    return value


def test_dispose_failure_is_safe_and_keeps_cause():
    engine = Mock()
    cause = RuntimeError("mysql://user:secret-password@localhost/gym")
    engine.dispose.side_effect = cause
    with pytest.raises(StorageError) as caught:
        connection.close_engine(engine)
    assert str(caught.value) == "关闭数据库资源失败"
    assert caught.value.__cause__ is cause


@pytest.mark.parametrize("input_result", ["0", EOFError(), KeyboardInterrupt()])
def test_normal_exit_still_returns_zero(monkeypatch, engine, input_result):
    prompt = Mock(return_value=input_result)
    if isinstance(input_result, BaseException):
        prompt.side_effect = input_result
    monkeypatch.setattr("builtins.input", prompt)
    assert entrypoint.main([]) == 0
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("failure", [RuntimeError("private"), EOFError(), KeyboardInterrupt()])
def test_app_keeps_failed_engine_until_retry(settings, engine, failure):
    app = App(settings)
    app.start()
    app.set_actor(Actor(account_id=1, role="admin", member_id=None, coach_id=None))
    engine.dispose.side_effect = [failure, None]
    expected = StorageError if type(failure) is RuntimeError else type(failure)
    with pytest.raises(expected):
        app.close()
    assert app._engine is engine
    with pytest.raises(AuthenticationError):
        app.get_actor()
    with pytest.raises(InvalidState):
        app.run()
    with pytest.raises(InvalidState):
        app.start()
    app.close()
    app.close()
    assert app._engine is None
    assert engine.dispose.call_count == 2


@pytest.mark.parametrize("startup_fails", [False, True])
@pytest.mark.parametrize("failure", [RuntimeError("secret-password"), EOFError(), KeyboardInterrupt()])
def test_main_reports_real_dispose_failure(monkeypatch, engine, capsys, startup_fails, failure):
    engine.dispose.side_effect = failure
    if startup_fails:
        monkeypatch.setattr(connection, "check_connection", Mock(side_effect=StorageError("连接检查失败")))
    monkeypatch.setattr("builtins.input", lambda *_: "0")
    assert entrypoint.main([]) == 1
    output = capsys.readouterr()
    assert "关闭应用资源失败" in output.err
    assert ("连接检查失败" in output.err) == startup_fails
    assert "secret-password" not in output.out + output.err
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("success", [False, True])
def test_db_command_preserves_result_and_reports_close_failure(monkeypatch, engine, capsys, success):
    engine.dispose.side_effect = RuntimeError("secret-password")
    if success:
        monkeypatch.setattr(db_command, "init_database", lambda _: db_command.InitResult(tables_created=18, schema_version=1))
    else:
        monkeypatch.setattr(connection, "check_connection", Mock(side_effect=StorageError("原始连接故障")))
    assert db_command.main(["init"]) == 1
    output = capsys.readouterr()
    assert "关闭数据库资源失败" in output.err
    assert ("成功创建 18 张表" in output.out) == success
    assert ("原始连接故障" in output.err) != success
    assert "secret-password" not in output.out + output.err


@pytest.mark.parametrize("tests_pass", [False, True])
def test_test_command_releases_lock_before_failed_dispose(monkeypatch, settings, engine, capsys, tests_pass):
    monkeypatch.setattr(test_command, "load_test_config", lambda _: test_command.TestSettings(test_database=True, app=settings))
    engine.connect.return_value.__enter__.return_value.execute.return_value.scalar_one.return_value = 1
    events = []
    def run_tests(*_):
        events.append("tests-finished")
        if not tests_pass:
            raise StorageError("原始测试故障")
        return 0
    def dispose():
        events.append("dispose")
        raise RuntimeError("secret-password")
    engine.dispose.side_effect = dispose
    monkeypatch.setattr(test_command, "_run_pytest", run_tests)
    assert test_command.main(["mysql", "--config", "test-config.json"]) == 1
    statements = engine.connect.return_value.__enter__.return_value.execute.call_args_list
    assert "RELEASE_LOCK" in str(statements[-1].args[0])
    assert events == ["tests-finished", "dispose"]
    output = capsys.readouterr()
    assert "关闭测试数据库资源失败" in output.err
    assert ("原始测试故障" in output.err) != tests_pass
    assert "secret-password" not in output.out + output.err
