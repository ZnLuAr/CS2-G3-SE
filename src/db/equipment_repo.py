"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import (
    EquipmentInput,
    EquipmentQuery,
    EquipmentStatus,
    EquipmentUpdateInput,
    EquipmentView,
    MaintenanceView,
    Page,
    PageRequest,
)
from src.models.equipment import Equipment

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class EquipmentRepository:
    """器械数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("EquipmentRepository.__init__ 尚未实现")

    def get(self, equipment_id: int) -> EquipmentView | None:
        """读取器械详情。

        返回：EquipmentView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("EquipmentRepository.get 尚未实现")

    def list(self, query: EquipmentQuery) -> Page[EquipmentView]:
        """按编号、名称、位置和状态筛选，再按 id 升序稳定分页。

        返回：Page[EquipmentView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("EquipmentRepository.list 尚未实现")

    def create(self, data: EquipmentInput) -> EquipmentView:
        """保存器械资产资料。

        返回：EquipmentView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("EquipmentRepository.create 尚未实现")

    def update(self, equipment_id: int, data: EquipmentUpdateInput) -> EquipmentView:
        """更新名称和位置，不修改资产编号与状态。

        返回：EquipmentView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("EquipmentRepository.update 尚未实现")

    def set_status(self, equipment_id: int, status: EquipmentStatus) -> EquipmentView:
        """写器械状态，与维修记录共用服务事务。

        返回：EquipmentView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("EquipmentRepository.set_status 尚未实现")

    def lock(self, equipment_id: int) -> Equipment | None:
        """锁定并读取器械，协调报修与修复。

        返回：Equipment | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("EquipmentRepository.lock 尚未实现")


class MaintenanceRepository:
    """维修记录数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("MaintenanceRepository.__init__ 尚未实现")

    def get(self, maintenance_id: int) -> MaintenanceView | None:
        """读取指定维修记录。

        返回：MaintenanceView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MaintenanceRepository.get 尚未实现")

    def lock(self, maintenance_id: int) -> MaintenanceView | None:
        """在当前事务中锁定并读取维修记录，供完成维修时复核状态。

        返回：MaintenanceView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MaintenanceRepository.lock 尚未实现")

    def list(self, equipment_id: int, paging: PageRequest) -> Page[MaintenanceView]:
        """按 reported_at、id 降序稳定分页查询。

        返回：Page[MaintenanceView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MaintenanceRepository.list 尚未实现")

    def create(
        self,
        *,
        equipment_id: int,
        description: str,
        reported_at: datetime,
        operator_id: int,
    ) -> MaintenanceView:
        """保存报修记录，与器械状态共用事务。

        返回：MaintenanceView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MaintenanceRepository.create 尚未实现")

    def finish(
        self,
        maintenance_id: int,
        *,
        resolved_at: datetime,
        resolved_by: int,
    ) -> MaintenanceView:
        """保存修复时间和操作者，不自行提交。

        返回：MaintenanceView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MaintenanceRepository.finish 尚未实现")
