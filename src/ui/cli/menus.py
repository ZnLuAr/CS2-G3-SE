"""菜单项与分模块导航接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.ui.cli.handlers.attendance import AttendanceHandler
from src.ui.cli.handlers.auth import AuthHandler
from src.ui.cli.handlers.booking import BookingHandler
from src.ui.cli.handlers.card import CardHandler
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
    card: CardHandler
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


def card_menu(handler: CardHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("card_menu 尚未实现")


def course_menu(handler: CourseHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("course_menu 尚未实现")


def booking_menu(handler: BookingHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    raise NotImplementedError("booking_menu 尚未实现")


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
