"""应用资源、服务装配与登录身份管理。"""

from __future__ import annotations

from dataclasses import dataclass

from src.config import AppSettings
from src.models.contracts import Actor
from src.services.attendance_service import AttendanceService
from src.services.auth_service import AuthService
from src.services.booking_service import BookingService
from src.services.product_service import ProductService
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
    products: ProductService
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
        """保存部署配置；资源在 start 中创建。"""
        self.settings = settings
        self._engine = None
        self._services: ServiceBundle | None = None
        self._cli = None
        self._actor: Actor | None = None

    def start(self) -> None:
        """检查数据库结构并装配服务和 CLI。"""
        from src.db.connection import (
            CURRENT_SCHEMA_VERSION,
            check_connection,
            check_schema,
            create_engine,
            create_session_factory,
        )
        from src.errors.business import InvalidState
        from src.ui.cli.app import GymCLI
        from src.ui.cli import menus

        if self._engine is not None:
            raise InvalidState("应用已经启动，请先关闭")
        self._engine = create_engine(self.settings)
        check_connection(self._engine)
        check_schema(self._engine, required_version=CURRENT_SCHEMA_VERSION)
        factory = create_session_factory(self._engine)
        zone = self.settings.timezone_name
        auth = AuthService(factory, log_config=self.settings.log)
        services = ServiceBundle(
            auth=auth, members=MemberService(factory, auth),
            products=ProductService(factory, auth, timezone_name=zone),
            courses=CourseService(factory, auth),
            bookings=BookingService(factory, auth, timezone_name=zone),
            attendance=AttendanceService(factory, auth), reviews=ReviewService(factory, auth),
            equipment=EquipmentService(factory, auth), measurements=MeasurementService(factory, auth),
            reports=ReportService(factory, auth, timezone_name=zone),
        )
        self._services = services
        handlers = menus.CliHandlers(
            auth=menus.AuthHandler(auth, self.get_actor, self.set_actor, self.logout, timezone_name=zone),
            member=menus.MemberHandler(services.members, self.get_actor, timezone_name=zone),
            product=menus.ProductHandler(services.products, self.get_actor, timezone_name=zone),
            course=menus.CourseHandler(services.courses, self.get_actor, timezone_name=zone),
            booking=menus.BookingHandler(services.bookings, self.get_actor, services.courses, services.products, timezone_name=zone),
            attendance=menus.AttendanceHandler(services.attendance, self.get_actor, timezone_name=zone),
            review=menus.ReviewHandler(services.reviews, self.get_actor, timezone_name=zone),
            equipment=menus.EquipmentHandler(services.equipment, self.get_actor, timezone_name=zone),
            measurement=menus.MeasurementHandler(services.measurements, self.get_actor, timezone_name=zone),
            report=menus.ReportHandler(services.reports, self.get_actor, timezone_name=zone),
        )
        self._cli = GymCLI(handlers, self.get_actor, self.logout)

    def run(self, *, tui: bool = False) -> int:
        """按模式启动交互；默认 CLI 不导入可选 TUI 库。"""
        from src.errors.business import InvalidState

        if tui:
            print("TUI 尚未就绪，请使用默认 CLI 启动。")
            return 1
        if self._cli is None:
            raise InvalidState("请先启动应用")
        return self._cli.run()

    def close(self) -> None:
        """清除交互状态并关闭资源；关闭失败保留引擎，允许再次清理。"""
        from src.db.connection import close_engine

        self.logout()
        self._cli = None
        self._services = None
        engine = self._engine
        if engine is not None:
            close_engine(engine)
            self._engine = None

    def get_actor(self) -> Actor:
        """读取当前可信操作者；未登录抛 AuthenticationError。"""
        from src.errors.business import AuthenticationError

        if self._actor is None:
            raise AuthenticationError("请先登录")
        return self._actor

    def set_actor(self, actor: Actor) -> None:
        """保存登录服务返回的身份，不接收用户伪造的角色。"""
        self._actor = actor

    def logout(self) -> None:
        """清除当前身份与私有交互状态，回到登录入口。"""
        self._actor = None
