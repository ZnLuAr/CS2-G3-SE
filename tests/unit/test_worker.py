from __future__ import annotations

from threading import Event

import pytest

from src.errors.business import ResourceError
from src.tasks.worker import PeriodicTask, PeriodicWorker


def test_worker_runs_other_tasks_after_one_task_fails(caplog):
    completed = Event()

    def failing_task() -> None:
        raise RuntimeError("sensitive database detail")

    worker = PeriodicWorker((
        PeriodicTask(name="fails", interval_seconds=60, callback=failing_task),
        PeriodicTask(name="completes", interval_seconds=60, callback=completed.set),
    ))
    worker.start()
    assert completed.wait(1)
    worker.stop(timeout=1)

    assert "后台任务执行失败" in caplog.text
    assert "sensitive database detail" not in caplog.text


def test_worker_stop_timeout_keeps_worker_available_for_retry():
    entered = Event()
    release = Event()

    def blocked_task() -> None:
        entered.set()
        release.wait(1)

    worker = PeriodicWorker((
        PeriodicTask(name="blocked", interval_seconds=60, callback=blocked_task),
    ))
    worker.start()
    assert entered.wait(1)
    with pytest.raises(ResourceError):
        worker.stop(timeout=0.01)

    release.set()
    worker.stop(timeout=1)
    worker.stop(timeout=1)
