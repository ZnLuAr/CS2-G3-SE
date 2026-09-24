"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.models.contracts import Page, PaymentMethod, PaymentQuery, PaymentView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class PaymentRepository:
    """收款数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("PaymentRepository.__init__ 尚未实现")

    def create(
        self,
        *,
        membership_id: int,
        member_id: int,
        amount: Decimal,
        method: PaymentMethod,
        paid_at: datetime,
        operator_id: int,
    ) -> PaymentView:
        """保存模拟实收并取得编号，与办卡共用事务。

        返回：PaymentView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("PaymentRepository.create 尚未实现")

    def get(self, payment_id: int) -> PaymentView | None:
        """读取收款明细。

        返回：PaymentView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("PaymentRepository.get 尚未实现")

    def get_by_membership(self, membership_id: int) -> PaymentView | None:
        """按会员卡读取唯一收款。

        返回：PaymentView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("PaymentRepository.get_by_membership 尚未实现")

    def list(self, query: PaymentQuery) -> Page[PaymentView]:
        """按时间、会员和方式筛选，再按 paid_at、id 降序稳定分页查询流水。

        返回：Page[PaymentView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("PaymentRepository.list 尚未实现")
