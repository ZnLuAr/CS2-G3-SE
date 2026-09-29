"""私教课包产品服务。"""

from __future__ import annotations

from collections.abc import Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.services.auth_service import AuthService
    from src.models.contracts import (
        Actor,
        GiftRuleRevisionInput,
        LessonPackageGiftRuleInput,
        LessonPackageGiftRuleQuery,
        LessonPackageGiftRuleView,
        LessonPackageProductTerms,
        LessonPackageProductView,
        NamedQuery,
        Page,
    )


class LessonPackageProductService:
    """私教课包产品管理服务。"""

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂与共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_lesson_package_product(
        self, actor: Actor, terms: LessonPackageProductTerms
    ) -> LessonPackageProductView:
        """创建私教课包产品。"""
        raise NotImplementedError("LessonPackageProductService.create_lesson_package_product 尚未实现")

    def update_lesson_package_product(
        self,
        actor: Actor,
        product_id: int,
        terms: LessonPackageProductTerms,
    ) -> LessonPackageProductView:
        """更新私教课包产品。"""
        raise NotImplementedError("LessonPackageProductService.update_lesson_package_product 尚未实现")

    def get_lesson_package_product(
        self, actor: Actor, product_id: int
    ) -> LessonPackageProductView:
        """获取私教课包产品详情。"""
        raise NotImplementedError("LessonPackageProductService.get_lesson_package_product 尚未实现")

    def list_lesson_package_products(
        self, actor: Actor, query: NamedQuery
    ) -> Page[LessonPackageProductView]:
        """列出私教课包产品。"""
        raise NotImplementedError("LessonPackageProductService.list_lesson_package_products 尚未实现")

    def set_lesson_package_product_sale_enabled(
        self, actor: Actor, product_id: int, enabled: bool
    ) -> LessonPackageProductView:
        """设置私教课包产品是否可销售。"""
        raise NotImplementedError("LessonPackageProductService.set_lesson_package_product_sale_enabled 尚未实现")

    def get_gift_rule(
        self, actor: Actor, rule_id: int
    ) -> LessonPackageGiftRuleView:
        """获取赠卡规则详情。"""
        raise NotImplementedError("LessonPackageProductService.get_gift_rule 尚未实现")

    def list_gift_rules(
        self, actor: Actor, query: LessonPackageGiftRuleQuery
    ) -> Page[LessonPackageGiftRuleView]:
        """列出赠卡规则。"""
        raise NotImplementedError("LessonPackageProductService.list_gift_rules 尚未实现")

    def create_gift_rule(
        self, actor: Actor, data: LessonPackageGiftRuleInput
    ) -> LessonPackageGiftRuleView:
        """创建赠卡规则。"""
        raise NotImplementedError("LessonPackageProductService.create_gift_rule 尚未实现")

    def replace_gift_rule(
        self,
        actor: Actor,
        rule_id: int,
        data: GiftRuleRevisionInput,
    ) -> LessonPackageGiftRuleView:
        """替换赠卡规则（创建新版本）。"""
        raise NotImplementedError("LessonPackageProductService.replace_gift_rule 尚未实现")

    def set_gift_rule_active(
        self, actor: Actor, rule_id: int, active: bool
    ) -> LessonPackageGiftRuleView:
        """设置赠卡规则是否启用。"""
        raise NotImplementedError("LessonPackageProductService.set_gift_rule_active 尚未实现")
