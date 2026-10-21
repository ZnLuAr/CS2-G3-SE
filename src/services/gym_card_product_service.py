"""健身房卡产品服务。"""

from __future__ import annotations

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

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_gym_card_product(
        self, session: Session, actor: Actor, terms: GymCardProductTerms
    ) -> GymCardProductView:
        """管理员输入按 kind 判别的完整条款，在同一事务创建根记录与对应子类型，返回 GymCardProductView。名称、金额、天数或次数非法抛 InvalidInputError，越权抛 PermissionDenied。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("GymCardProductService.create_gym_card_product 尚未实现")

    def update_gym_card_product(
        self, session: Session,
        actor: Actor,
        product_id: int,
        terms: GymCardProductTerms,
    ) -> GymCardProductView:
        """管理员输入产品编号与完整同种类条款，锁内更新后返回 GymCardProductView。新条款用于后续销售或赠送；种类或字段非法抛 InvalidInputError，不存在抛 NotFoundError。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("GymCardProductService.update_gym_card_product 尚未实现")

    def get_gym_card_product(
        self, session: Session, actor: Actor, product_id: int
    ) -> GymCardProductView:
        """输入产品编号，返回 GymCardProductView。前台查询可销售产品，管理员查询全部；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("GymCardProductService.get_gym_card_product 尚未实现")

    def list_gym_card_products(
        self, session: Session, actor: Actor, query: NamedQuery
    ) -> Page[GymCardProductView]:
        """输入名称、启用与分页条件，按 name ASC, id ASC 返回 Page[GymCardProductView]。前台范围限可销售产品，管理员可查全部；条件非法抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("GymCardProductService.list_gym_card_products 尚未实现")

    def set_gym_card_product_sale_enabled(
        self, session: Session, actor: Actor, product_id: int, enabled: bool
    ) -> GymCardProductView:
        """管理员输入产品编号与布尔销售状态，锁内更新并返回 GymCardProductView。历史卡按发放快照处理；输入非法抛 InvalidInputError，不存在抛 NotFoundError。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("GymCardProductService.set_gym_card_product_sale_enabled 尚未实现")

    def set_gym_card_product_gift_enabled(
        self, session: Session, actor: Actor, product_id: int, enabled: bool
    ) -> GymCardProductView:
        """管理员输入期限卡产品编号与布尔赠送状态，返回 GymCardProductView。按课包产品、赠卡规则、卡产品顺序取锁；停用时仍被启用规则引用抛 InvalidState，参数非法或目标不存在抛项目异常。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("GymCardProductService.set_gym_card_product_gift_enabled 尚未实现")
