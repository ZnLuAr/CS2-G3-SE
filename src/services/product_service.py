"""产品服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import (
    Actor,
    CardProductView,
    CardQuery,
    CardTerms,
    CardView,
    EntryInput,
    EntryView,
    NamedQuery,
    Page,
    SaleInput,
    SaleView,
)
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ProductService:
    """产品服务（私教课产品和入场次卡）。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；异常和事务约定见 docs/architecture.md 的会员与产品模块。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(
        self, session_factory: Callable[[], Session], auth: AuthService,
        *, timezone_name: str,
    ) -> None:
        """接收会话工厂、共用身份校验服务和门店时区；时区由 App 配置传入。"""
        self._session_factory = session_factory
        self._auth = auth
        self._timezone_name = timezone_name

    def create_product(self, actor: Actor, terms: CardTerms) -> CardProductView:
        """创建私教课产品或入场次卡。

        购买 20/64/256 节私教课，附赠 30/90/365 天门禁；不符合抛 InvalidInputError。
        次卡为 10 次入场、无期限、课节为 0；可空字段与固定值见架构文档的产品规则。
        返回：CardProductView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守架构文档的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ProductService.create_product 尚未实现")

    def update_product(self, actor: Actor, product_id: int, terms: CardTerms) -> CardProductView:
        """修改后续销售规则。

        同样校验月/季/年固定天数及课节数，不改变已售卡的快照和余额。
        返回：CardProductView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守架构文档的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ProductService.update_product 尚未实现")

    def get_product(self, actor: Actor, product_id: int) -> CardProductView:
        """查询产品详情。

        返回：CardProductView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守架构文档的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ProductService.get_product 尚未实现")

    def list_products(self, actor: Actor, query: NamedQuery) -> Page[CardProductView]:
        """分页查询产品。

        返回：Page[CardProductView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守架构文档的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ProductService.list_products 尚未实现")

    def set_product_active(self, actor: Actor, product_id: int, active: bool) -> CardProductView:
        """停售或恢复产品。

        返回：CardProductView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守架构文档的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ProductService.set_product_active 尚未实现")

    def get_card(self, actor: Actor, membership_id: int) -> CardView:
        """查询会员卡权益。

        到期卡的余额仍供历史核对，不能显示为可预约课节或转移给新卡。
        返回：CardView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守架构文档的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ProductService.get_card 尚未实现")

    def list_cards(self, actor: Actor, query: CardQuery) -> Page[CardView]:
        """分页查询会员卡及提醒。

        返回：Page[CardView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守架构文档的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ProductService.list_cards 尚未实现")

    def sell_product(self, actor: Actor, data: SaleInput, request_id: str) -> SaleView:
        """购买产品或续购：权益、收款、防重记录在同一事务内保存。
        输入不含生效日；会员锁内计算期限卡从所有未作废期限卡末尾接续，最早为今天。
        依次锁定会员、卡产品并锁定当前读既有已售会员卡后，生成一次当前时刻；
        生效门店日期及收款时间均由该时刻取得。
        次卡购买当天生效，不参与期限卡接续；相同请求不重新计算并再次销售。
        课节按产品购买数量初始化，预约占用为 0；不接收旧卡剩余课节。
        成功返回 SaleView；输入、权限、状态或请求冲突按公共失败规则抛出。
        提交结果未知时抛 OutcomeUnknownError，不能告知用户“肯定没收款”。"""
        raise NotImplementedError("ProductService.sell_product 尚未实现")

    def get_sale_by_request(self, actor: Actor, request_id: str) -> SaleView:
        """按原请求编号核实销售结果；核对操作者且 operation 必须为 sell_product。

        无记录或不可见抛 NotFoundError；操作类型或输入不一致抛 ConflictError。"""
        raise NotImplementedError("ProductService.get_sale_by_request 尚未实现")

    def get_today_entry(self, actor: Actor, member_id: int) -> EntryView:
        """查询本门店今天已登记的入场结果，不扣次。

        会员仅本人，前台/管理员可代查；无记录抛 NotFoundError，可改查有效卡列表。
        重验账号及会员状态；日期由服务生成。成功固定返回 EntryView，当前仅占位。"""
        raise NotImplementedError("ProductService.get_today_entry 尚未实现")

    def register_entry(self, actor: Actor, data: EntryInput, request_id: str) -> EntryView:
        """登记当日首次入场，会员同一天后续入场返回原 EntryView。

        会员仅本人，前台/管理员可代办；可信门店日期在会员锁内生成。
        首次处理锁定会员及所选会员卡，锁后时刻同时用于门店日期和 entered_at。
        原请求重试先按幂等记录返回；每次请求均检查操作者权限和卡归属。
        当日已有记录时将新 request_id 映射到该记录，不检查卡当日有效性或余额，也不再扣次。
        首次入场再校验卡状态和有效期；次卡扣 1 次，期限卡扣 0 次；三项写入共用事务。
        次日真实入场使用新编号；失败按公共异常规则回滚。
        卡不适用抛 CardNotEligible，余额不足抛 InsufficientCredits；当前仅占位。"""
        raise NotImplementedError("ProductService.register_entry 尚未实现")

    def get_entry_by_request(self, actor: Actor, request_id: str) -> EntryView:
        """按本人 register_entry 请求核实结果；返回原日期的 EntryView，不再次扣次。

        无记录或不可见抛 NotFoundError，操作类型不符抛 ConflictError；查不到不代表提交失败。
        不修改数据；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("ProductService.get_entry_by_request 尚未实现")
