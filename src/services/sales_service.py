"""销售服务。"""

from __future__ import annotations

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

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def get_sale_order(
        self, session: Session, actor: Actor, sale_order_id: int
    ) -> SaleOrderDetailView:
        """输入订单编号，返回含唯一付款、项目、权益和赠送的 SaleOrderDetailView。会员仅查本人，前台与管理员可查全部；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("SalesService.get_sale_order 尚未实现")

    def list_sale_orders(
        self, session: Session, actor: Actor, query: SaleOrderQuery
    ) -> Page[SaleOrderView]:
        """输入会员、销售种类、操作者、时间与分页条件，返回按 sold_at DESC, id DESC 的 Page[SaleOrderView]。会员仅查本人，前台与管理员可查全部；条件非法抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("SalesService.list_sale_orders 尚未实现")

    def sell_gym_card(
        self, session: Session,
        actor: Actor,
        data: GymCardSaleInput,
        request_id: str,
    ) -> GymCardSaleResultView:
        """前台或管理员输入会员、产品、付款方式与 UUID 请求编号，返回 GymCardSaleResultView。锁内复制价格及卡条款，接续期限卡从已有最大截止日开始；订单、项目、付款、卡和请求记录共用事务。相同请求复用原结果；输入、权限、状态或唯一冲突抛项目异常，提交未知由 Logic 携原请求编号报告。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("SalesService.sell_gym_card 尚未实现")

    def sell_lesson_package(
        self, session: Session,
        actor: Actor,
        data: LessonPackageSaleInput,
        request_id: str,
    ) -> LessonPackageSaleResultView:
        """前台或管理员输入会员、课包产品、付款方式与 UUID 请求编号，返回 LessonPackageSaleResultView。锁定产品与赠卡规则，订单、付款、课包、赠送和卡共用事务；赠卡按规则保存快照与接续日期。相同请求复用原结果；输入、权限、状态或请求冲突抛项目异常，提交未知沿原请求核实。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("SalesService.sell_lesson_package 尚未实现")

    def get_gym_card_sale_by_request(
        self, session: Session, actor: Actor, request_id: str
    ) -> GymCardSaleResultView:
        """原操作者输入售卡请求编号，返回当前 GymCardSaleResultView。不存在或不可见抛 NotFoundError，操作类型不符抛 ConflictError；查询保持付款与权益。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("SalesService.get_gym_card_sale_by_request 尚未实现")

    def get_lesson_package_sale_by_request(
        self, session: Session, actor: Actor, request_id: str
    ) -> LessonPackageSaleResultView:
        """原操作者输入售课包请求编号，返回当前 LessonPackageSaleResultView。不存在或不可见抛 NotFoundError，操作类型不符抛 ConflictError；查询保持付款与权益。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("SalesService.get_lesson_package_sale_by_request 尚未实现")
