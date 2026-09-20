"""固定数据对象的中文文本格式化接口。时刻按传入的门店时区显示，日期保持不变。

当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from src.models.contracts import (
    AccountView,
    BookingView,
    CardProductView,
    CardView,
    CoachStatsView,
    CoachView,
    ConsumptionView,
    CourseView,
    EntryView,
    EquipmentView,
    MaintenanceView,
    MeasurementComparison,
    MeasurementView,
    MemberView,
    MembershipStats,
    Page,
    PaymentView,
    RevenueView,
    ReviewView,
    RoomView,
    SaleView,
    SessionStatsView,
    SessionView,
)


def format_account(view: AccountView, *, timezone_name: str) -> str:
    """把 AccountView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_account 尚未实现")


def format_member(member: MemberView, *, timezone_name: str) -> str:
    """把 MemberView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_member 尚未实现")


def format_card_product(view: CardProductView, *, timezone_name: str) -> str:
    """把 CardProductView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_card_product 尚未实现")


def format_card(view: CardView, *, timezone_name: str) -> str:
    """把 CardView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_card 尚未实现")


def format_sale(view: SaleView, *, timezone_name: str) -> str:
    """把 SaleView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_sale 尚未实现")


def format_entry(view: EntryView, *, timezone_name: str) -> str:
    """展示当日首次入场时刻、卡和当日扣次；不查询、不打印。

    accesses_used 是当日首次扣减量，重复显示不表示再次扣次；当前仅占位。"""
    raise NotImplementedError("format_entry 尚未实现")


def format_coach(view: CoachView, *, timezone_name: str) -> str:
    """把 CoachView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_coach 尚未实现")


def format_course(view: CourseView, *, timezone_name: str) -> str:
    """把 CourseView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_course 尚未实现")


def format_room(view: RoomView, *, timezone_name: str) -> str:
    """把 RoomView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_room 尚未实现")


def format_session(view: SessionView, *, timezone_name: str) -> str:
    """把 SessionView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_session 尚未实现")


def format_booking(view: BookingView, *, timezone_name: str) -> str:
    """把 BookingView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_booking 尚未实现")


def format_consumption(view: ConsumptionView, *, timezone_name: str) -> str:
    """把 ConsumptionView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_consumption 尚未实现")


def format_review(view: ReviewView, *, timezone_name: str) -> str:
    """把 ReviewView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_review 尚未实现")


def format_equipment(view: EquipmentView, *, timezone_name: str) -> str:
    """把 EquipmentView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_equipment 尚未实现")


def format_maintenance(view: MaintenanceView, *, timezone_name: str) -> str:
    """把 MaintenanceView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_maintenance 尚未实现")


def format_measurement(view: MeasurementView, *, timezone_name: str) -> str:
    """把 MeasurementView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_measurement 尚未实现")


def format_measurement_comparison(view: MeasurementComparison, *, timezone_name: str) -> str:
    """把 MeasurementComparison 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_measurement_comparison 尚未实现")


def format_payment(view: PaymentView, *, timezone_name: str) -> str:
    """把 PaymentView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_payment 尚未实现")


def format_revenue(view: RevenueView, *, timezone_name: str) -> str:
    """把 RevenueView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_revenue 尚未实现")


def format_membership_stats(view: MembershipStats, *, timezone_name: str) -> str:
    """把 MembershipStats 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_membership_stats 尚未实现")


def format_session_stats(view: SessionStatsView, *, timezone_name: str) -> str:
    """把 SessionStatsView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_session_stats 尚未实现")


def format_coach_stats(view: CoachStatsView, *, timezone_name: str) -> str:
    """把 CoachStatsView 转成展示文字；不输入、不打印、不查数据库。

    金额、时间、状态和空值的显示规则见设计；当前调用抛 NotImplementedError。"""
    raise NotImplementedError("format_coach_stats 尚未实现")


def format_accounts(page: Page[AccountView], *, timezone_name: str) -> str:
    """把 AccountView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_accounts 尚未实现")


def format_members(page: Page[MemberView], *, timezone_name: str) -> str:
    """把 MemberView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_members 尚未实现")


def format_products(page: Page[CardProductView], *, timezone_name: str) -> str:
    """把 CardProductView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_products 尚未实现")


def format_cards(page: Page[CardView], *, timezone_name: str) -> str:
    """把 CardView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_cards 尚未实现")


def format_coaches(page: Page[CoachView], *, timezone_name: str) -> str:
    """把 CoachView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_coaches 尚未实现")


def format_courses(page: Page[CourseView], *, timezone_name: str) -> str:
    """把 CourseView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_courses 尚未实现")


def format_rooms(page: Page[RoomView], *, timezone_name: str) -> str:
    """把 RoomView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_rooms 尚未实现")


def format_sessions(page: Page[SessionView], *, timezone_name: str) -> str:
    """把 SessionView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_sessions 尚未实现")


def format_bookings(page: Page[BookingView], *, timezone_name: str) -> str:
    """把 BookingView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_bookings 尚未实现")


def format_reviews(page: Page[ReviewView], *, timezone_name: str) -> str:
    """把 ReviewView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_reviews 尚未实现")


def format_equipment_list(page: Page[EquipmentView], *, timezone_name: str) -> str:
    """把 EquipmentView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_equipment_list 尚未实现")


def format_maintenance_records(page: Page[MaintenanceView], *, timezone_name: str) -> str:
    """把 MaintenanceView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_maintenance_records 尚未实现")


def format_measurements(page: Page[MeasurementView], *, timezone_name: str) -> str:
    """把 MeasurementView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_measurements 尚未实现")


def format_payments(page: Page[PaymentView], *, timezone_name: str) -> str:
    """把 PaymentView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_payments 尚未实现")


def format_session_stats_page(page: Page[SessionStatsView], *, timezone_name: str) -> str:
    """把 SessionStatsView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_session_stats_page 尚未实现")


def format_coach_stats_page(page: Page[CoachStatsView], *, timezone_name: str) -> str:
    """把 CoachStatsView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    raise NotImplementedError("format_coach_stats_page 尚未实现")
