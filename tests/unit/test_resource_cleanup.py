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
from src.errors.business import AuthenticationError, InvalidState, ResourceError
from src.errors.storage import OutcomeUnknownError, StorageError
from src.logic import LogicBundle
from src.models.contracts import Actor


@pytest.fixture
def settings():
    return AppSettings(database=DatabaseConfig(
        host="localhost", port=3306, database="cleanup_test", username="test", password="",
    ))


@pytest.fixture
def worker(monkeypatch):
    """生命周期测试使用任务替身，独立验证线程调度的测试位于 test_worker。"""
    value = Mock()
    monkeypatch.setattr("src.tasks.worker.PeriodicWorker", Mock(return_value=value))
    return value


@pytest.fixture
def engine(monkeypatch, settings, worker):
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


def test_commit_failure_preserves_verification_ids():
    """提交确认丢失时，界面核实所需的编号不能被事务包装器丢掉。"""
    session = Mock()
    cause = RuntimeError("connection lost during commit")
    session.commit.side_effect = cause

    with pytest.raises(OutcomeUnknownError) as caught:
        with connection.transaction(session, request_id="request-123", record_id=42):
            pass

    assert caught.value.request_id == "request-123"
    assert caught.value.record_id == 42
    assert caught.value.__cause__ is cause
    session.rollback.assert_called_once()


def test_flush_constraint_failure_is_not_reported_as_unknown_commit():
    """flush 已知失败表示没有提交，服务仍需看见原约束异常。"""
    session = Mock()
    cause = RuntimeError("known constraint failure")
    session.flush.side_effect = cause

    with pytest.raises(RuntimeError) as caught:
        with connection.transaction(session, request_id="request-123"):
            pass

    assert caught.value is cause
    session.commit.assert_not_called()
    session.rollback.assert_called_once()


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


def test_app_assembles_logic_bundle_for_cli_handlers(settings, engine):
    app = App(settings)
    app.start()
    try:
        bundle = app._logic_bundle
        handlers = app._cli._handlers
        assert isinstance(bundle, LogicBundle)
        assert handlers.auth._logic is bundle.auth
        assert handlers.member._logic is bundle.members
        assert handlers.product._product_logic is bundle.products
        assert handlers.product._sales_logic is bundle.sales
        assert handlers.product._entitlement_logic is bundle.entitlements
        assert handlers.product._access_logic is bundle.access
        assert handlers.course._logic is bundle.courses
        assert handlers.booking._logic is bundle.reservations
        assert handlers.booking._course_logic is bundle.courses
        assert handlers.booking._entitlement_logic is bundle.entitlements
        assert handlers.attendance._logic is bundle.attendance
        assert handlers.review._logic is bundle.reviews
        assert handlers.equipment._logic is bundle.equipment
        assert handlers.measurement._logic is bundle.measurements
        assert handlers.report._logic is bundle.reports
    finally:
        app.close()


def test_app_starts_worker_by_default_and_stops_before_database(settings, engine, worker):
    """默认 CLI 也装配周期任务，关停时先排空任务再释放引擎。"""
    app = App(settings)
    app.start()
    assert app._worker is worker
    worker.start.assert_called_once()

    def stop(*, timeout):
        assert timeout == 30
        engine.dispose.assert_not_called()

    worker.stop.side_effect = stop
    app.close()
    worker.stop.assert_called_once_with(timeout=30)
    engine.dispose.assert_called_once()


def test_app_can_disable_worker_explicitly(settings, engine, worker):
    app = App(settings)
    app.start(with_worker=False)
    try:
        assert app._worker is None
        worker.start.assert_not_called()
    finally:
        app.close()
    worker.stop.assert_not_called()


def test_app_worker_timeout_preserves_live_resources_for_retry(settings, engine, worker):
    """任务仍在运行时保留业务入口和引擎，下一次 close 可以继续回收。"""
    app = App(settings)
    app.start()
    bundle = app.logic_bundle
    worker.stop.side_effect = [ResourceError("后台任务未停止"), None]

    with pytest.raises(ResourceError):
        app.close()
    assert app._worker is worker
    assert app.logic_bundle is bundle
    assert app._engine is engine
    engine.dispose.assert_not_called()

    app.close()
    assert app._worker is None
    assert app._engine is None
    engine.dispose.assert_called_once()


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
        monkeypatch.setattr(db_command, "init_database", lambda _: db_command.InitResult(tables_created=18, schema_version=2))
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
