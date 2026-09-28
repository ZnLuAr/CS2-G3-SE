"""销售订单数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.models.contracts import (
    SaleKind,
    SaleOrderQuery,
)
from src.models.sale_order import SaleOrder, SaleOrderAggregate

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SaleOrderRepository:
    """销售订单数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("SaleOrderRepository.__init__ 尚未实现")

    def create(
        self,
        member_id: int,
        kind: SaleKind,
        total_amount: Decimal,
        sold_at: datetime,
        operator_id: int,
    ) -> SaleOrder:
        """创建销售订单；不自行提交。

        返回：SaleOrder；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SaleOrderRepository.create 尚未实现")

    def get(self, order_id: int) -> SaleOrder | None:
        """查询销售订单详情；未找到返回 None，由服务转成异常。

        返回：SaleOrder | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SaleOrderRepository.get 尚未实现")

    def get_detail(
        self, order_id: int
    ) -> SaleOrderAggregate | None:
        """查询销售订单详情及关联数据；使用固定 JOIN 装载。

        返回：SaleOrderAggregate | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SaleOrderRepository.get_detail 尚未实现")

    def list(
        self, query: SaleOrderQuery
    ) -> tuple[list[SaleOrder], int]:
        """按条件查询并返回订单列表和总数。

        返回：tuple[list[SaleOrder], int]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SaleOrderRepository.list 尚未实现")
