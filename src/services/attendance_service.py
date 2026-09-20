"""签到与消课服务接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import Actor, BookingView, ConsumptionView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AttendanceService:
    """签到与消课服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    当前所有方法仅占位，调用会抛 NotImplementedError。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        raise NotImplementedError("AttendanceService.__init__ 尚未实现")

    def check_in(self, actor: Actor, booking_id: int) -> BookingView:
        """确认预约会员到场。

        会员可从课次开始时刻起自行签到；本课教练或前台也可代为签到。
        从开课起至预约结算前允许签到；教练下课后补签使用 correct_attendance。
        按当前状态设计，取消、完成或缺席后不能签到；越过状态边界抛 InvalidState。

        返回：BookingView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AttendanceService.check_in 尚未实现")

    def correct_attendance(
        self, actor: Actor, booking_id: int, present: bool,
    ) -> BookingView:
        """由本课教练或管理员更正会员的到场选择。

        present=True 为未结算预约补签，时间记录实际操作时刻；允许下课后办理。
        present=False 将已签到记录改回 reserved，并清空签到时间；相同选择返回当前记录。
        不扣或恢复私教节数，不以操作当天卡过期为由拒绝合法原预约，也不恢复体测更新权限。
        取消、完成或缺席状态拒绝更正，抛 InvalidState；首版不提供结算后冲正。
        前台不能使用更正接口；记录操作者与前后状态，但不在日志保存体测数据。
        返回固定的 BookingView；当前仅占位。"""
        raise NotImplementedError("AttendanceService.correct_attendance 尚未实现")

    def complete(self, actor: Actor, booking_id: int) -> ConsumptionView:
        """本课教练或管理员在下课后登记消课，扣除 1 节私教并释放 1 节占用。

        只处理 checked_in 预约；重复消课返回原 ConsumptionView，不扣门禁次数。
        来源卡日期资格按原上课日期检查，不因事后结算时卡过期而拒绝。
        界面须在调用前确认结算，完成后首版不提供退节数或修改签到入口。

        返回：ConsumptionView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AttendanceService.complete 尚未实现")

    def mark_no_show(self, actor: Actor, booking_id: int) -> BookingView:
        """本课教练或管理员在下课后将 reserved 预约登记为缺席，释放 1 节占用。

        不扣私教节数、不创建消费记录；重复处理返回当前 BookingView。
        界面须先确认，结算后首版不再开放补签。

        返回：BookingView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AttendanceService.mark_no_show 尚未实现")
