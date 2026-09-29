"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import DateWindow, PaymentMethod, PaymentQuery, PaymentTotals
from src.models.payment import Payment

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session


class PaymentRepository:
    """收款数据访问；只使用传入会话，不提交、不输出提示。

    返回领域模型 Payment（非 View）；查询未命中返回 None，由服务转换异常。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("PaymentRepository.__init__ 尚未实现")

    def create(
        self,
        sale_order_id: int,
        member_id: int,
        amount: Decimal,
        method: PaymentMethod,
        paid_at: datetime,
        operator_id: int,
    ) -> Payment:
        """保存模拟实收并取得编号，与销售共用事务。"""
        raise NotImplementedError("PaymentRepository.create 尚未实现")

    def get_by_order(self, sale_order_id: int) -> Payment | None:
        """按销售订单读取唯一收款。"""
        raise NotImplementedError("PaymentRepository.get_by_order 尚未实现")

    def list(self, query: PaymentQuery) -> tuple[list[Payment], int]:
        """按时间、会员和方式筛选，再按 paid_at、id 降序稳定分页，返回（当页记录, 总数）。"""
        raise NotImplementedError("PaymentRepository.list 尚未实现")

    def aggregate(self, window: DateWindow, method: PaymentMethod | None) -> PaymentTotals:
        """按窗口和收款方式汇总收入总额。"""
        raise NotImplementedError("PaymentRepository.aggregate 尚未实现")
