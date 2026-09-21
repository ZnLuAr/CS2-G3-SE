"""接口共用的数据格式，依据 docs/architecture.md 第 3 节定义。

数据类只声明字段，不校验业务；计算属性尚未实现。
服务只能返回约定的 View 或 Page，失败抛异常，不返回临时字典。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, Literal, TypeVar

T = TypeVar("T")  # Page 可以装会员，也可以装预约等其他记录
Role = Literal["member", "coach", "receptionist", "admin"]
CardKind = Literal["monthly", "quarterly", "yearly", "count"]
# 当前只做私教课；保留课程类型字段是为了让接口语义明确，唯一允许值为 private。
CourseKind = Literal["private"]
CardStatus = Literal["active", "void"]
SessionStatus = Literal["scheduled", "completed", "cancelled"]
BookingStatus = Literal["reserved", "cancelled", "checked_in", "completed", "no_show"]
EquipmentStatus = Literal["available", "maintenance", "retired"]
PaymentMethod = Literal["cash", "card", "transfer"]  # 现金、刷卡、转账；仅记账
OperationName = Literal["sell_product", "create_session", "cancel_session", "book", "cancel_booking", "register_entry"]


@dataclass(frozen=True, kw_only=True)
class PageRequest:
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True, kw_only=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True, kw_only=True)
class DateWindow:
    start: datetime
    end: datetime  # [start, end)，开始包含、结束不包含


@dataclass(frozen=True, kw_only=True)
class NamedQuery:
    keyword: str = ""
    is_active: bool | None = None  # None 表示不过滤启用状态
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class Actor:
    account_id: int
    role: Role
    member_id: int | None
    coach_id: int | None


@dataclass(frozen=True, kw_only=True)
class AccountInput:
    username: str
    password: str = field(repr=False)  # 避免普通对象打印带出密码
    role: Role


@dataclass(frozen=True, kw_only=True)
class AccountView:
    id: int
    username: str
    role: Role
    is_active: bool
    member_id: int | None
    coach_id: int | None


@dataclass(frozen=True, kw_only=True)
class AccountLinkInput:
    member_id: int | None
    coach_id: int | None  # 恰好一项有值；将指定档案移交给空闲且角色匹配的目标账号


@dataclass(frozen=True, kw_only=True)
class MemberInput:
    name: str
    phone: str | None


@dataclass(frozen=True, kw_only=True)
class MemberView:
    id: int
    account_id: int | None
    name: str
    phone: str | None
    is_active: bool


@dataclass(frozen=True, kw_only=True)
class MemberQuery:
    member_id: int | None = None
    keyword: str = ""  # 姓名包含匹配，同名用 ID 区分
    is_active: bool | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class CoachInput:
    account_id: int
    name: str
    specialty: str


@dataclass(frozen=True, kw_only=True)
class CoachUpdateInput:
    name: str
    specialty: str  # 资料编辑不改变账号关联


@dataclass(frozen=True, kw_only=True)
class CoachView:
    id: int
    account_id: int
    name: str
    specialty: str
    is_active: bool


@dataclass(frozen=True, kw_only=True)
class CardTerms:
    name: str
    kind: CardKind
    price: Decimal
    private_lesson_credits: int  # 月/季/年固定赠送 20/64/256 节；次卡为 0
    access_uses: int | None  # 次卡为总入场次数；期限卡为 None
    valid_days: int | None  # 月/季/年固定为 30/90/365；次卡无期限，为 None


@dataclass(frozen=True, kw_only=True)
class CardProductView:
    id: int
    terms: CardTerms
    is_active: bool


@dataclass(frozen=True, kw_only=True)
class CardView:
    id: int
    member_id: int
    product_id: int
    terms: CardTerms  # 售出快照，不实时读取产品
    valid_from: date
    valid_until: date | None  # 不含此日期；次卡无期限，为 None
    remaining_accesses: int | None
    remaining_private_lessons: int
    reserved_private_lessons: int
    status: CardStatus

    @property
    def available_private_lessons(self) -> int:
        """返回账面剩余减占用；卡过期时该余额不可新预约，日期资格另由服务检查。"""
        raise NotImplementedError("CardView.available_private_lessons 尚未实现")


@dataclass(frozen=True, kw_only=True)
class CardQuery:
    member_id: int | None = None
    status: CardStatus | None = None
    valid_on: date | None = None  # 仅筛在该门店日期有效且未作废的卡
    expires_before: date | None = None  # valid_until 严格早于此日期
    private_lessons_at_most: int | None = None  # 只筛赠课产品，按剩余减占用筛选，包含阈值
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class SaleInput:
    member_id: int
    product_id: int
    method: PaymentMethod


@dataclass(frozen=True, kw_only=True)
class EntryInput:
    member_id: int
    membership_id: int  # 当日首次入场选择的卡；再次入场沿用当日记录


@dataclass(frozen=True, kw_only=True)
class EntryView:
    id: int
    member_id: int
    membership_id: int
    business_date: date  # 服务按门店时区生成，不由界面指定
    entered_at: datetime  # 当日首次登记的 UTC 时刻
    accesses_used: int  # 首次用次卡为 1，用期限卡为 0；重复调用仍返回原值
    operator_id: int


@dataclass(frozen=True, kw_only=True)
class PaymentView:
    id: int
    membership_id: int
    member_id: int
    amount: Decimal
    method: PaymentMethod
    paid_at: datetime
    operator_id: int


@dataclass(frozen=True, kw_only=True)
class SaleView:
    card: CardView
    payment: PaymentView


@dataclass(frozen=True, kw_only=True)
class PaymentQuery:
    window: DateWindow | None = None  # 按 paid_at 筛选
    member_id: int | None = None
    method: PaymentMethod | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class CourseInput:
    name: str
    kind: CourseKind
    duration_minutes: int  # 整数分钟，1–150；最长 2.5 小时


@dataclass(frozen=True, kw_only=True)
class CourseView:
    id: int
    name: str
    kind: CourseKind
    duration_minutes: int
    is_active: bool


@dataclass(frozen=True, kw_only=True)
class CourseQuery:
    keyword: str = ""
    kind: CourseKind | None = None
    is_active: bool | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class RoomInput:
    name: str
    capacity: int


@dataclass(frozen=True, kw_only=True)
class RoomView:
    id: int
    name: str
    capacity: int
    is_active: bool


@dataclass(frozen=True, kw_only=True)
class SessionInput:
    course_id: int
    coach_id: int
    room_id: int
    starts_at: datetime
    ends_at: datetime
    capacity: int


@dataclass(frozen=True, kw_only=True)
class SessionView:
    id: int
    course_id: int
    course_name: str
    kind: CourseKind
    coach_id: int
    coach_name: str
    room_id: int
    room_name: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    occupied_count: int
    available_count: int
    status: SessionStatus


@dataclass(frozen=True, kw_only=True)
class SessionQuery:
    window: DateWindow | None = None  # 按 starts_at 筛选
    kind: CourseKind | None = None
    coach_id: int | None = None
    room_id: int | None = None
    status: SessionStatus | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class BookingInput:
    member_id: int
    session_id: int
    membership_id: int  # 同一张卡提供预约资格及赠课；旧赠课不得搭配新卡


@dataclass(frozen=True, kw_only=True)
class BookingView:
    id: int
    member_id: int
    member_name: str
    membership_id: int
    session: SessionView
    status: BookingStatus
    booked_at: datetime
    checked_in_at: datetime | None
    closed_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class BookingQuery:
    member_id: int | None = None
    session_id: int | None = None
    window: DateWindow | None = None  # 按关联课次 starts_at 筛选
    status: BookingStatus | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class ConsumptionView:
    id: int
    booking_id: int
    membership_id: int
    lessons_used: int
    completed_at: datetime
    operator_id: int


@dataclass(frozen=True, kw_only=True)
class ReviewInput:
    booking_id: int
    rating: int
    comment: str


@dataclass(frozen=True, kw_only=True)
class ReviewView:
    id: int
    booking_id: int
    member_id: int
    session_id: int
    rating: int
    comment: str
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class EquipmentInput:
    asset_code: str
    name: str
    location: str


@dataclass(frozen=True, kw_only=True)
class EquipmentUpdateInput:
    name: str
    location: str


@dataclass(frozen=True, kw_only=True)
class EquipmentView:
    id: int
    asset_code: str
    name: str
    location: str
    status: EquipmentStatus


@dataclass(frozen=True, kw_only=True)
class EquipmentQuery:
    keyword: str = ""  # 匹配资产编号、名称、位置
    status: EquipmentStatus | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class MaintenanceView:
    id: int
    equipment_id: int
    description: str
    reported_at: datetime
    resolved_at: datetime | None
    operator_id: int
    resolved_by: int | None


@dataclass(frozen=True, kw_only=True)
class MeasurementInput:
    member_id: int
    measured_at: datetime
    height_cm: Decimal
    weight_kg: Decimal
    body_fat_pct: Decimal | None


@dataclass(frozen=True, kw_only=True)
class MeasurementView:
    id: int
    member_id: int
    coach_id: int  # 从可信操作者取得，不由表单指定
    measured_at: datetime
    height_cm: Decimal
    weight_kg: Decimal
    body_fat_pct: Decimal | None


@dataclass(frozen=True, kw_only=True)
class MeasurementQuery:
    member_id: int
    window: DateWindow | None = None  # 按 measured_at 筛选
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class MeasurementComparison:
    before: MeasurementView
    after: MeasurementView
    height_delta_cm: Decimal
    weight_delta_kg: Decimal
    body_fat_delta_pct: Decimal | None


@dataclass(frozen=True, kw_only=True)
class RevenueView:
    window: DateWindow
    payment_count: int
    total_amount: Decimal


@dataclass(frozen=True, kw_only=True)
class MembershipStats:
    as_of: datetime  # 本次快照的统计时刻，由服务生成；不支持历史状态回放
    active_members: int
    inactive_members: int
    valid_cards: int
    expired_cards: int
    future_cards: int
    void_cards: int
    exhausted_cards: int  # 已生效但入场次数为 0 的次卡


@dataclass(frozen=True, kw_only=True)
class SessionStatsView:
    session_id: int
    starts_at: datetime
    reserved_count: int
    checked_in_count: int
    completed_count: int
    no_show_count: int
    cancelled_count: int
    attendance_rate: Decimal | None


@dataclass(frozen=True, kw_only=True)
class CoachStatsView:
    coach_id: int
    coach_name: str
    completed_sessions: int
    attended_members: int


@dataclass(frozen=True, kw_only=True)
class CsvExport:
    filename: str  # 建议文件名，不含路径
    content: bytes  # 已编码的 UTF-8 BOM CSV
    row_count: int  # 不含表头在内的行数


# ================== 日志查询 ==================

@dataclass(frozen=True, kw_only=True)
class LogFrame:
    """日志堆栈帧。"""

    filename: str
    line_number: int
    function_name: str


@dataclass(frozen=True, kw_only=True)
class AttendanceChange:
    """签到状态变更记录。"""

    before: Literal["reserved", "checked_in"]
    after: Literal["reserved", "checked_in"]


@dataclass(frozen=True, kw_only=True)
class LogEntry:
    """日志条目（查询结果）。"""

    timestamp: datetime  # 时间戳（UTC）
    level: str  # "INFO" | "WARNING" | "ERROR"
    operation: str  # 操作名称
    outcome: str  # "success" | "rejected" | "failed" | "unknown"
    actor_id: int | None  # 操作人编号
    request_id: str | None  # 请求编号
    result_id: int | None  # 结果记录编号
    error_type: str | None  # 异常类型
    error_message: str | None  # 脱敏后的错误消息
    attendance_change: AttendanceChange | None = None  # 签到状态变更
    frames: tuple[LogFrame, ...] = ()  # 堆栈帧
    truncated: bool = False  # 堆栈是否被截断


@dataclass(frozen=True, kw_only=True)
class LogQuery:
    """日志查询条件。"""

    window: DateWindow | None = None  # 时间范围
    level: str | None = None  # "INFO" | "WARNING" | "ERROR"
    operation: str | None = None  # 操作名称
    actor_id: int | None = None  # 操作人编号
    request_id: str | None = None  # 请求编号
    paging: PageRequest = field(default_factory=PageRequest)
