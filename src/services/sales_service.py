"""销售服务。"""

from __future__ import annotations

from collections.abc import Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.services.auth_service import AuthService
    from src.models.contracts import (
        Actor,
        GymCardSaleInput,
        GymCardSaleResultView,
        LessonPackageSaleInput,
        LessonPackageSaleResultView,
        Page,
        SaleOrderDetailView,
        SaleOrderQuery,
        SaleOrderView,
    )


class SalesService:
    """销售服务。"""

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂与共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def get_sale_order(
        self, actor: Actor, sale_order_id: int
    ) -> SaleOrderDetailView:
        """获取销售订单详情。"""
        raise NotImplementedError("SalesService.get_sale_order 尚未实现")

    def list_sale_orders(
        self, actor: Actor, query: SaleOrderQuery
    ) -> Page[SaleOrderView]:
        """列出销售订单。"""
        raise NotImplementedError("SalesService.list_sale_orders 尚未实现")

    def sell_gym_card(
        self,
        actor: Actor,
        data: GymCardSaleInput,
        request_id: str,
    ) -> GymCardSaleResultView:
        """销售健身房卡。"""
        raise NotImplementedError("SalesService.sell_gym_card 尚未实现")

    def sell_lesson_package(
        self,
        actor: Actor,
        data: LessonPackageSaleInput,
        request_id: str,
    ) -> LessonPackageSaleResultView:
        """销售私教课包。"""
        raise NotImplementedError("SalesService.sell_lesson_package 尚未实现")

    def get_gym_card_sale_by_request(
        self, actor: Actor, request_id: str
    ) -> GymCardSaleResultView:
        """按请求ID获取健身房卡销售结果。"""
        raise NotImplementedError("SalesService.get_gym_card_sale_by_request 尚未实现")

    def get_lesson_package_sale_by_request(
        self, actor: Actor, request_id: str
    ) -> LessonPackageSaleResultView:
        """按请求ID获取私教课包销售结果。"""
        raise NotImplementedError("SalesService.get_lesson_package_sale_by_request 尚未实现")
