"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from src.models.contracts import (
    CoachStatsView,
    DateWindow,
    MembershipStats,
    Page,
    PageRequest,
    RevenueView,
    SessionQuery,
    SessionStatsView,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ReportRepository:
    """报表数据查询；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("ReportRepository.__init__ 尚未实现")

    def revenue(self, window: DateWindow) -> RevenueView:
        """汇总时间范围内的实收，空数据返回零值。

        返回：RevenueView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReportRepository.revenue 尚未实现")

    def membership_stats(
        self, as_of: datetime, *, business_date: date,
    ) -> MembershipStats:
        """统计当前快照；as_of 与门店 business_date 由服务传入，不回放历史。

        返回：MembershipStats；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReportRepository.membership_stats 尚未实现")

    def session_stats(self, query: SessionQuery) -> Page[SessionStatsView]:
        """按课次开始时间分页统计预约与到课。

        返回：Page[SessionStatsView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReportRepository.session_stats 尚未实现")

    def coach_stats(self, window: DateWindow, paging: PageRequest) -> Page[CoachStatsView]:
        """分页汇总各教练已完成课次与到课人次。

        返回：Page[CoachStatsView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReportRepository.coach_stats 尚未实现")
