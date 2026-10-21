"""体测用例入口及会话、事务生命周期。"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable

from sqlalchemy.exc import SQLAlchemyError

from src.db.connection import transaction
from src.errors import OutcomeUnknownError, StorageError
from src.logging import Operation, Outcome, log_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        MeasurementComparison,
        MeasurementInput,
        MeasurementQuery,
        MeasurementView,
        Page,
    )
    from src.services.measurement_service import MeasurementService


class MeasurementLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        measurement_service: MeasurementService,
    ) -> None:
        self._session_factory = session_factory
        self._measurement_service = measurement_service

    def record(self, actor: Actor, data: MeasurementInput) -> MeasurementView:
        """提交一次体测录入；失败回滚，提交未知时附上记录编号供详情核实。"""
        result = None
        try:
            with self._session_factory() as session:
                try:
                    with transaction(session):
                        result = self._measurement_service.record(session, actor, data)
                except OutcomeUnknownError as exc:
                    if result is not None:
                        exc.record_id = result.id
                    raise
        except SQLAlchemyError as exc:
            raise StorageError("保存体测记录失败") from exc
        try:
            log_event(
                logging.INFO, operation=Operation.MEASUREMENT_RECORD.value,
                outcome=Outcome.SUCCESS.value, actor_id=actor.account_id, result_id=result.id,
            )
        except Exception:
            print("操作日志记录失败", file=sys.stderr)
        return result

    def get_measurement(self, actor: Actor, measurement_id: int) -> MeasurementView:
        """用短事务读取授权详情，退出时释放身份锁和会话。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._measurement_service.get_measurement(session, actor, measurement_id)
        except SQLAlchemyError as exc:
            raise StorageError("查询体测记录失败") from exc

    def list_measurements(self, actor: Actor, query: MeasurementQuery) -> Page[MeasurementView]:
        """在同一业务快照内读取授权总数和当前页。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._measurement_service.list_measurements(session, actor, query)
        except SQLAlchemyError as exc:
            raise StorageError("查询体测历史失败") from exc

    def compare(self, actor: Actor, before_id: int, after_id: int) -> MeasurementComparison:
        """在同一业务快照和授权截止内读取并比较两条记录。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._measurement_service.compare(session, actor, before_id, after_id)
        except SQLAlchemyError as exc:
            raise StorageError("对比体测记录失败") from exc
