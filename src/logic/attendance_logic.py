"""AttendanceLogic use-case entry points."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
import sys
from typing import TYPE_CHECKING, Callable

from sqlalchemy.exc import SQLAlchemyError

from src.db.connection import transaction
from src.errors import StorageError
from src.logging import Operation, Outcome, log_event
from src.services.attendance_service import ATTENDANCE_CHANGE_KEY

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        AttendanceChange,
        BookingView,
        ConsumptionView,
    )
    from src.services.attendance_service import AttendanceService


class AttendanceLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        attendance_service: AttendanceService,
    ) -> None:
        self._session_factory = session_factory
        self._attendance_service = attendance_service

    def check_in(self, actor: Actor, booking_id: int) -> BookingView:
        """提交签到，业务失败时回滚，提交未知时附预约编号。"""
        try:
            with self._session_factory() as session, transaction(session, record_id=booking_id):
                return self._attendance_service.check_in(session, actor, booking_id)
        except SQLAlchemyError as exc:
            raise StorageError("保存签到失败") from exc

    def correct_attendance(self, actor: Actor, booking_id: int, present: bool) -> BookingView:
        """提交到场更正，成功提交后记录实际发生的变更。"""
        try:
            with self._session_factory() as session, transaction(session, record_id=booking_id):
                result = self._attendance_service.correct_attendance(session, actor, booking_id, present)
                change = session.info.pop(ATTENDANCE_CHANGE_KEY, None)
        except SQLAlchemyError as exc:
            raise StorageError("保存到场更正失败") from exc
        if change is not None:
            self._log_correction(actor, booking_id, change)
        return result

    @staticmethod
    def _log_correction(actor: Actor, booking_id: int, change: AttendanceChange) -> None:
        try:
            log_event(
                logging.INFO, operation=Operation.ATTENDANCE_CORRECT.value,
                outcome=Outcome.SUCCESS.value, actor_id=actor.account_id,
                result_id=booking_id, attendance_change=change,
            )
        except NotImplementedError:
            # 统一日志接入前，将同一条脱敏事件输出到标准错误。
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "operation": Operation.ATTENDANCE_CORRECT.value,
                "outcome": Outcome.SUCCESS.value,
                "actor_id": actor.account_id,
                "result_id": booking_id,
                "attendance_change": {
                    key: value.isoformat() if isinstance(value, datetime) else value
                    for key, value in asdict(change).items()
                },
            }
            message = json.dumps(payload)
        except Exception:
            message = "操作日志记录失败"
        else:
            return
        try:
            print(message, file=sys.stderr)
        except (OSError, ValueError):
            pass

    def complete(self, actor: Actor, booking_id: int) -> ConsumptionView:
        raise NotImplementedError

    def mark_no_show(self, actor: Actor, booking_id: int) -> BookingView:
        raise NotImplementedError
