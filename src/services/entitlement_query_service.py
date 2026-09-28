"""权益查询服务。"""

from __future__ import annotations

from collections.abc import Callable

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.services.auth_service import AuthService
    from src.models.contracts import (
        Actor,
        GymCardQuery,
        GymCardView,
        GymMembershipView,
        LessonPackageQuery,
        LessonPackageView,
        Page,
    )


class EntitlementQueryService:
    """权益查询服务。"""

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂与共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def get_gym_card(
        self, actor: Actor, gym_card_id: int
    ) -> GymCardView:
        """获取健身房卡详情。"""
        raise NotImplementedError("EntitlementQueryService.get_gym_card 尚未实现")

    def list_gym_cards(
        self, actor: Actor, query: GymCardQuery
    ) -> Page[GymCardView]:
        """列出健身房卡。"""
        raise NotImplementedError("EntitlementQueryService.list_gym_cards 尚未实现")

    def get_lesson_package(
        self, actor: Actor, lesson_package_id: int
    ) -> LessonPackageView:
        """获取私教课包详情。"""
        raise NotImplementedError("EntitlementQueryService.get_lesson_package 尚未实现")

    def list_lesson_packages(
        self, actor: Actor, query: LessonPackageQuery
    ) -> Page[LessonPackageView]:
        """列出私教课包。"""
        raise NotImplementedError("EntitlementQueryService.list_lesson_packages 尚未实现")

    def get_gym_membership(
        self,
        actor: Actor,
        member_id: int,
        business_date: date | None = None,
    ) -> GymMembershipView:
        """获取会员的健身房会员资格。"""
        raise NotImplementedError("EntitlementQueryService.get_gym_membership 尚未实现")

    def void_gym_card(
        self, actor: Actor, gym_card_id: int
    ) -> GymCardView:
        """作废健身房卡。"""
        raise NotImplementedError("EntitlementQueryService.void_gym_card 尚未实现")

    def void_lesson_package(
        self, actor: Actor, lesson_package_id: int
    ) -> LessonPackageView:
        """作废私教课包。"""
        raise NotImplementedError("EntitlementQueryService.void_lesson_package 尚未实现")
