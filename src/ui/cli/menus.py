"""菜单项与分模块导航接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.ui.cli.handlers.attendance import AttendanceHandler
from src.ui.cli.handlers.auth import AuthHandler
from src.ui.cli.handlers.booking import BookingHandler
from src.ui.cli.handlers.product import ProductHandler
from src.ui.cli.handlers.course import CourseHandler
from src.ui.cli.handlers.equipment import EquipmentHandler
from src.ui.cli.handlers.measurement import MeasurementHandler
from src.ui.cli.handlers.member import MemberHandler
from src.ui.cli.handlers.report import ReportHandler
from src.ui.cli.handlers.review import ReviewHandler


@dataclass(frozen=True, kw_only=True)
class MenuItem:
    """选择键、中文文字与对应的无参数交互方法。"""

    key: str
    label: str
    action: Callable[[], None]


@dataclass(frozen=True, kw_only=True)
class CliHandlers:
    """菜单可调用的交互处理器，按模块固定字段。"""

    auth: AuthHandler
    member: MemberHandler
    product: ProductHandler
    course: CourseHandler
    booking: BookingHandler
    attendance: AttendanceHandler
    review: ReviewHandler
    equipment: EquipmentHandler
    measurement: MeasurementHandler
    report: ReportHandler


def auth_menu(handler: AuthHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("auth_menu 尚未实现")


def member_menu(handler: MemberHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("member_menu 尚未实现")


def product_menu(handler: ProductHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("product_menu 尚未实现")


def course_menu(handler: CourseHandler) -> list[MenuItem]:
    """构造课程与教练模块的菜单项。

    菜单只列出本模块已经接入服务的操作；每个 action 都是无参数方法，
    由 CLI 主循环交给统一异常处理入口执行。
    """
    return [
        MenuItem(key="1", label="创建教练档案", action=handler.create_coach),
        MenuItem(key="2", label="修改教练资料", action=handler.update_coach),
        MenuItem(key="3", label="查看教练详情", action=handler.get_coach),
        MenuItem(key="4", label="教练列表", action=handler.list_coaches),
        MenuItem(key="5", label="停用/恢复教练", action=handler.set_coach_active),
        MenuItem(key="6", label="创建课程模板", action=handler.create_course),
        MenuItem(key="7", label="修改课程模板", action=handler.update_course),
        MenuItem(key="8", label="查看课程模板", action=handler.get_course),
        MenuItem(key="9", label="课程模板列表", action=handler.list_courses),
        MenuItem(key="10", label="归档/恢复课程模板", action=handler.set_course_active),
        MenuItem(key="11", label="新增场地", action=handler.create_room),
        MenuItem(key="12", label="修改场地", action=handler.update_room),
        MenuItem(key="13", label="查看场地详情", action=handler.get_room),
        MenuItem(key="14", label="场地列表", action=handler.list_rooms),
        MenuItem(key="15", label="停用/恢复场地", action=handler.set_room_active),
        MenuItem(key="16", label="发布课次（排课）", action=handler.create_session),
        MenuItem(key="17", label="查看课次详情", action=handler.get_session),
        MenuItem(key="18", label="课表查询", action=handler.list_sessions),
        MenuItem(key="19", label="按请求编号核实课次", action=handler.get_session_by_request),
        MenuItem(key="20", label="完成课次", action=handler.complete_session),
        MenuItem(key="21", label="取消课次", action=handler.cancel_session),
    ]


def booking_menu(handler: BookingHandler) -> list[MenuItem]:
    """构造预约模块的菜单项。

    会员预约时自动使用本人编号；前台和管理员由处理器提示输入代约会员。
    """
    return [
        MenuItem(key="1", label="预约课次", action=handler.book),
        MenuItem(key="2", label="查看预约详情", action=handler.get_booking),
        MenuItem(key="3", label="按请求编号核实预约", action=handler.get_booking_by_request),
        MenuItem(key="4", label="取消预约", action=handler.cancel),
        MenuItem(key="5", label="预约列表", action=handler.list_bookings),
    ]


def attendance_menu(handler: AttendanceHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("attendance_menu 尚未实现")


def review_menu(handler: ReviewHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("review_menu 尚未实现")


def equipment_menu(handler: EquipmentHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("equipment_menu 尚未实现")


def measurement_menu(handler: MeasurementHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("measurement_menu 尚未实现")


def report_menu(handler: ReportHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("report_menu 尚未实现")
