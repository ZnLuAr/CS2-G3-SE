"""权益查询服务。"""

from __future__ import annotations

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

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def get_gym_card(
        self, session: Session, actor: Actor, gym_card_id: int
    ) -> GymCardView:
        """输入健身房卡编号，返回带 kind、来源和条款快照的 GymCardView。会员仅查本人，前台与管理员可查全部；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("EntitlementQueryService.get_gym_card 尚未实现")

    def list_gym_cards(
        self, session: Session, actor: Actor, query: GymCardQuery
    ) -> Page[GymCardView]:
        """输入会员、种类、状态、来源、日期和分页筛选，返回 Page[GymCardView]。会员范围在 SQL 计数与分页前应用；前台和管理员可查全部，条件非法抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("EntitlementQueryService.list_gym_cards 尚未实现")

    def get_lesson_package(
        self, session: Session, actor: Actor, lesson_package_id: int
    ) -> LessonPackageView:
        """输入课包编号，返回含销售来源与余额的 LessonPackageView。会员仅查本人，前台与管理员可查全部；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("EntitlementQueryService.get_lesson_package 尚未实现")

    def list_lesson_packages(
        self, session: Session, actor: Actor, query: LessonPackageQuery
    ) -> Page[LessonPackageView]:
        """输入会员、状态、日期、余额和分页条件，返回 Page[LessonPackageView]。会员仅查本人，前台与管理员可查全部；条件非法抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("EntitlementQueryService.list_lesson_packages 尚未实现")

    def get_gym_membership(
        self, session: Session,
        actor: Actor,
        member_id: int,
        business_date: date | None = None,
    ) -> GymMembershipView:
        """输入会员编号与可空业务日期，返回 GymMembershipView。日期为空时由服务取门店当天；有效期限卡与有余额次卡的资格按会员去重。会员仅查本人，前台与管理员可查；不可见抛 NotFoundError，查询保持余额。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("EntitlementQueryService.get_gym_membership 尚未实现")

    def void_gym_card(
        self, session: Session, actor: Actor, gym_card_id: int
    ) -> GymCardView:
        """管理员输入卡编号，锁定卡并永久设置 void，返回最新 GymCardView。重复作废返回当前结果，历史订单与入场保留；不存在抛 NotFoundError，越权抛 PermissionDenied，写入由 Logic 统一提交。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("EntitlementQueryService.void_gym_card 尚未实现")

    def void_lesson_package(
        self, session: Session, actor: Actor, lesson_package_id: int
    ) -> LessonPackageView:
        """管理员输入课包编号，按会员、课包、预约取锁，返回最新 LessonPackageView。要求占用为零且没有 reserved/checked_in 预约，否则抛 InvalidState；重复作废返回当前结果，历史保持可查，写入由 Logic 统一提交。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("EntitlementQueryService.void_lesson_package 尚未实现")
