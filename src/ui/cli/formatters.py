"""按固定 View 字段展示中文文本；权限由调用服务检查。"""


from __future__ import annotations
from src.models.contracts import AccountView, BookingView, CoachStatsView, CoachView, CourseView, EntryView, EquipmentView, MaintenanceView, MeasurementComparison, MeasurementView, MemberView, MembershipStats, Page, PaymentView, RevenueView, ReviewView, RoomView, SessionStatsView, SessionView



from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import TypeVar
from zoneinfo import ZoneInfo

T = TypeVar("T")
_WORDS = {
    "member": "会员", "coach": "教练", "receptionist": "前台", "admin": "管理员",
    "monthly": "月产品", "quarterly": "季产品", "yearly": "年产品", "count": "入场次卡",
    "active": "有效", "archived": "已归档", "void": "已作废", "private": "私教", "scheduled": "已排课",
    "completed": "已完成", "cancelled": "已取消", "reserved": "已预约", "checked_in": "已签到",
    "no_show": "缺席", "available": "可用", "maintenance": "维修中", "retired": "已报废",
    "cash": "现金", "card": "刷卡", "transfer": "转账", "gym_card": "健身房卡",
    "lesson_package": "私教课包", "duration_gym_card": "期限卡", "visit_gym_card": "入场次卡",
    "booking": "私教预约",
}


def _text(value: str) -> str:
    """使终端控制字符可见，避免备注改变终端内容。"""
    return "".join(c if c.isprintable() else repr(c)[1:-1] for c in value)


def _value(value: object, zone: str) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("展示时刻必须带时区")
        return value.astimezone(ZoneInfo(zone)).strftime("%Y-%m-%d %H:%M:%S %z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, ".2f")
    return _text(str(value))


def _phone(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:3] + "****" + value[-4:] if len(value) == 11 else "****"


def _lines(values: list[tuple[str, object]], zone: str) -> str:
    return "\n".join(f"{label}：{_value(value, zone)}" for label, value in values)


def _page(page: Page[T], formatter: Callable[..., str], zone: str) -> str:
    pages = max(1, (page.total + page.page_size - 1) // page.page_size)
    header = f"第 {page.page}/{pages} 页，共 {page.total} 条"
    content = "\n\n".join(formatter(item, timezone_name=zone) for item in page.items)
    return header + "\n" + (content or "暂无记录。")



def format_account(view: AccountView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("用户名", view.username),
        ("角色", _WORDS[view.role]),
        ("启用", view.is_active),
        ("会员编号", view.member_id),
        ("教练编号", view.coach_id),
    ], timezone_name)
    return details


def format_member(member: MemberView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", member.id),
        ("名称", member.name),
        ("电话", _phone(member.phone)),
        ("状态", _WORDS[member.status]),
        ("归档时刻", member.archived_at),
        ("创建时刻", member.created_at),
        ("更新时间", member.updated_at),
    ], timezone_name)
    return details


def format_entry(view: EntryView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    source = view.authorization
    source_id = getattr(source, "gym_card_id", None)
    if source_id is None:
        source_id = getattr(source, "booking_id", None)
    values = [
        ("编号", view.id),
        ("会员编号", view.member_id),
        ("入场日期", view.business_date),
        ("首次入场时刻", view.entered_at),
        ("入场来源", _WORDS[source.kind]),
        ("来源编号", source_id),
        ("操作人编号", view.operator_id),
    ]
    if source.kind == "visit_gym_card":
        values.insert(-1, ("剩余入场次数", source.remaining_entries))
    return _lines(values, timezone_name)


def format_coach(view: CoachView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("名称", view.name),
        ("电话", _phone(view.phone)),
        ("启用", view.is_active),
        ("创建时刻", view.created_at),
        ("更新时间", view.updated_at),
    ], timezone_name)
    return details


def format_course(view: CourseView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("名称", view.name),
        ("类型", _WORDS[view.kind]),
        ("时长（分钟）", view.duration_minutes),
        ("启用", view.is_active),
    ], timezone_name)
    return details


def format_room(view: RoomView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("名称", view.name),
        ("位置", view.location),
        ("启用", view.is_active),
        ("创建时刻", view.created_at),
        ("更新时间", view.updated_at),
    ], timezone_name)
    return details


def format_session(view: SessionView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("课程编号", view.course.id),
        ("课程", view.course_name),
        ("类型", _WORDS[view.kind]),
        ("时长（分钟）", view.duration_minutes),
        ("教练编号", view.coach.id),
        ("教练", view.coach.name),
        ("场地编号", view.room.id),
        ("场地", view.room.name),
        ("开始时刻", view.starts_at),
        ("结束时刻", view.ends_at),
        ("容量", view.capacity),
        ("已占名额", view.occupied_count),
        ("可用名额", view.available_count),
        ("状态", _WORDS[view.status]),
    ], timezone_name)
    return details


def format_booking(view: BookingView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("会员编号", view.member_id),
        ("会员", view.member_name),
        ("私教课包编号", view.lesson_package_id),
        ("状态", _WORDS[view.status]),
        ("预约时刻", view.booked_at),
        ("签到时刻", view.checked_in_at),
        ("结算时刻", view.closed_at),
    ], timezone_name)
    return details + "\n" + "课次：\n" + format_session(view.session, timezone_name=timezone_name)


def format_review(view: ReviewView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("预约编号", view.booking_id),
        ("会员编号", view.member_id),
        ("课次编号", view.session_id),
        ("评分", view.rating),
        ("评价", view.comment),
        ("创建时刻", view.created_at),
    ], timezone_name)
    return details


def format_equipment(view: EquipmentView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("资产编号", view.asset_code),
        ("名称", view.name),
        ("位置", view.location),
        ("状态", _WORDS[view.status]),
    ], timezone_name)
    return details


def format_maintenance(view: MaintenanceView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("器械编号", view.equipment_id),
        ("描述", view.description),
        ("报修时刻", view.reported_at),
        ("解决时刻", view.resolved_at),
        ("操作人编号", view.operator_id),
        ("解决人编号", view.resolved_by),
    ], timezone_name)
    return details


def format_measurement(view: MeasurementView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("会员编号", view.member_id),
        ("教练编号", view.coach_id),
        ("测量时刻", view.measured_at),
        ("身高（厘米）", view.height_cm),
        ("体重（千克）", view.weight_kg),
        ("体脂率（%）", view.body_fat_pct),
    ], timezone_name)
    return details


def format_measurement_comparison(view: MeasurementComparison, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("身高变化（厘米）", view.height_delta_cm),
        ("体重变化（千克）", view.weight_delta_kg),
        ("体脂率变化（百分点）", view.body_fat_delta_pct),
    ], timezone_name)
    return details + "\n" + "对比前：\n" + format_measurement(view.before, timezone_name=timezone_name) + "\n" + "对比后：\n" + format_measurement(view.after, timezone_name=timezone_name)


def format_payment(view: PaymentView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("编号", view.id),
        ("销售单编号", view.sale_order_id),
        ("会员编号", view.member_id),
        ("金额", view.amount),
        ("收款方式", _WORDS[view.method]),
        ("收款时刻", view.paid_at),
        ("操作人编号", view.operator_id),
    ], timezone_name)
    return details


def format_revenue(view: RevenueView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("起始时刻（含）", view.window.start),
        ("结束时刻（不含）", view.window.end),
        ("收款笔数", view.total_payment_count),
        ("总金额", view.total_amount),
    ], timezone_name)
    breakdowns = "\n".join(
        f"{_WORDS[item.sale_kind]}：{item.payment_count} 笔，{_value(item.total_amount, timezone_name)} 元"
        for item in view.breakdowns
    )
    return details + ("\n" + breakdowns if breakdowns else "")


def format_membership_stats(view: MembershipStats, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("统计时刻", view.as_of),
        ("统计日期", view.business_date),
        ("有效会员档案", view.active_member_profiles),
        ("已归档会员档案", view.archived_member_profiles),
        ("有效期限卡", view.valid_duration_gym_card_count),
        ("可用入场次卡", view.usable_visit_gym_card_count),
        ("有门禁资格的会员", view.members_with_gym_access),
        ("未生效期限卡", view.future_duration_gym_cards),
        ("过期期限卡", view.expired_duration_gym_cards),
        ("用尽入场次卡", view.exhausted_visit_gym_cards),
        ("作废健身房卡", view.void_gym_cards),
        ("剩余入场次数", view.remaining_visit_entries),
        ("有效私教课包", view.active_lesson_package_count),
        ("未生效课包", view.future_lesson_packages),
        ("过期课包", view.expired_lesson_packages),
        ("作废课包", view.void_lesson_packages),
        ("用尽课包", view.exhausted_lesson_packages),
        ("剩余课节", view.remaining_lessons),
        ("可用课节", view.available_lessons),
        ("已预约课节", view.reserved_lessons),
    ], timezone_name)
    return details


def format_session_stats(view: SessionStatsView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("课次编号", view.session_id),
        ("开始时刻", view.starts_at),
        ("待签到", view.reserved_count),
        ("已签到", view.checked_in_count),
        ("已消课", view.completed_count),
        ("缺席", view.no_show_count),
        ("取消", view.cancelled_count),
        ("出勤率", None if view.attendance_rate is None else format(view.attendance_rate, ".2%")),
    ], timezone_name)
    return details


def format_coach_stats(view: CoachStatsView, *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    details = _lines([
        ("教练编号", view.coach_id),
        ("教练", view.coach_name),
        ("完成课次", view.completed_sessions),
        ("到课人次", view.attended_members),
    ], timezone_name)
    return details


def format_accounts(page: Page[AccountView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_account, timezone_name)


def format_members(page: Page[MemberView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_member, timezone_name)


def format_coaches(page: Page[CoachView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_coach, timezone_name)


def format_courses(page: Page[CourseView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_course, timezone_name)


def format_rooms(page: Page[RoomView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_room, timezone_name)


def format_sessions(page: Page[SessionView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_session, timezone_name)


def format_bookings(page: Page[BookingView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_booking, timezone_name)


def format_reviews(page: Page[ReviewView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_review, timezone_name)


def format_equipment_list(page: Page[EquipmentView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_equipment, timezone_name)


def format_maintenance_records(page: Page[MaintenanceView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_maintenance, timezone_name)


def format_measurements(page: Page[MeasurementView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_measurement, timezone_name)


def format_payments(page: Page[PaymentView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_payment, timezone_name)


def format_session_stats_page(page: Page[SessionStatsView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_session_stats, timezone_name)


def format_coach_stats_page(page: Page[CoachStatsView], *, timezone_name: str) -> str:
    """返回中文展示文本。"""
    return _page(page, format_coach_stats, timezone_name)
