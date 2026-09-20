"""收款查询与报表服务接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import (
    Actor,
    CoachStatsView,
    CsvExport,
    DateWindow,
    MembershipStats,
    Page,
    PageRequest,
    PaymentQuery,
    PaymentView,
    RevenueView,
    SessionQuery,
    SessionStatsView,
)
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ReportService:
    """收款查询与报表服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    当前所有方法仅占位，调用会抛 NotImplementedError。
    """

    def __init__(
        self, session_factory: Callable[[], Session], auth: AuthService,
        *, timezone_name: str,
    ) -> None:
        """接收会话工厂、共用身份校验服务和门店时区；时区由 App 配置传入。"""
        raise NotImplementedError("ReportService.__init__ 尚未实现")

    def get_payment(self, actor: Actor, payment_id: int) -> PaymentView:
        """查询收款详情。

        返回：PaymentView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.get_payment 尚未实现")

    def list_payments(self, actor: Actor, query: PaymentQuery) -> Page[PaymentView]:
        """分页查询收款流水。

        返回：Page[PaymentView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.list_payments 尚未实现")

    def revenue(self, actor: Actor, window: DateWindow) -> RevenueView:
        """按时间汇总实收。

        返回：RevenueView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.revenue 尚未实现")

    def membership_stats(self, actor: Actor) -> MembershipStats:
        """统计当前快照的会员与持卡，服务生成 as_of；不接受历史查询时间。

        返回：MembershipStats。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.membership_stats 尚未实现")

    def session_stats(self, actor: Actor, query: SessionQuery) -> Page[SessionStatsView]:
        """分页汇总课次预约及到课。

        返回：Page[SessionStatsView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.session_stats 尚未实现")

    def coach_stats(
        self,
        actor: Actor,
        window: DateWindow,
        paging: PageRequest,
    ) -> Page[CoachStatsView]:
        """分页汇总教练授课。

        返回：Page[CoachStatsView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.coach_stats 尚未实现")

    def export_payments(self, actor: Actor, query: PaymentQuery) -> CsvExport:
        """导出授权范围内的收款流水。

        返回：CsvExport。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.export_payments 尚未实现")

    def export_revenue(self, actor: Actor, window: DateWindow) -> CsvExport:
        """导出实收汇总。

        返回：CsvExport。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.export_revenue 尚未实现")

    def export_memberships(self, actor: Actor) -> CsvExport:
        """导出会员与持卡统计。

        返回：CsvExport。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.export_memberships 尚未实现")

    def export_sessions(self, actor: Actor, query: SessionQuery) -> CsvExport:
        """导出课程预约与到课统计。

        返回：CsvExport。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.export_sessions 尚未实现")

    def export_coaches(self, actor: Actor, window: DateWindow) -> CsvExport:
        """导出教练授课统计。

        返回：CsvExport。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReportService.export_coaches 尚未实现")
