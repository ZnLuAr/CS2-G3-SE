"""CLI 子进程 fixture：超时和中断后先回收资源。"""
from __future__ import annotations

import math
import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


class _CliProcesses:
    """管理本用例的 CLI 进程，数据库 fixture 清理前先回收它们。"""

    def __init__(self):
        self._children: list[subprocess.Popen[str]] = []

    @staticmethod
    def _stop(child: subprocess.Popen[str]) -> None:
        # 清理期间的再次 Ctrl+C 留到进程回收后；避免遗留仍访问测试库的进程。
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            if child.poll() is None:
                try:
                    child.terminate()
                except ProcessLookupError:
                    pass
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate()
        finally:
            signal.signal(signal.SIGINT, previous)

    @staticmethod
    def _close_pipes(child: subprocess.Popen[str]) -> None:
        for pipe in (child.stdin, child.stdout, child.stderr):
            if pipe is not None:
                pipe.close()

    def close(self) -> None:
        for child in tuple(self._children):
            self._stop(child)
            self._close_pipes(child)
            self._children.remove(child)

    def run_cli_process(
        self, argv: list[str], *, env: dict[str, str] | None = None,
        timeout: float = 120.0,
    ) -> subprocess.CompletedProcess[str]:
        """发送退出选项并收集结果；超时或中断时先回收进程再传播异常。"""
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("CLI 测试超时必须是有限正数")
        command = [sys.executable, "-X", "utf8", str(ROOT / "main.py"), *argv]
        child = subprocess.Popen(
            command, cwd=ROOT, env=None if env is None else env.copy(), shell=False,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8",
        )
        self._children.append(child)
        try:
            stdout, stderr = child.communicate(input="0\n", timeout=timeout)
            return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
        except BaseException:
            self._stop(child)
            raise
        finally:
            if child.poll() is not None:
                self._close_pipes(child)
                self._children.remove(child)


@pytest.fixture
def cli_processes():
    """提供本用例的进程资源；用例失败时同样执行回收。"""
    processes = _CliProcesses()
    try:
        yield processes
    finally:
        processes.close()


@pytest.fixture
def run_cli(cli_processes):
    """调用 run_cli(argv, env=..., timeout=...) 运行受控 CLI 子进程。"""
    return cli_processes.run_cli_process
