"""签到与到场更正的命令行交互。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor, Role
from src.logic.attendance_logic import AttendanceLogic
from src.ui.cli import formatters, prompts


class AttendanceHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成。
    """

    def __init__(
        self,
        logic: AttendanceLogic,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        self._logic = logic
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    @property
    def current_role(self) -> Role:
        """返回当前登录角色，供签到菜单筛选入口。"""
        return self._get_actor().role

    def check_in(self) -> None:
        """确认预约编号后签到，并展示更新后的预约。"""
        booking_id = prompts.prompt_int("预约编号（q 取消）：", minimum=1)
        if prompts.prompt_confirm(f"确认对预约 {booking_id} 签到？"):
            result = self._logic.check_in(self._get_actor(), booking_id)
            print(formatters.format_booking(result, timezone_name=self._timezone_name))

    def correct_attendance(self) -> None:
        """选择到场或未到场，确认后更正并展示更新后的预约。"""
        booking_id = prompts.prompt_int("预约编号（q 取消）：", minimum=1)
        choice = prompts.prompt_int("1 到场 / 2 未到场（q 取消）：", minimum=1, maximum=2)
        label = "到场" if choice == 1 else "未到场"
        if prompts.prompt_confirm(f"确认将预约 {booking_id} 更正为{label}？"):
            result = self._logic.correct_attendance(self._get_actor(), booking_id, present=choice == 1)
            print(formatters.format_booking(result, timezone_name=self._timezone_name))

    def complete(self) -> None:
        """组织 AttendanceService.complete 的交互步骤。

        展示课次和扣除的一节课，确认结算后再调用服务；成功展示消费记录。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AttendanceHandler.complete 尚未实现")

    def mark_no_show(self) -> None:
        """组织 AttendanceService.mark_no_show 的交互步骤。

        展示课次并说明不扣节数，确认标记缺席后再调用服务。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AttendanceHandler.mark_no_show 尚未实现")
