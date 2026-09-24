"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from src.models.contracts import (
    CardProductView, CardQuery, CardTerms, CardView, EntryView, NamedQuery, Page,
)
from src.models.membership import CardProduct, Membership

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CardProductRepository:
    """卡产品数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("CardProductRepository.__init__ 尚未实现")

    def get(self, product_id: int) -> CardProductView | None:
        """读取卡产品详情；不存在返回 None。

        返回：CardProductView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CardProductRepository.get 尚未实现")

    def list(self, query: NamedQuery) -> Page[CardProductView]:
        """按名称和启用状态筛选，再按 id 升序稳定分页查询卡产品。

        返回：Page[CardProductView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CardProductRepository.list 尚未实现")

    def create(self, terms: CardTerms) -> CardProductView:
        """新增卡产品，返回完整规则与编号。

        返回：CardProductView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CardProductRepository.create 尚未实现")

    def update(self, product_id: int, terms: CardTerms) -> CardProductView:
        """更新售卡规则，不改变已售卡快照。

        返回：CardProductView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CardProductRepository.update 尚未实现")

    def set_active(self, product_id: int, active: bool) -> CardProductView:
        """设置是否允许继续销售。

        返回：CardProductView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CardProductRepository.set_active 尚未实现")

    def lock(self, product_id: int) -> CardProduct | None:
        """锁定卡产品并读取当前规则，供办卡与调价协调。

        返回：CardProduct | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CardProductRepository.lock 尚未实现")


class MembershipRepository:
    """会员持卡数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("MembershipRepository.__init__ 尚未实现")

    def get(self, membership_id: int) -> CardView | None:
        """读取已售快照及权益余额。

        返回：CardView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MembershipRepository.get 尚未实现")

    def list(self, query: CardQuery, *, scope_member_id: int | None) -> Page[CardView]:
        """在服务给定的会员权限范围内按 id 升序稳定分页查询。

        返回：Page[CardView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MembershipRepository.list 尚未实现")

    def latest_term_end(self, member_id: int) -> date | None:
        """读取该会员未作废期限卡中最晚的 valid_until，包括未来生效的卡。

        次卡不参与；没有期限卡返回 None。调用方须先锁会员，此查询使用锁定当前读。
        返回 date | None，不修改数据；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("MembershipRepository.latest_term_end 尚未实现")

    def create(
        self,
        *,
        member_id: int,
        product_id: int,
        terms: CardTerms,
        valid_from: date,
        valid_until: date | None,
        remaining_accesses: int | None,
        remaining_private_lessons: int,
        reserved_private_lessons: int,
    ) -> CardView:
        """保存会员卡与快照；与收款共用事务。

        返回：CardView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MembershipRepository.create 尚未实现")

    def update_private_lessons(
        self,
        membership_id: int,
        *,
        remaining_private_lessons: int,
        reserved_private_lessons: int,
    ) -> CardView:
        """写私教课节余额与预约占用；没有可用课节时由服务拒绝预约。

        返回：CardView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MembershipRepository.update_private_lessons 尚未实现")

    def lock(self, membership_id: int) -> Membership | None:
        """锁定持卡并读取最新余额，避免并发超扣。

        返回：Membership | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MembershipRepository.lock 尚未实现")

    def update_accesses(self, membership_id: int, *, remaining_accesses: int) -> CardView:
        """写次卡剩余入场次数，与当日入场记录共用服务事务。

        服务先锁卡并检查非负余额；期限卡不能调用此方法。失败交由服务回滚。
        返回 CardView；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("MembershipRepository.update_accesses 尚未实现")


class EntryRepository:
    """每日入场记录；使用传入事务，不自行提交或处理界面权限。"""

    def __init__(self, session: Session) -> None:
        """接收本次入场业务共用的数据库会话；当前仅占位。"""
        raise NotImplementedError("EntryRepository.__init__ 尚未实现")

    def get(self, entry_id: int) -> EntryView | None:
        """按编号读取入场结果，供请求核实；不存在返回 None，不修改数据。"""
        raise NotImplementedError("EntryRepository.get 尚未实现")

    def find_for_day(
        self, member_id: int, business_date: date, *, for_update: bool = False,
    ) -> EntryView | None:
        """读取会员指定门店日期的唯一记录；不存在返回 None。

        写流程先锁会员并传 for_update=True，避免读到旧快照后重复扣次；查询不写数据。
        当前调用抛 NotImplementedError。"""
        raise NotImplementedError("EntryRepository.find_for_day 尚未实现")

    def create(
        self, *, member_id: int, membership_id: int, business_date: date,
        entered_at: datetime, accesses_used: int, operator_id: int,
    ) -> EntryView:
        """保存当日首次入场，与次卡扣次及请求结果一起提交。

        日期和时刻由服务生成；会员与日期受唯一约束，异常交给服务回滚。
        返回 EntryView；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("EntryRepository.create 尚未实现")
