"""按业务划分的 CLI 交互接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.attendance_service import AttendanceService


class AttendanceHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: AttendanceService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        self._service = service
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    def check_in(self) -> None:
        """组织 AttendanceService.check_in 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AttendanceHandler.check_in 尚未实现")

    def correct_attendance(self) -> None:
        """采集预约编号和到场选择，由本课教练或管理员更正并展示结果。

        我的课表 → 选择课次 → 学员签到情况 → 更正到场/未到场 → 确认。
        未结算预约可在下课后补签；校验交给服务，取消输入不调用写方法。
        成功展示 BookingView；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("AttendanceHandler.correct_attendance 尚未实现")

    def complete(self) -> None:
        """组织 AttendanceService.complete 的交互步骤。

        展示课次和本次扣 1 节，确认“结算后首版不支持更正”再调用服务；成功展示消费记录。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AttendanceHandler.complete 尚未实现")

    def mark_no_show(self) -> None:
        """组织 AttendanceService.mark_no_show 的交互步骤。

        展示课次并说明不扣节数，确认“标记缺席后首版不能补签”再调用服务。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AttendanceHandler.mark_no_show 尚未实现")
