"""销售项目数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from src.models.contracts import (
    GymCardSaleItemProductSnapshot,
    LessonPackageSaleItemProductSnapshot,
)
from src.models.sale_item import SaleItem

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SaleItemRepository:
    """销售项目数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("SaleItemRepository.__init__ 尚未实现")

    def create_gym_card_item(
        self,
        sale_order_id: int,
        member_id: int,
        product_id: int,
        product_snapshot: GymCardSaleItemProductSnapshot,
        price: Decimal,
    ) -> SaleItem:
        """创建健身房卡销售项目；不自行提交。

        返回：SaleItem；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SaleItemRepository.create_gym_card_item 尚未实现")

    def create_lesson_package_item(
        self,
        sale_order_id: int,
        member_id: int,
        product_id: int,
        product_snapshot: LessonPackageSaleItemProductSnapshot,
        price: Decimal,
    ) -> SaleItem:
        """创建私教课包销售项目；不自行提交。

        返回：SaleItem；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SaleItemRepository.create_lesson_package_item 尚未实现")

    def list_for_order(self, order_id: int) -> list[SaleItem]:
        """查询指定订单的所有销售项目。

        返回：list[SaleItem]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SaleItemRepository.list_for_order 尚未实现")
