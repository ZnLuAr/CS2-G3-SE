"""私教课包产品服务。"""

from __future__ import annotations

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

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_lesson_package_product(
        self, session: Session, actor: Actor, terms: LessonPackageProductTerms
    ) -> LessonPackageProductView:
        """管理员输入名称、金额、正课节数与可空有效天数，创建后返回 LessonPackageProductView。非法条款抛 InvalidInputError，越权抛 PermissionDenied；写入由 Logic 统一提交。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.create_lesson_package_product 尚未实现")

    def update_lesson_package_product(
        self, session: Session,
        actor: Actor,
        product_id: int,
        terms: LessonPackageProductTerms,
    ) -> LessonPackageProductView:
        """管理员输入产品编号与完整条款，锁内更新后返回 LessonPackageProductView。条款用于后续销售，已售课包保留快照；非法条款或不存在抛项目异常。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.update_lesson_package_product 尚未实现")

    def get_lesson_package_product(
        self, session: Session, actor: Actor, product_id: int
    ) -> LessonPackageProductView:
        """输入产品编号，返回 LessonPackageProductView。前台限可销售产品，管理员可查全部；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.get_lesson_package_product 尚未实现")

    def list_lesson_package_products(
        self, session: Session, actor: Actor, query: NamedQuery
    ) -> Page[LessonPackageProductView]:
        """输入名称、启用与分页条件，按 name ASC, id ASC 返回 Page[LessonPackageProductView]。前台限可销售产品，管理员可查全部；非法条件抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.list_lesson_package_products 尚未实现")

    def set_lesson_package_product_sale_enabled(
        self, session: Session, actor: Actor, product_id: int, enabled: bool
    ) -> LessonPackageProductView:
        """管理员输入产品编号与布尔销售状态，锁内更新后返回 LessonPackageProductView。已售课包保留原条款；非法输入或不存在抛项目异常。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.set_lesson_package_product_sale_enabled 尚未实现")

    def get_gift_rule(
        self, session: Session, actor: Actor, rule_id: int
    ) -> LessonPackageGiftRuleView:
        """管理员输入规则编号，返回固定版本的 LessonPackageGiftRuleView。不存在抛 NotFoundError，越权抛 PermissionDenied，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.get_gift_rule 尚未实现")

    def list_gift_rules(
        self, session: Session, actor: Actor, query: LessonPackageGiftRuleQuery
    ) -> Page[LessonPackageGiftRuleView]:
        """管理员输入触发产品、奖励产品、启用与分页条件，按触发产品、版本倒序和编号倒序返回 Page[LessonPackageGiftRuleView]。非法条件抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.list_gift_rules 尚未实现")

    def create_gift_rule(
        self, session: Session, actor: Actor, data: LessonPackageGiftRuleInput
    ) -> LessonPackageGiftRuleView:
        """管理员输入触发课包、奖励期限卡、数量与激活策略，创建版本 1 并返回 LessonPackageGiftRuleView。锁序为课包产品、规则、奖励卡产品；产品资格不符抛 InvalidState，重复启用版本抛 ConflictError。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.create_gift_rule 尚未实现")

    def replace_gift_rule(
        self, session: Session,
        actor: Actor,
        rule_id: int,
        data: GiftRuleRevisionInput,
    ) -> LessonPackageGiftRuleView:
        """管理员输入旧规则编号与完整奖励条款，沿同一触发产品创建下一版本并停用原版本，返回新 LessonPackageGiftRuleView。两个变更共用当前事务；版本冲突、目标不存在或奖励资格不符抛项目异常。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.replace_gift_rule 尚未实现")

    def set_gift_rule_active(
        self, session: Session, actor: Actor, rule_id: int, active: bool
    ) -> LessonPackageGiftRuleView:
        """管理员输入规则编号与布尔状态，锁触发产品、全部规则和奖励卡产品，返回最新 LessonPackageGiftRuleView。同触发产品已有其他启用版本抛 ConflictError，启用资格不符抛 InvalidState。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("LessonPackageProductService.set_gift_rule_active 尚未实现")
