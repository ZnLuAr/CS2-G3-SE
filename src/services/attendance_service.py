"""签到与消课服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import Actor, BookingView, ConsumptionView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AttendanceService:
    """签到与消课服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md的返回、异常、权限和事务约定。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def check_in(self, session: Session, actor: Actor, booking_id: int) -> BookingView:
        """确认预约会员到场。

        锁定预约后生成当前时刻；会员可从课次开始时刻起自行签到，本课教练、前台或管理员可代为签到。
        普通签到时间为 starts_at <= now < ends_at；本课教练或管理员课后补签使用 correct_attendance。
        按当前状态设计，取消、完成或缺席后不能签到；越过状态边界抛 InvalidState。

        返回：BookingView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AttendanceService.check_in 尚未实现")

    def correct_attendance(
        self, session: Session, actor: Actor, booking_id: int, present: bool,
    ) -> BookingView:
        """由本课教练或管理员更正会员的到场选择。

        present=True 为未结算预约补签，时间记录实际操作时刻；允许下课后办理。
        present=False 将已签到记录改回 reserved，并清空签到时间；相同选择返回当前记录。
        到场更正保持课包余额，合法原预约按其上课日期资格处理。
        取消、完成或缺席状态拒绝更正，抛 InvalidState；结算后不可冲正。
        前台不能使用更正接口；记录操作者与前后状态，但不在日志保存体测数据。
        返回固定的 BookingView；当前仅占位。"""
        raise NotImplementedError("AttendanceService.correct_attendance 尚未实现")

    def complete(self, session: Session, actor: Actor, booking_id: int) -> ConsumptionView:
        """本课教练或管理员在下课后登记消课，扣除 1 节私教并释放 1 节占用。

        按会员、课次、课包、预约顺序取得锁后生成当前时刻，须大于或等于 ends_at；否则抛 InvalidState。
        已完成预约通过锁定当前读取得原消课记录；重复消课返回原 ConsumptionView，不扣门禁次数。
        原预约的课包日期资格按上课日期确定；结算时复核占用与余额不变量。
        界面须在调用前确认结算；完成后不退还课节，也不修改签到状态。

        返回：ConsumptionView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AttendanceService.complete 尚未实现")

    def mark_no_show(self, session: Session, actor: Actor, booking_id: int) -> BookingView:
        """本课教练或管理员在下课后将 reserved 预约登记为缺席，释放 1 节占用。

        按会员、课次、课包、预约顺序取得锁后生成当前时刻，须大于或等于 ends_at；否则抛 InvalidState。
        不扣私教节数、不创建消费记录；重复处理返回当前 BookingView。
        界面须先确认；标记缺席后不可补签。

        返回：BookingView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AttendanceService.mark_no_show 尚未实现")
