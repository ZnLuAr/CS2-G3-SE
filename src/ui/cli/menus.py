"""菜单项与分模块导航接口。各模块在对应菜单函数中登记已交付操作。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from src.models.contracts import Page, PageRequest
from src.errors.business import InputCancelled, InvalidInputError

from src.ui.cli.handlers.attendance import AttendanceHandler
from src.ui.cli.handlers.auth import AuthHandler
from src.ui.cli.handlers.booking import BookingHandler
from src.ui.cli.handlers.product import ProductHandler
from src.ui.cli.handlers.course import CourseHandler
from src.ui.cli.handlers.equipment import EquipmentHandler
from src.ui.cli.handlers.measurement import MeasurementHandler
from src.ui.cli.handlers.member import MemberHandler
from src.ui.cli.handlers.notification import NotificationHandler
from src.ui.cli.handlers.recommendation import RecommendationHandler
from src.ui.cli.handlers.report import ReportHandler
from src.ui.cli.handlers.review import ReviewHandler


@dataclass(frozen=True, kw_only=True)
class MenuItem:
    """选择键、中文文字与对应的无参数交互方法。"""

    key: str
    label: str
    operation: str
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
    notification: NotificationHandler
    recommendation: RecommendationHandler


def auth_menu(handler: AuthHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def member_menu(handler: MemberHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def product_menu(handler: ProductHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def course_menu(handler: CourseHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def booking_menu(handler: BookingHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def attendance_menu(handler: AttendanceHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def review_menu(handler: ReviewHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def equipment_menu(handler: EquipmentHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def measurement_menu(handler: MeasurementHandler) -> list[MenuItem]:
    """会员和教练可查体测；教练额外显示录入入口。"""
    role = handler.current_role
    if role not in {"member", "coach"}:
        return []
    items = [
        MenuItem(key="1", label="体测详情", operation="measurement.get", action=handler.get_measurement),
        MenuItem(key="2", label="体测历史", operation="measurement.list", action=handler.list_measurements),
        MenuItem(key="3", label="体测对比", operation="measurement.compare", action=handler.compare),
    ]
    if role == "coach":
        items.append(MenuItem(
            key="4", label="录入体测", operation="measurement.record", action=handler.record,
        ))
    return items


def report_menu(handler: ReportHandler) -> list[MenuItem]:
    """前台显示收款查询；管理员增加统计及五类导出。"""
    role = handler.current_role
    if role not in {"admin", "receptionist"}:
        return []
    items = [
        MenuItem(key="1", label="收款详情", operation="report.get_payment", action=handler.get_payment),
        MenuItem(key="2", label="收款查询", operation="report.list_payments", action=handler.list_payments),
    ]
    if role == "admin":
        items.extend([
            MenuItem(key="3", label="实收统计", operation="report.revenue", action=handler.revenue),
            MenuItem(key="4", label="会员与权益统计", operation="report.membership_stats", action=handler.membership_stats),
            MenuItem(key="5", label="课次出勤统计", operation="report.session_stats", action=handler.session_stats),
            MenuItem(key="6", label="教练统计", operation="report.coach_stats", action=handler.coach_stats),
            MenuItem(key="7", label="导出收款", operation="report.export_payments", action=handler.export_payments),
            MenuItem(key="8", label="导出实收", operation="report.export_revenue", action=handler.export_revenue),
            MenuItem(
                key="9", label="导出会员与权益",
                operation="report.export_memberships", action=handler.export_memberships,
            ),
            MenuItem(key="10", label="导出课次", operation="report.export_sessions", action=handler.export_sessions),
            MenuItem(key="11", label="导出教练", operation="report.export_coaches", action=handler.export_coaches),
        ])
    return items


def notification_menu(handler: NotificationHandler) -> list[MenuItem]:
    """构造站内通知菜单；具体操作随通知功能实现接入。"""
    return []


def recommendation_menu(handler: RecommendationHandler) -> list[MenuItem]:
    """构造课程推荐菜单；具体操作随推荐功能实现接入。"""
    return []


T = TypeVar("T")


def browse_pages(fetch_page: Callable[[PageRequest], Page[T]], format_page: Callable[[Page[T]], str], *, page_size: int = 20) -> None:
    """按稳定排序查询分页；改变筛选条件后重新调用，从第一页开始。"""
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise InvalidInputError("每页条数必须是 1～100 的整数")
    page_number = 1
    while True:
        page = fetch_page(PageRequest(page=page_number, page_size=page_size))
        last_page = max(1, (page.total + page_size - 1) // page_size)
        if page_number > last_page:
            page_number = last_page
            continue
        print(format_page(page))
        while True:
            choice = input("n 下一页 / p 上一页 / 0 返回：").strip().lower()
            if choice == "0":
                return
            if choice == "q":
                raise InputCancelled()
            if choice == "n" and page_number < last_page:
                page_number += 1
                break
            if choice == "p" and page_number > 1:
                page_number -= 1
                break
            print("当前选择不可用，请重试。")
