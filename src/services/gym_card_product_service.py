"""健身房卡产品服务。"""

from __future__ import annotations

from collections.abc import Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.services.auth_service import AuthService
    from src.models.contracts import (
        Actor,
        GymCardProductTerms,
        GymCardProductView,
        NamedQuery,
        Page,
    )


class GymCardProductService:
    """健身房卡产品管理服务。"""

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂与共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_gym_card_product(
        self, actor: Actor, terms: GymCardProductTerms
    ) -> GymCardProductView:
        """创建健身房卡产品。"""
        raise NotImplementedError("GymCardProductService.create_gym_card_product 尚未实现")

    def update_gym_card_product(
        self,
        actor: Actor,
        product_id: int,
        terms: GymCardProductTerms,
    ) -> GymCardProductView:
        """更新健身房卡产品。"""
        raise NotImplementedError("GymCardProductService.update_gym_card_product 尚未实现")

    def get_gym_card_product(
        self, actor: Actor, product_id: int
    ) -> GymCardProductView:
        """获取健身房卡产品详情。"""
        raise NotImplementedError("GymCardProductService.get_gym_card_product 尚未实现")

    def list_gym_card_products(
        self, actor: Actor, query: NamedQuery
    ) -> Page[GymCardProductView]:
        """列出健身房卡产品。"""
        raise NotImplementedError("GymCardProductService.list_gym_card_products 尚未实现")

    def set_gym_card_product_sale_enabled(
        self, actor: Actor, product_id: int, enabled: bool
    ) -> GymCardProductView:
        """设置健身房卡产品是否可销售。"""
        raise NotImplementedError("GymCardProductService.set_gym_card_product_sale_enabled 尚未实现")

    def set_gym_card_product_gift_enabled(
        self, actor: Actor, product_id: int, enabled: bool
    ) -> GymCardProductView:
        """设置健身房卡产品是否可赠送。"""
        raise NotImplementedError("GymCardProductService.set_gym_card_product_gift_enabled 尚未实现")
