"""MeasurementLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

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
        raise NotImplementedError

    def get_measurement(self, actor: Actor, measurement_id: int) -> MeasurementView:
        raise NotImplementedError

    def list_measurements(self, actor: Actor, query: MeasurementQuery) -> Page[MeasurementView]:
        raise NotImplementedError

    def compare(self, actor: Actor, before_id: int, after_id: int) -> MeasurementComparison:
        raise NotImplementedError
