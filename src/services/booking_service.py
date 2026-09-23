"""预约服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import Actor, BookingInput, BookingQuery, BookingView, Page
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class BookingService:
    """预约服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(
        self, session_factory: Callable[[], Session], auth: AuthService,
        *, timezone_name: str,
    ) -> None:
        """接收会话工厂、共用身份校验服务和门店时区；时区由 App 配置传入。"""
        self._session_factory = session_factory
        self._auth = auth
        self._timezone_name = timezone_name

    def book(self, actor: Actor, data: BookingInput, request_id: str) -> BookingView:
        """校验权限、私教课次时间和私教节数；同事务保存预约与节数占用。
        membership_id 固定为提供门禁资格及已购课节的同一张卡，不得组合旧卡课节与新门禁卡。
        对期限卡按课次开始时刻转门店日期检查 valid_from <= 上课日期 < valid_until。
        次卡不能约私教；未来生效的期限卡可约其有效期内的课，失败不写预约或占用余额。
        卡不适用抛 CardNotEligible；私教节数不足抛 InsufficientCredits；
        撞期抛 ScheduleConflict；满员抛 CapacityExceeded；已有预约抛 ConflictError。
        其余失败遵守公共异常规则，不能返回错误字典。"""
        raise NotImplementedError("BookingService.book 尚未实现")

    def get_booking(self, actor: Actor, booking_id: int) -> BookingView:
        """查询预约详情。

        返回：BookingView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("BookingService.get_booking 尚未实现")

    def get_booking_by_request(self, actor: Actor, request_id: str) -> BookingView:
        """按本人原预约或取消请求核实结果，返回当前 BookingView。

        不写数据；无记录或不可见抛 NotFoundError，操作类型不匹配抛 ConflictError。
        查不到不能证明原提交失败；其余异常按设计第 4.1 节。当前仅占位。"""
        raise NotImplementedError("BookingService.get_booking_by_request 尚未实现")

    def cancel(self, actor: Actor, booking_id: int, request_id: str) -> BookingView:
        """在私教课开始前取消未签到预约并释放私教节数占用。

        返回：BookingView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("BookingService.cancel 尚未实现")

    def list_bookings(self, actor: Actor, query: BookingQuery) -> Page[BookingView]:
        """在授权范围内分页查询预约。

        返回：Page[BookingView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("BookingService.list_bookings 尚未实现")
