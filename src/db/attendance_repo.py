"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import ConsumptionView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ConsumptionRepository:
    """消课记录数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("ConsumptionRepository.__init__ 尚未实现")

    def get_by_booking(self, booking_id: int) -> ConsumptionView | None:
        """按预约读取已有消课结果，供重复请求复用。

        返回：ConsumptionView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ConsumptionRepository.get_by_booking 尚未实现")

    def create(
        self,
        *,
        booking_id: int,
        membership_id: int,
        lessons_used: int,
        completed_at: datetime,
        operator_id: int,
    ) -> ConsumptionView:
        """保存唯一消课记录，与扣减私教节数共用事务。

        返回：ConsumptionView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ConsumptionRepository.create 尚未实现")
