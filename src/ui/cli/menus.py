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
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
    return []


def report_menu(handler: ReportHandler) -> list[MenuItem]:
    """构造本模块的已实现菜单入口。

    只返回界面菜单项；业务列表仍使用 Page。当前不注册可执行操作。"""
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
