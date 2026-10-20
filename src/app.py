"""应用资源、用例入口装配与登录身份管理。"""

from __future__ import annotations

from src.config import AppSettings
from src.logic import LogicBundle
from src.logic.access_logic import AccessLogic
from src.logic.attendance_logic import AttendanceLogic
from src.logic.auth_logic import AuthLogic
from src.logic.course_logic import CourseLogic
from src.logic.entitlement_logic import EntitlementLogic
from src.logic.equipment_logic import EquipmentLogic
from src.logic.measurement_logic import MeasurementLogic
from src.logic.member_logic import MemberLogic
from src.logic.notification_logic import NotificationLogic
from src.logic.product_logic import ProductLogic
from src.logic.recommendation_logic import RecommendationLogic
from src.logic.report_logic import ReportLogic
from src.logic.reservation_logic import ReservationLogic
from src.logic.review_logic import ReviewLogic
from src.logic.sales_logic import SalesLogic
from src.models.contracts import Actor
from src.services.access_service import AccessService
from src.services.attendance_service import AttendanceService
from src.services.auth_service import AuthService
from src.services.booking_service import BookingService
from src.services.coach_service import CoachService
from src.services.course_service import CourseService
from src.services.entitlement_query_service import EntitlementQueryService
from src.services.equipment_service import EquipmentService
from src.services.gym_card_product_service import GymCardProductService
from src.services.lesson_package_product_service import LessonPackageProductService
from src.services.measurement_service import MeasurementService
from src.services.member_service import MemberService
from src.services.notification_service import NotificationService
from src.services.recommendation_service import RecommendationService
from src.services.recommendation_snapshot import RecommendationSnapshotStore
from src.services.report_service import ReportService
from src.services.review_service import ReviewService
from src.services.room_service import RoomService
from src.services.sales_service import SalesService
from src.services.waitlist_service import WaitlistService


class App:
    """管理应用生命周期及当前登录身份。"""

    def __init__(self, settings: AppSettings) -> None:
        """保存部署配置；资源在 start 中创建。"""
        self.settings = settings
        self._engine = None
        self._logic_bundle: LogicBundle | None = None
        self._cli = None
        self._actor: Actor | None = None
        self._worker = None

    def start(self, *, with_worker: bool = True) -> None:
        """检查结构并装配服务与 CLI，默认同时启动候补核对和推荐刷新。"""
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
        auth = AuthService(log_config=self.settings.log)
        members = MemberService(auth)
        gym_card_products = GymCardProductService(auth)
        lesson_package_products = LessonPackageProductService(auth)
        sales = SalesService(auth)
        entitlements = EntitlementQueryService(auth)
        access = AccessService(auth)
        coaches = CoachService(auth)
        courses = CourseService(auth)
        rooms = RoomService(auth)
        bookings = BookingService(auth, timezone_name=zone)
        attendance = AttendanceService(auth)
        reviews = ReviewService(auth)
        equipment = EquipmentService(auth)
        measurements = MeasurementService(auth)
        reports = ReportService(auth, timezone_name=zone)
        notifications = NotificationService(auth)
        waitlists = WaitlistService(auth)
        recommendation_snapshots = RecommendationSnapshotStore()
        recommendations = RecommendationService(auth, recommendation_snapshots)
        logic = LogicBundle(
            auth=AuthLogic(factory, auth),
            members=MemberLogic(factory, members),
            products=ProductLogic(factory, gym_card_products, lesson_package_products),
            sales=SalesLogic(factory, sales),
            entitlements=EntitlementLogic(factory, entitlements),
            access=AccessLogic(factory, access),
            courses=CourseLogic(factory, coaches, courses, rooms),
            reservations=ReservationLogic(factory, bookings, courses, notifications, waitlists),
            attendance=AttendanceLogic(factory, attendance),
            reviews=ReviewLogic(factory, reviews),
            equipment=EquipmentLogic(factory, equipment),
            measurements=MeasurementLogic(factory, measurements),
            reports=ReportLogic(factory, reports),
            notifications=NotificationLogic(factory, notifications),
            recommendations=RecommendationLogic(factory, recommendations, recommendation_snapshots),
        )
        self._logic_bundle = logic
        handlers = menus.CliHandlers(
            auth=menus.AuthHandler(
                logic.auth, self.get_actor, self.set_actor, self.logout,
                timezone_name=zone,
            ),
            member=menus.MemberHandler(logic.members, self.get_actor, timezone_name=zone),
            product=menus.ProductHandler(
                logic.products, logic.sales, logic.entitlements, logic.access,
                self.get_actor, timezone_name=zone,
            ),
            course=menus.CourseHandler(logic.courses, self.get_actor, timezone_name=zone),
            booking=menus.BookingHandler(
                logic.reservations, self.get_actor, logic.courses, logic.entitlements,
                timezone_name=zone,
            ),
            attendance=menus.AttendanceHandler(logic.attendance, self.get_actor, timezone_name=zone),
            review=menus.ReviewHandler(logic.reviews, self.get_actor, timezone_name=zone),
            equipment=menus.EquipmentHandler(logic.equipment, self.get_actor, timezone_name=zone),
            measurement=menus.MeasurementHandler(logic.measurements, self.get_actor, timezone_name=zone),
            report=menus.ReportHandler(logic.reports, self.get_actor, timezone_name=zone),
            notification=menus.NotificationHandler(
                logic.notifications, self.get_actor, timezone_name=zone,
            ),
            recommendation=menus.RecommendationHandler(
                logic.recommendations, self.get_actor, timezone_name=zone,
            ),
        )
        self._cli = GymCLI(handlers, self.get_actor, self.logout)
        if with_worker:
            from src.tasks.worker import PeriodicTask, PeriodicWorker

            worker = PeriodicWorker(
                (
                    PeriodicTask(
                        name="waitlist_reconciliation",
                        interval_seconds=300,
                        callback=logic.reservations.reconcile_waitlists,
                    ),
                    PeriodicTask(
                        name="recommendation_refresh",
                        interval_seconds=30,
                        callback=logic.recommendations.refresh_snapshot,
                    ),
                )
            )
            self._worker = worker
            worker.start()

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
        """先停止后台任务，再清除交互状态并关闭数据库资源。"""
        from src.db.connection import close_engine

        worker = self._worker
        if worker is not None:
            worker.stop(timeout=30)
            self._worker = None
        self.logout()
        self._cli = None
        self._logic_bundle = None
        engine = self._engine
        if engine is not None:
            close_engine(engine)
            self._engine = None

    @property
    def logic_bundle(self) -> LogicBundle:
        """返回已装配的用例入口；应用未启动时抛 InvalidState。"""
        from src.errors.business import InvalidState

        if self._logic_bundle is None:
            raise InvalidState("请先启动应用")
        return self._logic_bundle

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
