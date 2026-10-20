"""以单个线程调度独立的周期任务。"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import Event, Lock, Thread
from time import monotonic
from typing import Callable

from src.errors.business import InvalidState, ResourceError


@dataclass(frozen=True, kw_only=True)
class PeriodicTask:
    """周期任务名称、周期秒数和系统 Logic 回调。"""

    name: str
    interval_seconds: float
    callback: Callable[[], None]

    def __post_init__(self) -> None:
        if not self.name or self.interval_seconds <= 0:
            raise ValueError("周期任务必须有名称和正周期")


class PeriodicWorker:
    """在独立线程中依次运行任务，并隔离单个任务异常。"""

    def __init__(self, tasks: tuple[PeriodicTask, ...]) -> None:
        names = [task.name for task in tasks]
        if not tasks or len(names) != len(set(names)):
            raise ValueError("周期任务必须非空且名称唯一")
        self._tasks = tasks
        self._stop_event = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._logger = logging.getLogger("src.tasks.worker")

    def start(self) -> None:
        """启动唯一 Worker 线程；重复启动抛 InvalidState。"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise InvalidState("后台任务已经启动")
            self._stop_event.clear()
            thread = Thread(
                target=self._run,
                name="gym-periodic-worker",
                daemon=True,
            )
            self._thread = thread
            try:
                thread.start()
            except BaseException:
                self._thread = None
                raise

    def stop(self, *, timeout: float = 30) -> None:
        """停止接收周期任务并等待当前回调结束；超时抛 ResourceError。"""
        with self._lock:
            thread = self._thread
            if thread is None:
                return
            self._stop_event.set()
        thread.join(timeout)
        if thread.is_alive():
            raise ResourceError("后台任务未能在规定时间内停止")
        with self._lock:
            if self._thread is thread:
                self._thread = None

    def _run(self) -> None:
        next_runs = {task.name: monotonic() for task in self._tasks}
        while not self._stop_event.is_set():
            now = monotonic()
            due = [task for task in self._tasks if next_runs[task.name] <= now]
            if not due:
                wait_seconds = min(next_runs.values()) - now
                self._stop_event.wait(max(0, wait_seconds))
                continue
            for task in due:
                if self._stop_event.is_set():
                    break
                try:
                    task.callback()
                except Exception as exc:
                    self._logger.error(
                        "后台任务执行失败",
                        extra={"task_name": task.name, "error_type": type(exc).__name__},
                    )
                next_runs[task.name] = monotonic() + task.interval_seconds
