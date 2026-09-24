"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import MeasurementInput, MeasurementQuery, MeasurementView, Page

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MeasurementRepository:
    """体测数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("MeasurementRepository.__init__ 尚未实现")

    def get(
        self, measurement_id: int, *, scope_member_id: int | None,
        scope_coach_id: int | None, as_of: datetime,
    ) -> MeasurementView | None:
        """读取范围内的体测详情；不存在或不可见返回 None。

        范围与 as_of 由服务根据可信身份生成，两种 scope 必须恰有一项非空。
        会员范围按归属；教练范围按历史预约计算截止并限制 created_at，见架构“体测权限规则”。

        返回：MeasurementView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MeasurementRepository.get 尚未实现")

    def list(
        self, query: MeasurementQuery, *, scope_member_id: int | None,
        scope_coach_id: int | None, as_of: datetime,
    ) -> Page[MeasurementView]:
        """按测量时间和编号降序分页查询，只计算授权范围内的 total 和 items。

        身份范围与可见截止同 get；query.member_id 只能缩小范围，不能覆盖服务给定的 scope。

        返回：Page[MeasurementView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MeasurementRepository.list 尚未实现")

    def create(
        self, data: MeasurementInput, coach_id: int, *, created_at: datetime,
    ) -> MeasurementView:
        """保存体测；教练编号来自可信操作者，created_at 由服务获得会员锁后生成。

        created_at 是实际录入时间，不接受界面传值；不可用 measured_at 代替。

        返回：MeasurementView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MeasurementRepository.create 尚未实现")
