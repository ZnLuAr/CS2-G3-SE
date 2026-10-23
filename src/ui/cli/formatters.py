"""固定数据对象的中文文本格式化接口。时刻按传入的门店时区显示，日期保持不变。

当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


_KIND_LABELS = {"private": "私教"}
_SESSION_STATUS_LABELS = {
    "scheduled": "已排课",
    "completed": "已完成",
    "cancelled": "已取消",
}
_BOOKING_STATUS_LABELS = {
    "reserved": "已预约",
    "cancelled": "已取消",
    "checked_in": "已签到",
    "completed": "已完成",
    "no_show": "缺席",
}


def _zone(timezone_name: str):
    """取得门店时区；配置异常时退回 UTC，保证展示不中断。"""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return timezone.utc


def _time_text(value: datetime | None, zone) -> str:
    """把 UTC 时刻转成门店时区的“年-月-日 时:分”；空值显示为横线。"""
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(zone).strftime("%Y-%m-%d %H:%M")


def _range_text(start: datetime | None, end: datetime | None, zone) -> str:
    """展示时间范围；同一天只显示一次日期，跨午夜时两端都带日期。"""
    if start is None or end is None:
        return "—"
    start_text = _time_text(start, zone)
    end_text = _time_text(end, zone)
    if start.astimezone(zone).date() == end.astimezone(zone).date():
        return f"{start_text}–{end_text.split(' ', 1)[-1]}"
    return f"{start_text}–{end_text}"


def _active_text(is_active: bool) -> str:
    """启用状态的中文展示。"""
    return "启用" if is_active else "停用"


def _page_text(page, formatter, timezone_name: str, empty_text: str) -> str:
    """把 Page 渲染成“汇总一行 + 每条一行”；空页也保留总数和页码。"""
    summary = f"共 {page.total} 条，第 {page.page} 页，每页 {page.page_size} 条"
    if not page.items:
        return f"{empty_text}（{summary}）"
    lines = [summary]
    lines.extend(formatter(item, timezone_name=timezone_name) for item in page.items)
    return "\n".join(lines)


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
    """把 CoachView 转成展示文字；不输入、不打印、不查数据库。"""
    specialty = view.specialty or "（未填写）"
    return (
        f"教练 #{view.id}：{view.name}｜专长：{specialty}"
        f"｜状态：{_active_text(view.is_active)}｜账号 #{view.account_id}"
    )


def format_course(view: CourseView, *, timezone_name: str) -> str:
    """把 CourseView 转成展示文字；不输入、不打印、不查数据库。"""
    kind = _KIND_LABELS.get(view.kind, view.kind)
    return (
        f"课程 #{view.id}：{view.name}｜类型：{kind}"
        f"｜默认时长：{view.duration_minutes} 分钟"
        f"｜状态：{'启用' if view.is_active else '已归档'}"
    )


def format_room(view: RoomView, *, timezone_name: str) -> str:
    """把 RoomView 转成展示文字；不输入、不打印、不查数据库。"""
    return (
        f"场地 #{view.id}：{view.name}｜容量：{view.capacity} 人"
        f"｜状态：{_active_text(view.is_active)}"
    )


def format_session(view: SessionView, *, timezone_name: str) -> str:
    """把 SessionView 转成展示文字；不输入、不打印、不查数据库。"""
    zone = _zone(timezone_name)
    kind = _KIND_LABELS.get(view.kind, view.kind)
    status = _SESSION_STATUS_LABELS.get(view.status, view.status)
    return (
        f"课次 #{view.id}：{_range_text(view.starts_at, view.ends_at, zone)}"
        f"｜{view.course_name}（{kind}）"
        f"｜教练：{view.coach_name}｜场地：{view.room_name}"
        f"｜{view.occupied_count}/{view.capacity} 人"
        f"｜状态：{status}"
    )


def format_booking(view: BookingView, *, timezone_name: str) -> str:
    """把 BookingView 转成展示文字；不输入、不打印、不查数据库。"""
    zone = _zone(timezone_name)
    status = _BOOKING_STATUS_LABELS.get(view.status, view.status)
    return (
        f"预约 #{view.id}：{view.member_name}（会员 #{view.member_id}）"
        f"｜会员卡 #{view.membership_id}｜状态：{status}\n"
        f"  课次 #{view.session.id}：{_range_text(view.session.starts_at, view.session.ends_at, zone)}"
        f"｜{view.session.course_name}｜教练：{view.session.coach_name}"
        f"｜场地：{view.session.room_name}"
        f"｜预约于 {_time_text(view.booked_at, zone)}"
    )


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
    return _page_text(page, format_coach, timezone_name, "暂无教练记录")

def format_courses(page: Page[CourseView], *, timezone_name: str) -> str:
    """把 CourseView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    return _page_text(page, format_course, timezone_name, "暂无课程模板")

def format_rooms(page: Page[RoomView], *, timezone_name: str) -> str:
    """把 RoomView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    return _page_text(page, format_room, timezone_name, "暂无场地记录")

def format_sessions(page: Page[SessionView], *, timezone_name: str) -> str:
    """把 SessionView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    return _page_text(page, format_session, timezone_name, "暂无课次记录")

def format_bookings(page: Page[BookingView], *, timezone_name: str) -> str:
    """把 BookingView 的分页结果转成列表文字。

    空页仍读取 Page 的 total 和页码；不接受临时字典或裸列表。"""
    return _page_text(page, format_booking, timezone_name, "暂无预约记录")

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
