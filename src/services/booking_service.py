"""预约服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import Actor, BookingInput, BookingQuery, BookingView, Page
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class BookingService:
    """预约服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；遵守后端架构的公共接口、权限和共享事务合同。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(
        self, auth: AuthService,
        *, timezone_name: str,
    ) -> None:
        """接收共用身份校验服务和门店时区；时区由 App 配置传入。"""
        self._auth = auth
        self._timezone_name = timezone_name

    def book(self, session: Session, actor: Actor, data: BookingInput, request_id: str) -> BookingView:
        """校验权限、私教课次时间和私教节数；同事务保存预约与节数占用。
        权限通过后先核对请求记录；会员、课次和课包锁全部取得后生成 booked_at 并复核开课边界。
        容量与会员撞期检查使用锁定当前读，不能沿用等待资源锁前建立的一致性读快照。
        lesson_package_id 指向本人 active 私教课包，按课次门店日期检查有效期，valid_until 可空。
        未来生效课包可提前预约有效期内课次；可用课节为 remaining_lessons - reserved_lessons。
        课包不适用抛 LessonPackageNotEligible；课节不足抛 InsufficientLessonCredits；
        撞期抛 ScheduleConflict；满员抛 CapacityExceeded；已有预约抛 ConflictError。
        其余失败遵守公共异常规则，不能返回错误字典。"""
        raise NotImplementedError("BookingService.book 尚未实现")

    def get_booking(self, session: Session, actor: Actor, booking_id: int) -> BookingView:
        """查询预约详情。

        返回：BookingView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md 的公共接口约定与对应领域章节的输入、权限、异常和事务约定。"""
        raise NotImplementedError("BookingService.get_booking 尚未实现")

    def get_booking_by_request(self, session: Session, actor: Actor, request_id: str) -> BookingView:
        """按本人原预约或取消请求核实结果，返回当前 BookingView。

        不写数据；无记录或不可见抛 NotFoundError，操作类型不匹配抛 ConflictError。
        查不到不能证明原提交失败；其余异常遵守 docs/architecture/backend.md 的公共接口约定与对应领域章节的约定。当前仅占位。"""
        raise NotImplementedError("BookingService.get_booking_by_request 尚未实现")

    def cancel(self, session: Session, actor: Actor, booking_id: int, request_id: str) -> BookingView:
        """在私教课开始前取消未签到预约并释放私教节数占用。

        权限通过后先核对请求记录；会员、课次、课包和预约锁全部取得后生成当前时刻并复核 starts_at。
        返回：BookingView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md 的公共接口约定与对应领域章节的输入、权限、异常和事务约定。"""
        raise NotImplementedError("BookingService.cancel 尚未实现")

    def list_bookings(self, session: Session, actor: Actor, query: BookingQuery) -> Page[BookingView]:
        """在授权范围内分页查询预约。

        返回：Page[BookingView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md 的公共接口约定与对应领域章节的输入、权限、异常和事务约定。"""
        raise NotImplementedError("BookingService.list_bookings 尚未实现")

    def reserve_for_waitlist(
        self, session: Session, data: BookingInput, booked_at: datetime,
    ) -> BookingView:
        """内部递补：在 Logic 已持有全部锁并复核队首的事务中预约。

        输入为会员、课次、课包及统一 UTC 时刻，复用普通预约的资格与冲突检查；
        返回 BookingView，创建预约并增加课节占用，重复处理由候补状态与关联核实。
        失败抛预约领域异常或 StorageError，由 Logic 回滚。当前仅占位。
        """
        raise NotImplementedError("候补预约写入尚未实现")

    def cancel_for_session(
        self, session: Session, booking_id: int, closed_at: datetime,
    ) -> BookingView:
        """内部课次取消：在稳定候选集及全部锁已取得后关闭开放预约并释放占用。

        返回 BookingView；已取消返回当前记录，不存在抛 NotFoundError，
        完成或缺席状态抛 InvalidState，存储失败抛 StorageError；Logic 提交或回滚。当前仅占位。
        """
        raise NotImplementedError("课次预约关闭尚未实现")
