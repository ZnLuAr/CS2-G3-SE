"""EntitlementLogic use-case entry points."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        GymCardQuery,
        GymCardView,
        GymMembershipView,
        LessonPackageQuery,
        LessonPackageView,
        Page,
    )
    from src.services.entitlement_query_service import EntitlementQueryService


class EntitlementLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        entitlement_query_service: EntitlementQueryService,
    ) -> None:
        self._session_factory = session_factory
        self._entitlement_query_service = entitlement_query_service

    def get_gym_card(self, actor: Actor, gym_card_id: int) -> GymCardView:
        raise NotImplementedError

    def list_gym_cards(self, actor: Actor, query: GymCardQuery) -> Page[GymCardView]:
        raise NotImplementedError

    def get_lesson_package(self, actor: Actor, lesson_package_id: int) -> LessonPackageView:
        raise NotImplementedError

    def list_lesson_packages(self, actor: Actor, query: LessonPackageQuery) -> Page[LessonPackageView]:
        raise NotImplementedError

    def get_gym_membership(self, actor: Actor, member_id: int, business_date: date | None = None) -> GymMembershipView:
        raise NotImplementedError

    def void_gym_card(self, actor: Actor, gym_card_id: int) -> GymCardView:
        raise NotImplementedError

    def void_lesson_package(self, actor: Actor, lesson_package_id: int) -> LessonPackageView:
        raise NotImplementedError
