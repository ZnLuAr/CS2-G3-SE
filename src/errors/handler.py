"""将 CLI 与 TUI 的异常转换为安全提示和界面动作。"""

from __future__ import annotations

import logging
import sys

from src.errors.base import ErrorAction, ErrorResult, GymError
from src.errors.business import AuthenticationError, ResourceError
from src.errors.storage import OutcomeUnknownError, StorageError
from src.logging.events import Outcome, log_event


def handle_error(
    error: Exception,
    *,
    operation: str,
    actor_id: int | None = None,
    request_id: str | None = None,
    fatal: bool = False,
) -> ErrorResult:
    """分类异常，返回可展示的提示、界面动作和可选核实编号。"""
    action: ErrorAction
    record_id = None
    if isinstance(error, OutcomeUnknownError):
        action, level, outcome = "verify", logging.ERROR, Outcome.UNKNOWN
        message = error.message
        request_id = error.request_id or request_id
        record_id = error.record_id
    elif isinstance(error, AuthenticationError):
        action, level, outcome = "login", logging.WARNING, Outcome.REJECTED
        message = error.message
    elif isinstance(error, (StorageError, ResourceError)):
        action, level, outcome = "exit", logging.ERROR, Outcome.FAILED
        message = error.message
    elif isinstance(error, GymError):
        action, level, outcome = "continue", logging.WARNING, Outcome.REJECTED
        message = error.message
    else:
        action, level, outcome = "exit", logging.ERROR, Outcome.FAILED
        message = "操作失败，请联系维护人员检查。"

    try:
        log_event(
            level, operation=operation, outcome=outcome.value, actor_id=actor_id,
            request_id=request_id, result_id=record_id, error=error,
        )
    except Exception:
        try:
            print("操作日志记录失败", file=sys.stderr)
        except (OSError, ValueError):
            pass
    return ErrorResult(
        message=message, action="exit" if fatal else action,
        request_id=request_id, record_id=record_id,
    )
