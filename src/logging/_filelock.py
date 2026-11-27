"""跨进程独占文件锁；Windows 使用 msvcrt，其他平台使用 fcntl。"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import os
import time
from typing import Iterator

_POLL_SECONDS = 0.05


@contextmanager
def exclusive_file_lock(path: Path, *, timeout: float = 5.0) -> Iterator[None]:
    """在 path 上取得跨进程独占锁。

    输入：锁文件路径和最长等待秒数。
    返回：上下文管理器；进入后持有锁，退出时释放。
    异常：等待超时抛 TimeoutError；目录或锁文件无法打开抛 OSError。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        _acquire(handle, timeout)
        try:
            yield
        finally:
            _release(handle)
    finally:
        handle.close()


def _acquire(handle, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                if handle.read(1) == b"":
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError("等待文件锁超时")
            time.sleep(_POLL_SECONDS)


def _release(handle) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
