"""按业务划分的 CLI 交互接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.report_service import ReportService


class ReportHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: ReportService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        raise NotImplementedError("ReportHandler.__init__ 尚未实现")

    def get_payment(self) -> None:
        """组织 ReportService.get_payment 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.get_payment 尚未实现")

    def list_payments(self) -> None:
        """组织 ReportService.list_payments 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.list_payments 尚未实现")

    def revenue(self) -> None:
        """组织 ReportService.revenue 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.revenue 尚未实现")

    def membership_stats(self) -> None:
        """组织 ReportService.membership_stats 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.membership_stats 尚未实现")

    def session_stats(self) -> None:
        """组织 ReportService.session_stats 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.session_stats 尚未实现")

    def coach_stats(self) -> None:
        """组织 ReportService.coach_stats 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.coach_stats 尚未实现")

    def export_payments(self) -> None:
        """组织 ReportService.export_payments 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.export_payments 尚未实现")

    def export_revenue(self) -> None:
        """组织 ReportService.export_revenue 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.export_revenue 尚未实现")

    def export_memberships(self) -> None:
        """组织 ReportService.export_memberships 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.export_memberships 尚未实现")

    def export_sessions(self) -> None:
        """组织 ReportService.export_sessions 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.export_sessions 尚未实现")

    def export_coaches(self) -> None:
        """组织 ReportService.export_coaches 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReportHandler.export_coaches 尚未实现")
