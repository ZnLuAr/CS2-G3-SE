"""收款查询、经营报表及 CSV 保存交互。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from src.errors.business import ResourceError
from src.logic.report_logic import ReportLogic
from src.models.contracts import Actor, CsvExport, DateWindow, PaymentQuery, Role, SessionQuery
from src.ui.cli import formatters, prompts

T = TypeVar("T")


class ReportHandler:
    """查询交给 Logic；下载字节由用户指定新文件路径保存。"""

    def __init__(
        self,
        logic: ReportLogic,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收用例入口、当前身份回调及门店时区。"""
        self._logic = logic
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    @property
    def current_role(self) -> Role:
        """返回菜单展示角色；Logic 每次调用仍执行权限校验。"""
        return self._get_actor().role

    def _window(self) -> DateWindow:
        return DateWindow(
            start=prompts.prompt_datetime(
                "开始时刻（含，YYYY-MM-DD HH:MM）：",
                timezone_name=self._timezone_name,
            ),
            end=prompts.prompt_datetime(
                "结束时刻（不含，YYYY-MM-DD HH:MM）：",
                timezone_name=self._timezone_name,
            ),
        )

    @staticmethod
    def _optional_id(label: str) -> int | None:
        while True:
            raw = prompts.prompt_optional_text(label)
            if raw is None:
                return None
            if raw.isascii() and raw.isdecimal():
                try:
                    value = int(raw)
                except ValueError:
                    pass
                else:
                    if 1 <= value <= 2**63 - 1:
                        return value
            print("请输入正整数编号，或留空表示全部。")

    @staticmethod
    def _choice(label: str, values: tuple[T, ...]) -> T | None:
        index = prompts.prompt_int(label, minimum=0, maximum=len(values))
        return None if index == 0 else values[index - 1]

    def _payment_query(self) -> PaymentQuery:
        member_id = self._optional_id("会员编号（留空表示全部，q 取消）：")
        method = self._choice(
            "收款方式（0 全部 / 1 现金 / 2 刷卡 / 3 转账）：",
            ("cash", "card", "transfer"),
        )
        window = self._window() if prompts.prompt_confirm("限定收款时间范围？") else None
        return PaymentQuery(member_id=member_id, method=method, window=window)

    def _session_query(self) -> SessionQuery:
        coach_id = self._optional_id("教练编号（留空表示全部，q 取消）：")
        room_id = self._optional_id("场地编号（留空表示全部，q 取消）：")
        window = self._window() if prompts.prompt_confirm("限定课次开始时间范围？") else None
        status = self._choice(
            "课次状态（0 全部 / 1 已排课 / 2 已完成 / 3 已取消）：",
            ("scheduled", "completed", "cancelled"),
        )
        return SessionQuery(coach_id=coach_id, room_id=room_id, window=window, status=status)

    def get_payment(self) -> None:
        """前台或管理员输入收款编号后查看详情。"""
        actor = self._get_actor()
        payment_id = prompts.prompt_int("收款编号（q 取消）：", minimum=1)
        view = self._logic.get_payment(actor, payment_id)
        print(formatters.format_payment(view, timezone_name=self._timezone_name))

    def list_payments(self) -> None:
        """固定筛选条件，按页浏览收款结果。"""
        from src.ui.cli.menus import browse_pages

        actor = self._get_actor()
        query = self._payment_query()
        browse_pages(
            lambda paging: self._logic.list_payments(actor, replace(query, paging=paging)),
            lambda page: formatters.format_payments(page, timezone_name=self._timezone_name),
        )

    def revenue(self) -> None:
        """展示指定半开时间窗口内的实收统计。"""
        actor = self._get_actor()
        view = self._logic.revenue(actor, self._window())
        print(formatters.format_revenue(view, timezone_name=self._timezone_name))

    def membership_stats(self) -> None:
        """展示 Logic 在同一快照中取得的会员与权益统计。"""
        view = self._logic.membership_stats(self._get_actor())
        print(formatters.format_membership_stats(view, timezone_name=self._timezone_name))

    def session_stats(self) -> None:
        """按筛选和分页展示预约状态及课次出勤率。"""
        from src.ui.cli.menus import browse_pages

        actor = self._get_actor()
        query = self._session_query()
        browse_pages(
            lambda paging: self._logic.session_stats(actor, replace(query, paging=paging)),
            lambda page: formatters.format_session_stats_page(page, timezone_name=self._timezone_name),
        )

    def coach_stats(self) -> None:
        """按指定时间窗口分页查看教练业绩。"""
        from src.ui.cli.menus import browse_pages

        actor = self._get_actor()
        window = self._window()
        browse_pages(
            lambda paging: self._logic.coach_stats(actor, window, paging),
            lambda page: formatters.format_coach_stats_page(page, timezone_name=self._timezone_name),
        )

    def _save_export(self, export: CsvExport) -> None:
        """确认新文件路径后独占创建；输出失败映射为资源异常。"""
        print(f"建议文件名：{export.filename}")
        target = Path(prompts.prompt_text("CSV 保存路径（含文件名，q 取消）：")).expanduser()
        if not prompts.prompt_confirm("确认保存 CSV？"):
            return
        try:
            with target.open("xb") as output:
                output.write(export.content)
        except FileExistsError as exc:
            raise ResourceError("输出文件已存在，请选择新的文件名") from exc
        except (OSError, ValueError) as exc:
            raise ResourceError("CSV 保存失败，请检查输出目录和写入权限") from exc
        print(f"已导出 {export.row_count} 行至 {str(target)!r}。")

    def export_payments(self) -> None:
        """导出筛选后的全部收款；服务控制权限与行数上限。"""
        actor = self._get_actor()
        self._save_export(self._logic.export_payments(actor, self._payment_query()))

    def export_revenue(self) -> None:
        """导出指定时间窗口的实收统计。"""
        actor = self._get_actor()
        self._save_export(self._logic.export_revenue(actor, self._window()))

    def export_memberships(self) -> None:
        """以本次调用时刻申请导出当前快照的会员及权益指标。"""
        actor = self._get_actor()
        self._save_export(self._logic.export_memberships(actor, datetime.now(timezone.utc)))

    def export_sessions(self) -> None:
        """导出筛选后的全部课次统计。"""
        actor = self._get_actor()
        self._save_export(self._logic.export_sessions(actor, self._session_query()))

    def export_coaches(self) -> None:
        """导出指定时间窗口的全部教练统计。"""
        actor = self._get_actor()
        self._save_export(self._logic.export_coaches(actor, self._window()))
