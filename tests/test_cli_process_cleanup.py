"""验证交互式测试进程能结束，并在超时、中断后得到回收。"""
from __future__ import annotations

from dataclasses import asdict
import json
import os
import signal
import subprocess
import sys
from unittest.mock import Mock

import pytest

from src.cmd import test as test_command


def test_cli_process_captures_real_help(run_cli):
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "健身房管理系统" in result.stdout
    assert not result.stderr


def test_cli_process_sends_exit_and_closes_input(monkeypatch, run_cli):
    original = subprocess.Popen
    children = []
    def launch(command, **kwargs):
        child = original([sys.executable, "-X", "utf8", "-c",
                          "import sys; print('登录菜单'); assert sys.stdin.read() == '0\\n'"], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(subprocess, "Popen", launch)
    result = run_cli([])
    assert result.returncode == 0
    assert "登录菜单" in result.stdout
    assert all(pipe.closed for pipe in (children[0].stdin, children[0].stdout, children[0].stderr))


@pytest.mark.parametrize("interrupted", [False, True])
def test_hanging_cli_is_reaped_before_error(monkeypatch, run_cli, interrupted):
    original = subprocess.Popen
    children = []
    def launch(command, **kwargs):
        child = original([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
        children.append(child)
        if interrupted:
            communicate = child.communicate
            calls = iter([True, False])
            def interrupt_once(*args, **kw):
                if next(calls):
                    raise KeyboardInterrupt
                return communicate(*args, **kw)
            child.communicate = interrupt_once
        return child
    monkeypatch.setattr(subprocess, "Popen", launch)
    expected = KeyboardInterrupt if interrupted else subprocess.TimeoutExpired
    with pytest.raises(expected):
        run_cli([], timeout=0.1)
    assert children[0].poll() is not None
    assert all(pipe.closed for pipe in (children[0].stdin, children[0].stdout, children[0].stderr))


def test_cli_force_kills_after_terminate_timeout(cli_processes):
    child = Mock()
    child.poll.return_value = None
    child.communicate.side_effect = [subprocess.TimeoutExpired(["cli"], 5), ("", "")]
    cli_processes._stop(child)
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
    assert child.communicate.call_count == 2


@pytest.mark.parametrize("stop_fails", [False, True])
def test_database_cleanup_waits_for_cli_process(monkeypatch, cli_processes, stop_fails):
    fixtures = sys.modules[type(cli_processes).__module__]
    events = []
    def stop():
        events.append("stop-cli")
        if stop_fails:
            raise RuntimeError("进程尚未回收")
    monkeypatch.setattr(cli_processes, "close", stop)
    monkeypatch.setattr(fixtures, "_drop_tables", lambda *_, **__: events.append("clean-db"))
    lifecycle = fixtures.empty_mysql_database.__wrapped__(Mock(), cli_processes)
    next(lifecycle)
    if stop_fails:
        with pytest.raises(RuntimeError, match="尚未回收"):
            lifecycle.close()
    else:
        lifecycle.close()
    assert events == (["clean-db", "stop-cli"] if stop_fails else ["clean-db", "stop-cli", "clean-db"])
    # 用例注入的故障只作用于上述清理路径，结束前恢复共享 fixture 的关闭方法。
    monkeypatch.setattr(cli_processes, "close", type(cli_processes).close.__get__(cli_processes))


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True])
def test_invalid_timeout_does_not_start_process(monkeypatch, run_cli, timeout):
    launch = Mock()
    monkeypatch.setattr(subprocess, "Popen", launch)
    with pytest.raises(ValueError):
        run_cli([], timeout=timeout)
    launch.assert_not_called()


def test_pytest_interrupt_waits_for_cleanup(monkeypatch):
    child = Mock()
    child.poll.return_value = None
    child.wait.return_value = 2
    if os.name != "nt":
        monkeypatch.setattr(os, "killpg", Mock())
    test_command._stop_pytest(child)
    child.wait.assert_called_once_with(timeout=10)
    child.terminate.assert_not_called()


def test_pytest_force_stops_tree_then_reaps(monkeypatch):
    child = Mock(pid=43210)
    child.poll.return_value = None
    child.wait.side_effect = [subprocess.TimeoutExpired(["pytest"], 10), 1]
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    if os.name != "nt":
        monkeypatch.setattr(os, "killpg", Mock())
    test_command._stop_pytest(child)
    if os.name == "nt":
        assert run.call_args.args[0] == ["taskkill", "/PID", "43210", "/T", "/F"]
    else:
        os.killpg.assert_called_with(43210, signal.SIGKILL)
    assert child.wait.call_count == 2


@pytest.mark.mysql
def test_mysql_cli_reaches_login_and_exits(initialized_mysql_database, test_settings, tmp_path, run_cli):
    config = asdict(test_settings.app)
    config["log"]["directory"] = str(config["log"]["directory"])
    config["database"]["password"] = ""
    path = tmp_path / "cli-config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    env = os.environ.copy()
    env["DB_PASSWORD"] = test_settings.app.database.password
    try:
        result = run_cli(["--config", str(path)], env=env)
        assert result.returncode == 0
        assert "1 登录" in result.stdout
        assert "0 退出" in result.stdout
        assert not result.stderr
    finally:
        path.unlink(missing_ok=True)
