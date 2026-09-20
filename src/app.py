"""应用资源与登录身份管理。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass

from src.config import AppSettings
from src.models.contracts import Actor
from src.services.attendance_service import AttendanceService
from src.services.auth_service import AuthService
from src.services.booking_service import BookingService
from src.services.card_service import CardService
from src.services.course_service import CourseService
from src.services.equipment_service import EquipmentService
from src.services.measurement_service import MeasurementService
from src.services.member_service import MemberService
from src.services.report_service import ReportService
from src.services.review_service import ReviewService


@dataclass(frozen=True, kw_only=True)
class ServiceBundle:
    """应用创建的各业务服务，交互层按职责取用。"""

    auth: AuthService
    members: MemberService
    cards: CardService
    courses: CourseService
    bookings: BookingService
    attendance: AttendanceService
    reviews: ReviewService
    equipment: EquipmentService
    measurements: MeasurementService
    reports: ReportService


class App:
    """管理应用生命周期及当前登录身份。"""

    def __init__(self, settings: AppSettings) -> None:
        """接收部署配置，后续由 start 创建资源。

        当前占位：调用抛 NotImplementedError。"""
        raise NotImplementedError("App.__init__ 尚未实现")

    def start(self) -> None:
        """创建日志、连接与服务；启动失败交给统一错误处理入口。

        当前占位：调用抛 NotImplementedError。"""
        raise NotImplementedError("App.start 尚未实现")

    def run(self, *, tui: bool = False) -> int:
        """按模式启动交互；默认 CLI 不导入可选 TUI 库。

        当前占位：调用抛 NotImplementedError。"""
        raise NotImplementedError("App.run 尚未实现")

    def close(self) -> None:
        """关闭本应用创建的资源；后续应允许重复清理。

        当前占位：调用抛 NotImplementedError。"""
        raise NotImplementedError("App.close 尚未实现")

    def get_actor(self) -> Actor:
        """读取当前可信操作者；实现后未登录抛 AuthenticationError。

        当前占位：调用抛 NotImplementedError。"""
        raise NotImplementedError("App.get_actor 尚未实现")

    def set_actor(self, actor: Actor) -> None:
        """保存登录服务返回的身份，不接收用户伪造的角色。

        当前占位：调用抛 NotImplementedError。"""
        raise NotImplementedError("App.set_actor 尚未实现")

    def logout(self) -> None:
        """清除当前身份与私有交互状态，回到登录入口。

        当前占位：调用抛 NotImplementedError。"""
        raise NotImplementedError("App.logout 尚未实现")
