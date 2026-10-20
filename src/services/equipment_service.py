"""器械服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class EquipmentService:
    """器械服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md的返回、异常、权限和事务约定。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_equipment(self, session: Session, actor: Actor, data: EquipmentInput) -> EquipmentView:
        """创建器械台账。

        返回：EquipmentView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.create_equipment 尚未实现")

    def update_equipment(
        self, session: Session,
        actor: Actor,
        equipment_id: int,
        data: EquipmentUpdateInput,
    ) -> EquipmentView:
        """修改器械资料。

        返回：EquipmentView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.update_equipment 尚未实现")

    def get_equipment(self, session: Session, actor: Actor, equipment_id: int) -> EquipmentView:
        """查询器械详情。

        所有已登录角色可查看器械基础资料，以便提交报修。
        返回：EquipmentView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.get_equipment 尚未实现")

    def list_equipment(self, session: Session, actor: Actor, query: EquipmentQuery) -> Page[EquipmentView]:
        """分页查询器械。

        所有已登录角色可查询器械基础资料；空结果返回空 Page。
        返回：Page[EquipmentView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.list_equipment 尚未实现")

    def report_fault(self, session: Session, actor: Actor, equipment_id: int, description: str) -> MaintenanceView:
        """登记器械报修。

        返回：MaintenanceView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.report_fault 尚未实现")

    def finish_maintenance(self, session: Session, actor: Actor, maintenance_id: int) -> MaintenanceView:
        """完成维修并恢复器械状态。

        先取得器械编号，再锁器械和维修记录；锁内复核未完成及 maintenance 状态。
        返回：MaintenanceView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.finish_maintenance 尚未实现")

    def list_maintenance(
        self, session: Session,
        actor: Actor,
        equipment_id: int,
        paging: PageRequest,
    ) -> Page[MaintenanceView]:
        """分页查询维修历史。

        仅管理员可查看含操作人字段的维修明细。
        返回：Page[MaintenanceView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.list_maintenance 尚未实现")

    def retire_equipment(self, session: Session, actor: Actor, equipment_id: int) -> EquipmentView:
        """报废器械并保留历史。

        返回：EquipmentView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("EquipmentService.retire_equipment 尚未实现")
