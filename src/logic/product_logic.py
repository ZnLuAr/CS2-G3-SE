"""ProductLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        GiftRuleRevisionInput,
        GymCardProductTerms,
        GymCardProductView,
        LessonPackageGiftRuleInput,
        LessonPackageGiftRuleQuery,
        LessonPackageGiftRuleView,
        LessonPackageProductTerms,
        LessonPackageProductView,
        NamedQuery,
        Page,
    )
    from src.services.gym_card_product_service import GymCardProductService
    from src.services.lesson_package_product_service import LessonPackageProductService


class ProductLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        gym_card_product_service: GymCardProductService,
        lesson_package_product_service: LessonPackageProductService,
    ) -> None:
        self._session_factory = session_factory
        self._gym_card_product_service = gym_card_product_service
        self._lesson_package_product_service = lesson_package_product_service

    def create_gym_card_product(self, actor: Actor, terms: GymCardProductTerms) -> GymCardProductView:
        raise NotImplementedError

    def update_gym_card_product(self, actor: Actor, product_id: int, terms: GymCardProductTerms) -> GymCardProductView:
        raise NotImplementedError

    def get_gym_card_product(self, actor: Actor, product_id: int) -> GymCardProductView:
        raise NotImplementedError

    def list_gym_card_products(self, actor: Actor, query: NamedQuery) -> Page[GymCardProductView]:
        raise NotImplementedError

    def set_gym_card_product_sale_enabled(self, actor: Actor, product_id: int, enabled: bool) -> GymCardProductView:
        raise NotImplementedError

    def set_gym_card_product_gift_enabled(self, actor: Actor, product_id: int, enabled: bool) -> GymCardProductView:
        raise NotImplementedError

    def create_lesson_package_product(self, actor: Actor, terms: LessonPackageProductTerms) -> LessonPackageProductView:
        raise NotImplementedError

    def update_lesson_package_product(self, actor: Actor, product_id: int, terms: LessonPackageProductTerms) -> LessonPackageProductView:
        raise NotImplementedError

    def get_lesson_package_product(self, actor: Actor, product_id: int) -> LessonPackageProductView:
        raise NotImplementedError

    def list_lesson_package_products(self, actor: Actor, query: NamedQuery) -> Page[LessonPackageProductView]:
        raise NotImplementedError

    def set_lesson_package_product_sale_enabled(self, actor: Actor, product_id: int, enabled: bool) -> LessonPackageProductView:
        raise NotImplementedError

    def get_gift_rule(self, actor: Actor, rule_id: int) -> LessonPackageGiftRuleView:
        raise NotImplementedError

    def list_gift_rules(self, actor: Actor, query: LessonPackageGiftRuleQuery) -> Page[LessonPackageGiftRuleView]:
        raise NotImplementedError

    def create_gift_rule(self, actor: Actor, data: LessonPackageGiftRuleInput) -> LessonPackageGiftRuleView:
        raise NotImplementedError

    def replace_gift_rule(self, actor: Actor, rule_id: int, data: GiftRuleRevisionInput) -> LessonPackageGiftRuleView:
        raise NotImplementedError

    def set_gift_rule_active(self, actor: Actor, rule_id: int, active: bool) -> LessonPackageGiftRuleView:
        raise NotImplementedError
