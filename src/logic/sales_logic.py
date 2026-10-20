"""SalesLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
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
    from src.services.sales_service import SalesService


class SalesLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        sales_service: SalesService,
    ) -> None:
        self._session_factory = session_factory
        self._sales_service = sales_service

    def get_sale_order(self, actor: Actor, sale_order_id: int) -> SaleOrderDetailView:
        raise NotImplementedError

    def list_sale_orders(self, actor: Actor, query: SaleOrderQuery) -> Page[SaleOrderView]:
        raise NotImplementedError

    def sell_gym_card(self, actor: Actor, data: GymCardSaleInput, request_id: str) -> GymCardSaleResultView:
        raise NotImplementedError

    def sell_lesson_package(self, actor: Actor, data: LessonPackageSaleInput, request_id: str) -> LessonPackageSaleResultView:
        raise NotImplementedError

    def get_gym_card_sale_by_request(self, actor: Actor, request_id: str) -> GymCardSaleResultView:
        raise NotImplementedError

    def get_lesson_package_sale_by_request(self, actor: Actor, request_id: str) -> LessonPackageSaleResultView:
        raise NotImplementedError
