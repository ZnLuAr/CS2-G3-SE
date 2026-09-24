"""按业务划分的 CLI 交互接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.equipment_service import EquipmentService


class EquipmentHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: EquipmentService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        self._service = service
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    def create_equipment(self) -> None:
        """组织 EquipmentService.create_equipment 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.create_equipment 尚未实现")

    def update_equipment(self) -> None:
        """组织 EquipmentService.update_equipment 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.update_equipment 尚未实现")

    def get_equipment(self) -> None:
        """组织 EquipmentService.get_equipment 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.get_equipment 尚未实现")

    def list_equipment(self) -> None:
        """组织 EquipmentService.list_equipment 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.list_equipment 尚未实现")

    def report_fault(self) -> None:
        """组织 EquipmentService.report_fault 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.report_fault 尚未实现")

    def finish_maintenance(self) -> None:
        """组织 EquipmentService.finish_maintenance 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.finish_maintenance 尚未实现")

    def list_maintenance(self) -> None:
        """组织 EquipmentService.list_maintenance 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.list_maintenance 尚未实现")

    def retire_equipment(self) -> None:
        """组织 EquipmentService.retire_equipment 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("EquipmentHandler.retire_equipment 尚未实现")
