"""EquipmentLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        EquipmentInput,
        EquipmentQuery,
        EquipmentUpdateInput,
        EquipmentView,
        MaintenanceView,
        Page,
        PageRequest,
    )
    from src.services.equipment_service import EquipmentService


class EquipmentLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        equipment_service: EquipmentService,
    ) -> None:
        self._session_factory = session_factory
        self._equipment_service = equipment_service

    def create_equipment(self, actor: Actor, data: EquipmentInput) -> EquipmentView:
        raise NotImplementedError

    def get_equipment(self, actor: Actor, equipment_id: int) -> EquipmentView:
        raise NotImplementedError

    def list_equipment(self, actor: Actor, query: EquipmentQuery) -> Page[EquipmentView]:
        raise NotImplementedError

    def update_equipment(self, actor: Actor, equipment_id: int, data: EquipmentUpdateInput) -> EquipmentView:
        raise NotImplementedError

    def report_fault(self, actor: Actor, equipment_id: int, description: str) -> MaintenanceView:
        raise NotImplementedError

    def finish_maintenance(self, actor: Actor, maintenance_id: int) -> MaintenanceView:
        raise NotImplementedError

    def retire_equipment(self, actor: Actor, equipment_id: int) -> EquipmentView:
        raise NotImplementedError

    def list_maintenance(self, actor: Actor, equipment_id: int, paging: PageRequest) -> Page[MaintenanceView]:
        raise NotImplementedError
