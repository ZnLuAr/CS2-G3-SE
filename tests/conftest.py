"""装配后端测试资源；导入时不读取配置或连接数据库。"""
from __future__ import annotations

import os
from pathlib import Path
import signal

import pytest

pytest_plugins = ("tests.support.cli", "tests.support.mysql")


def _interrupt_tests(signum, frame):
    raise KeyboardInterrupt


def pytest_configure(config):
    """Windows 测试进程组用 Ctrl+Break 请求正常清理。"""
    if os.name == "nt":
        config._gym_previous_sigbreak = signal.signal(signal.SIGBREAK, _interrupt_tests)


def pytest_unconfigure(config):
    if os.name == "nt":
        signal.signal(signal.SIGBREAK, config._gym_previous_sigbreak)


def pytest_collection_modifyitems(items):
    """集成目录自动标记 MySQL；直接 pytest 时给出显式模式提示。"""
    integration = Path(__file__).resolve().parent / "integration"
    enabled = os.environ.get("GYM_TEST_MODE") in {"mysql", "all"}
    for item in items:
        if integration in Path(item.path).resolve().parents:
            item.add_marker(pytest.mark.mysql)
        if not enabled and item.get_closest_marker("mysql") is not None:
            item.add_marker(pytest.mark.skip(
                reason="通过 python -m src.cmd.test mysql/all --config 指定独立测试库"
            ))
