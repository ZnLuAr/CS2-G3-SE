"""体测服务接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import (
    Actor,
    MeasurementComparison,
    MeasurementInput,
    MeasurementQuery,
    MeasurementView,
    Page,
)
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MeasurementService:
    """体测服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    会员只查本人；教练历史查看权永久保留，最后有效预约结束后停止更新，再预约恢复。
    前台和管理员不能查看个人体测明细，也不能调用详情、列表或对比接口绕过限制。
    截止时间由本教练的预约记录计算，按体测 created_at 过滤，不按可补录的 measured_at。
    详情、历史总数及内容、对比两条记录共用同一范围和 as_of；不能只在界面隐藏。
    当前所有方法仅占位，调用会抛 NotImplementedError。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        raise NotImplementedError("MeasurementService.__init__ 尚未实现")

    def record(self, actor: Actor, data: MeasurementInput) -> MeasurementView:
        """录入会员体测。

        身高为 100.00–250.00 cm，体重为 30.00–150.00 kg，含边界；体脂可空或 0.00–100.00%。
        超出范围抛 InvalidInputError，不写入记录。
        教练须有该会员的当前有效预约；历史只读权限不能用于新增，越权抛 PermissionDenied。
        获得会员行锁后生成可信 created_at，体测原记录不可编辑或删除。

        返回：MeasurementView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MeasurementService.record 尚未实现")

    def get_measurement(self, actor: Actor, measurement_id: int) -> MeasurementView:
        """查看体测详情。

        会员只能查看本人；教练只能查看授权范围；前台和管理员无权查看明细。
        数据访问必须带服务生成的身份范围和查询时刻；范围外或不存在均抛 NotFoundError。
        返回：MeasurementView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MeasurementService.get_measurement 尚未实现")

    def list_measurements(self, actor: Actor, query: MeasurementQuery) -> Page[MeasurementView]:
        """分页查看体测历史。

        会员只能查询本人；前台和管理员无权查询个人体测历史。
        教练只得到可见截止内的记录，total 也按该范围统计；没有历史授权时为正常空 Page。
        返回：Page[MeasurementView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MeasurementService.list_measurements 尚未实现")

    def compare(self, actor: Actor, before_id: int, after_id: int) -> MeasurementComparison:
        """对比同会员先后两次体测。

        会员只能对比本人记录；教练只能对比授权范围；前台和管理员无权对比明细。
        两条记录使用同一 as_of 和身份范围；任一条不可见抛 NotFoundError，不泄露差值。
        返回：MeasurementComparison。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MeasurementService.compare 尚未实现")
