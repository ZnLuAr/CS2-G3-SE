"""操作名称、结果类别与脱敏事件记录接口。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import sys
import traceback
from typing import Any

from src.models.contracts import AttendanceChange

MAX_LOG_BYTES = 16 * 1024
MAX_OPERATION_CHARS = 64
MAX_REQUEST_ID_CHARS = 64
MAX_OUTCOME_CHARS = 32
# handler 还会追加一个换行符，按整行（含终止符）不超过 16 KiB 计算。
MAX_PAYLOAD_BYTES = MAX_LOG_BYTES - 1


class Operation(str, Enum):
    """操作名称枚举（所有需要记日志的操作）。"""

    # 启动与关闭
    APP_START = "app.start"
    APP_EXIT = "app.exit"

    # 账号
    ACCOUNT_CREATE = "account.create"
    ACCOUNT_UPDATE = "account.update"
    ACCOUNT_LINK = "account.link"
    ACCOUNT_QUERY = "account.query"
    ACCOUNT_ACTIVATE = "account.activate"
    ACCOUNT_DEACTIVATE = "account.deactivate"
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOG_QUERY = "log.query"

    # 会员
    MEMBER_CREATE = "member.create"
    MEMBER_UPDATE = "member.update"
    MEMBER_ACTIVATE = "member.activate"
    MEMBER_DEACTIVATE = "member.deactivate"

    # 产品销售
    PRODUCT_SELL = "product.sell"

    # 入场
    ENTRY_REGISTER = "entry.register"

    # 教练
    COACH_CREATE = "coach.create"
    COACH_UPDATE = "coach.update"

    # 课程和排课
    COURSE_CREATE = "course.create"
    COURSE_UPDATE = "course.update"
    SESSION_CREATE = "session.create"
    SESSION_CANCEL = "session.cancel"
    SESSION_COMPLETE = "session.complete"

    # 预约
    BOOKING_CREATE = "booking.create"
    BOOKING_CANCEL = "booking.cancel"

    # 签到与消课
    ATTENDANCE_CHECKIN = "attendance.checkin"
    ATTENDANCE_CORRECT = "attendance.correct"
    ATTENDANCE_COMPLETE = "attendance.complete"
    ATTENDANCE_NOSHOW = "attendance.noshow"

    # 评价
    REVIEW_CREATE = "review.create"

    # 体测
    MEASUREMENT_RECORD = "measurement.record"

    # 器械
    EQUIPMENT_CREATE = "equipment.create"
    EQUIPMENT_UPDATE = "equipment.update"
    EQUIPMENT_REPORT_FAULT = "equipment.report_fault"
    EQUIPMENT_FINISH_MAINTENANCE = "equipment.finish_maintenance"
    EQUIPMENT_RETIRE = "equipment.retire"


class Outcome(str, Enum):
    """操作结果类型。"""

    SUCCESS = "success"
    REJECTED = "rejected"
    FAILED = "failed"
    UNKNOWN = "unknown"


def report_log_failure(operation: str, error: Exception) -> None:
    """向标准错误流报告操作名和日志异常类型，保留原业务结果。"""
    try:
        print(f"操作日志记录失败（{operation}，{type(error).__name__}）", file=sys.stderr)
    except (OSError, ValueError):
        return


def log_event(
    level: int,
    *,
    operation: str,
    outcome: str,
    actor_id: int | None = None,
    request_id: str | None = None,
    result_id: int | None = None,
    error: Exception | None = None,
    attendance_change: AttendanceChange | None = None,
) -> bool:
    """记录一条脱敏操作日志。

    输入：日志级别、固定操作名、结果类别、非敏感编号、异常和可选签到变化。
    返回：写入成功返回 True；运行期写入失败返回 False，并向标准错误输出固定提示。
    异常：不抛出。日志故障不能传播到已完成的业务调用。
    数据变更：向已配置的 app.log 追加一行不超过 16 KiB 的 UTF-8 JSON。
    """
    from src.logging.lifecycle import get_logger

    operation_name = _text_value(operation)
    logger = get_logger()
    if logger is None:
        report_log_failure(operation_name, RuntimeError("日志系统未初始化"))
        return False
    try:
        truncated = False
        if len(operation_name) > MAX_OPERATION_CHARS:
            operation_name = operation_name[:MAX_OPERATION_CHARS]
            truncated = True
        outcome_name = _text_value(outcome)
        if len(outcome_name) > MAX_OUTCOME_CHARS:
            outcome_name = outcome_name[:MAX_OUTCOME_CHARS]
            truncated = True
        request_id_value = request_id
        if isinstance(request_id_value, str) and len(request_id_value) > MAX_REQUEST_ID_CHARS:
            request_id_value = request_id_value[:MAX_REQUEST_ID_CHARS]
            truncated = True
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": logging.getLevelName(level),
            "operation": operation_name,
            "outcome": outcome_name,
            "actor_id": actor_id,
            "request_id": request_id_value,
            "result_id": result_id,
            "error_type": None,
            "error_message": None,
            "attendance_change": _attendance_payload(attendance_change),
            "frames": [],
            "truncated": truncated,
        }
        if error is not None:
            payload["error_type"], payload["error_message"] = _error_fields(error)
            payload["frames"] = _frames(error)
        text, _ = _fit(payload)
        logger.log(level, text)
    except Exception as exc:
        report_log_failure(operation_name, exc)
        return False
    return True


def _text_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _attendance_payload(value: AttendanceChange | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "before": value.before,
        "after": value.after,
        "before_checked_in_at": _timestamp(value.before_checked_in_at),
        "after_checked_in_at": _timestamp(value.after_checked_in_at),
        "corrected_at": _timestamp(value.corrected_at),
    }


def _error_fields(error: Exception) -> tuple[str, str | None]:
    """项目异常只记录安全的中文消息；未知异常不记录 str(error)。"""
    from src.errors.base import GymError

    message = error.message if isinstance(error, GymError) else None
    return type(error).__name__, message


def _frames(error: Exception) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    for frame in traceback.extract_tb(error.__traceback__):
        frames.append({
            "filename": Path(frame.filename).name,
            "line_number": frame.lineno,
            "function_name": frame.name,
        })
    return frames


def _serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def _encoded_size(text: str) -> int:
    return len(text.encode("utf-8"))


def _fit(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """保证单条日志（含换行）不超过 16 KiB；超限时依次丢堆栈、截断错误消息。"""
    text = _serialize(payload)
    if _encoded_size(text) <= MAX_PAYLOAD_BYTES:
        return text, payload

    payload["truncated"] = True
    payload["frames"] = []
    text = _serialize(payload)
    if _encoded_size(text) <= MAX_PAYLOAD_BYTES:
        return text, payload

    message = payload.get("error_message")
    if isinstance(message, str):
        low, high = 0, len(message)
        while low < high:
            middle = (low + high + 1) // 2
            payload["error_message"] = message[:middle]
            text = _serialize(payload)
            if _encoded_size(text) <= MAX_PAYLOAD_BYTES:
                low = middle
            else:
                high = middle - 1
        payload["error_message"] = message[:low]
        text = _serialize(payload)
        if _encoded_size(text) <= MAX_PAYLOAD_BYTES:
            return text, payload

    payload["error_message"] = None
    text = _serialize(payload)
    if _encoded_size(text) <= MAX_PAYLOAD_BYTES:
        return text, payload

    minimal = {
        "timestamp": payload["timestamp"],
        "level": payload["level"],
        "operation": str(payload["operation"])[:MAX_OPERATION_CHARS],
        "outcome": str(payload["outcome"])[:MAX_OUTCOME_CHARS],
        "truncated": True,
        "frames": [],
    }
    return _serialize(minimal), minimal
