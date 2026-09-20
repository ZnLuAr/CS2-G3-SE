"""按业务划分的 CLI 交互接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.booking_service import BookingService
from src.services.card_service import CardService
from src.services.course_service import CourseService


class BookingHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: BookingService,
        get_actor: Callable[[], Actor],
        course_service: CourseService,
        card_service: CardService,
        *, timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        raise NotImplementedError("BookingHandler.__init__ 尚未实现")

    def book(self) -> None:
        """组织 BookingService.book 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("BookingHandler.book 尚未实现")

    def get_booking(self) -> None:
        """组织 BookingService.get_booking 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("BookingHandler.get_booking 尚未实现")

    def get_booking_by_request(self) -> None:
        """采集原请求编号，调用服务只读核实预约并展示结果；异常交操作边界。

        不重新预约；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingHandler.get_booking_by_request 尚未实现")

    def cancel(self) -> None:
        """组织 BookingService.cancel 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("BookingHandler.cancel 尚未实现")

    def list_bookings(self) -> None:
        """组织 BookingService.list_bookings 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("BookingHandler.list_bookings 尚未实现")
