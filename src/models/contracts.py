"""接口共用的数据格式，依据 docs/architecture.md“公共类型定义”。

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
CourseKind = Literal["private"]
MemberStatus = Literal["active", "archived"]
GymCardStatus = Literal["active", "void"]
LessonPackageStatus = Literal["active", "void"]
SessionStatus = Literal["scheduled", "completed", "cancelled"]
BookingStatus = Literal["reserved", "checked_in", "completed", "cancelled", "no_show"]
PaymentMethod = Literal["cash", "card", "transfer"]
GymCardStartPolicy = Literal["immediate", "append"]
GiftActivationPolicy = Literal["immediate", "append"]
GymCardKind = Literal["duration", "visit"]
EntrySourceKind = Literal["duration_gym_card", "visit_gym_card", "booking"]
EquipmentStatus = Literal["available", "maintenance", "retired"]
EntitlementOriginKind = Literal["purchase", "gift"]
SaleKind = Literal["gym_card", "lesson_package"]
SaleItemKind = Literal["gym_card", "lesson_package"]
OperationResultKind = Literal["member", "sale_order", "course_session", "booking", "gym_entry"]
OperationName = Literal[
    "create_member",
    "sell_gym_card",
    "sell_lesson_package",
    "create_session",
    "cancel_session",
    "book",
    "cancel_booking",
    "register_entry",
]
ErrorAction = Literal["continue", "login", "exit", "verify"]


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
    member_id: int | None  # member 角色必须有值，其他角色必须为 None
    coach_id: int | None  # coach 角色必须有值，其他角色必须为 None


@dataclass(frozen=True, kw_only=True)
class AccountInput:
    username: str  # 去首尾空白并转小写后，只允许 3–50 位 ASCII 字母、数字和下划线
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
class MemberInput:
    name: str
    phone: str | None


@dataclass(frozen=True, kw_only=True)
class MemberView:
    id: int
    name: str
    phone: str | None
    status: MemberStatus
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class MemberQuery:
    member_id: int | None = None
    keyword: str = ""
    status: MemberStatus | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class MemberAccountLinkInput:
    account_id: int
    member_id: int


@dataclass(frozen=True, kw_only=True)
class CoachAccountLinkInput:
    account_id: int
    coach_id: int


@dataclass(frozen=True, kw_only=True)
class MemberAccountLinkView:
    account_id: int
    member_id: int
    linked_at: datetime
    linked_by: int


@dataclass(frozen=True, kw_only=True)
class CoachInput:
    name: str
    phone: str | None


@dataclass(frozen=True, kw_only=True)
class CoachView:
    id: int
    name: str
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class DurationGymCardProductTerms:
    kind: Literal["duration"]
    name: str
    price: Decimal
    valid_days: int
    start_policy: GymCardStartPolicy


@dataclass(frozen=True, kw_only=True)
class VisitGymCardProductTerms:
    kind: Literal["visit"]
    name: str
    price: Decimal
    total_entries: int


GymCardProductTerms = DurationGymCardProductTerms | VisitGymCardProductTerms


@dataclass(frozen=True, kw_only=True)
class DurationGymCardProductView:
    kind: Literal["duration"]
    id: int
    terms: DurationGymCardProductTerms
    is_sale_enabled: bool
    is_gift_enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class VisitGymCardProductView:
    kind: Literal["visit"]
    id: int
    terms: VisitGymCardProductTerms
    is_sale_enabled: bool
    created_at: datetime
    updated_at: datetime


GymCardProductView = DurationGymCardProductView | VisitGymCardProductView


@dataclass(frozen=True, kw_only=True)
class LessonPackageProductTerms:
    name: str
    price: Decimal
    lesson_credits: int
    valid_days: int | None


@dataclass(frozen=True, kw_only=True)
class LessonPackageProductView:
    id: int
    terms: LessonPackageProductTerms
    is_sale_enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class LessonPackageGiftRuleInput:
    trigger_product_id: int
    reward_gym_card_product_id: int
    reward_quantity: int
    activation_policy: GiftActivationPolicy


@dataclass(frozen=True, kw_only=True)
class GiftRuleRevisionInput:
    reward_gym_card_product_id: int
    reward_quantity: int
    activation_policy: GiftActivationPolicy


@dataclass(frozen=True, kw_only=True)
class LessonPackageGiftRuleView:
    id: int
    trigger_product_id: int
    reward_gym_card_product_id: int
    reward_quantity: int
    activation_policy: GiftActivationPolicy
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class LessonPackageGiftRuleQuery:
    trigger_product_id: int | None = None
    reward_gym_card_product_id: int | None = None
    is_active: bool | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class PurchasedGymCardOriginView:
    sale_order_id: int
    sale_item_id: int


@dataclass(frozen=True, kw_only=True)
class GiftedGymCardOriginView:
    gift_grant_id: int
    trigger_sale_order_id: int
    trigger_sale_item_id: int
    gift_rule_id: int


GymCardOriginView = PurchasedGymCardOriginView | GiftedGymCardOriginView


@dataclass(frozen=True, kw_only=True)
class DurationGymCardView:
    kind: Literal["duration"]
    id: int
    member_id: int
    product_id: int
    name: str
    valid_days: int
    start_policy: GymCardStartPolicy
    valid_from: date
    valid_until: date
    status: GymCardStatus
    origin: GymCardOriginView
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class VisitGymCardView:
    kind: Literal["visit"]
    id: int
    member_id: int
    product_id: int
    name: str
    total_entries: int
    remaining_entries: int
    status: GymCardStatus
    origin: PurchasedGymCardOriginView
    created_at: datetime
    updated_at: datetime


GymCardView = DurationGymCardView | VisitGymCardView


@dataclass(frozen=True, kw_only=True)
class GymCardQuery:
    member_id: int | None = None
    kind: GymCardKind | None = None
    status: GymCardStatus | None = None
    origin_kind: EntitlementOriginKind | None = None
    valid_on: date | None = None
    expires_before: date | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class GymMembershipView:
    member_id: int
    business_date: date
    is_member: bool
    eligible_card_ids: tuple[int, ...]


@dataclass(frozen=True, kw_only=True)
class PurchasedDurationGymCardCreate:
    member_id: int
    product_id: int
    purchase_sale_item_id: int
    name: str
    valid_days: int
    start_policy: GymCardStartPolicy
    valid_from: date
    valid_until: date
    status: GymCardStatus


@dataclass(frozen=True, kw_only=True)
class PurchasedVisitGymCardCreate:
    member_id: int
    product_id: int
    purchase_sale_item_id: int
    name: str
    total_entries: int
    remaining_entries: int
    status: GymCardStatus


@dataclass(frozen=True, kw_only=True)
class GiftedDurationGymCardCreate:
    member_id: int
    product_id: int
    gift_grant_id: int
    name: str
    valid_days: int
    start_policy: GymCardStartPolicy
    valid_from: date
    valid_until: date
    status: GymCardStatus


@dataclass(frozen=True, kw_only=True)
class LessonPackageCreate:
    member_id: int
    product_id: int
    purchase_sale_item_id: int
    name: str
    total_lessons: int
    remaining_lessons: int
    reserved_lessons: int
    valid_from: date
    valid_until: date | None
    status: LessonPackageStatus


@dataclass(frozen=True, kw_only=True)
class GymCardSaleItemProductSnapshot:
    product_name: str


@dataclass(frozen=True, kw_only=True)
class LessonPackageSaleItemProductSnapshot:
    product_name: str


@dataclass(frozen=True, kw_only=True)
class GiftRuleSnapshot:
    gift_rule_id: int
    reward_gym_card_product_id: int
    version: int
    activation_policy: GiftActivationPolicy


@dataclass(frozen=True, kw_only=True)
class RewardGymCardProductSnapshot:
    product_name: str
    valid_days: int


@dataclass(frozen=True, kw_only=True)
class LessonPackageView:
    id: int
    member_id: int
    product_id: int
    sale_order_id: int
    sale_item_id: int
    name: str
    total_lessons: int
    remaining_lessons: int
    reserved_lessons: int
    valid_from: date
    valid_until: date | None
    status: LessonPackageStatus
    created_at: datetime
    updated_at: datetime

    @property
    def available_lessons(self) -> int:
        return self.remaining_lessons - self.reserved_lessons


@dataclass(frozen=True, kw_only=True)
class LessonPackageQuery:
    member_id: int | None = None
    status: LessonPackageStatus | None = None
    valid_on: date | None = None
    expires_before: date | None = None
    available_lessons_at_most: int | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class GymCardSaleInput:
    member_id: int
    gym_card_product_id: int
    method: PaymentMethod


@dataclass(frozen=True, kw_only=True)
class LessonPackageSaleInput:
    member_id: int
    lesson_package_product_id: int
    method: PaymentMethod


@dataclass(frozen=True, kw_only=True)
class SaleOrderView:
    id: int
    member_id: int
    kind: SaleKind
    total_amount: Decimal
    sold_at: datetime
    operator_id: int


@dataclass(frozen=True, kw_only=True)
class SaleOrderQuery:
    member_id: int | None = None
    kind: SaleKind | None = None
    operator_id: int | None = None
    window: DateWindow | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class SaleItemView:
    id: int
    sale_order_id: int
    kind: SaleItemKind
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    line_amount: Decimal


@dataclass(frozen=True, kw_only=True)
class PaymentView:
    id: int
    sale_order_id: int
    member_id: int
    amount: Decimal
    method: PaymentMethod
    paid_at: datetime
    operator_id: int


@dataclass(frozen=True, kw_only=True)
class GiftGrantView:
    id: int
    member_id: int
    trigger_sale_order_id: int
    trigger_sale_item_id: int
    gift_rule_id: int
    sequence: int
    gym_card_id: int
    granted_at: datetime


@dataclass(frozen=True, kw_only=True)
class SaleOrderDetailView:
    order: SaleOrderView
    items: tuple[SaleItemView, ...]
    payment: PaymentView
    gym_cards: tuple[GymCardView, ...]
    lesson_packages: tuple[LessonPackageView, ...]
    gift_grants: tuple[GiftGrantView, ...]


@dataclass(frozen=True, kw_only=True)
class GymCardSaleResultView:
    order: SaleOrderView
    item: SaleItemView
    payment: PaymentView
    card: GymCardView


@dataclass(frozen=True, kw_only=True)
class LessonPackageSaleResultView:
    order: SaleOrderView
    item: SaleItemView
    payment: PaymentView
    package: LessonPackageView
    gift_grants: tuple[GiftGrantView, ...]
    gifted_cards: tuple[GymCardView, ...]


@dataclass(frozen=True, kw_only=True)
class LegacyOperationResultView:
    request_id: str
    legacy_operation: str
    target_operation: OperationName
    result_kind: OperationResultKind
    result_id: int
    legacy_payload_hash: str
    migrated_at: datetime


@dataclass(frozen=True, kw_only=True)
class DurationGymCardEntrySourceInput:
    kind: Literal["duration_gym_card"]
    gym_card_id: int


@dataclass(frozen=True, kw_only=True)
class VisitGymCardEntrySourceInput:
    kind: Literal["visit_gym_card"]
    gym_card_id: int


@dataclass(frozen=True, kw_only=True)
class BookingEntrySourceInput:
    kind: Literal["booking"]
    booking_id: int


EntrySourceInput = (
    DurationGymCardEntrySourceInput
    | VisitGymCardEntrySourceInput
    | BookingEntrySourceInput
)


@dataclass(frozen=True, kw_only=True)
class EntryInput:
    member_id: int
    source: EntrySourceInput


@dataclass(frozen=True, kw_only=True)
class DurationGymCardEntryAuthorization:
    kind: Literal["duration_gym_card"]
    entry_id: int
    member_id: int
    business_date: date
    gym_card_id: int
    authorized_at: datetime


@dataclass(frozen=True, kw_only=True)
class VisitGymCardEntryAuthorization:
    kind: Literal["visit_gym_card"]
    entry_id: int
    member_id: int
    business_date: date
    gym_card_id: int
    remaining_entries: int
    authorized_at: datetime


@dataclass(frozen=True, kw_only=True)
class BookingEntryAuthorization:
    kind: Literal["booking"]
    entry_id: int
    member_id: int
    business_date: date
    booking_id: int
    authorized_at: datetime


EntryAuthorization = (
    DurationGymCardEntryAuthorization
    | VisitGymCardEntryAuthorization
    | BookingEntryAuthorization
)


@dataclass(frozen=True, kw_only=True)
class EntryView:
    id: int
    member_id: int
    authorization: EntryAuthorization
    business_date: date
    entered_at: datetime
    operator_id: int


@dataclass(frozen=True, kw_only=True)
class PaymentQuery:
    window: DateWindow | None = None  # 按 paid_at 筛选
    member_id: int | None = None
    method: PaymentMethod | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class CourseInput:
    name: str
    description: str | None
    kind: CourseKind
    duration_minutes: int


@dataclass(frozen=True, kw_only=True)
class CourseView:
    id: int
    name: str
    description: str | None
    kind: CourseKind
    duration_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class RoomInput:
    name: str
    location: str | None


@dataclass(frozen=True, kw_only=True)
class RoomView:
    id: int
    name: str
    location: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class SessionInput:
    course_id: int
    coach_id: int
    room_id: int
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True, kw_only=True)
class SessionView:
    id: int
    course: CourseView
    coach: CoachView
    room: RoomView
    course_name: str
    kind: CourseKind
    duration_minutes: int
    starts_at: datetime
    ends_at: datetime
    capacity: int
    occupied_count: int
    available_count: int
    status: SessionStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class SessionQuery:
    kind: CourseKind | None = None
    coach_id: int | None = None
    room_id: int | None = None
    window: DateWindow | None = None
    status: SessionStatus | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class BookingInput:
    member_id: int
    session_id: int
    lesson_package_id: int


@dataclass(frozen=True, kw_only=True)
class BookingView:
    id: int
    member_id: int
    member_name: str
    lesson_package_id: int
    session: SessionView
    status: BookingStatus
    booked_at: datetime
    checked_in_at: datetime | None
    closed_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class BookingQuery:
    member_id: int | None = None
    session_id: int | None = None
    lesson_package_id: int | None = None
    window: DateWindow | None = None
    status: BookingStatus | None = None
    paging: PageRequest = field(default_factory=PageRequest)


@dataclass(frozen=True, kw_only=True)
class ConsumptionView:
    id: int
    booking_id: int
    lesson_package_id: int
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
    coach_id: int
    rating: int
    comment: str
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class ReviewQuery:
    member_id: int | None = None
    coach_id: int | None = None
    paging: PageRequest = field(default_factory=PageRequest)


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
    created_at: datetime
    updated_at: datetime


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
    coach_id: int
    measured_at: datetime
    created_at: datetime
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
class MembershipStats:
    as_of: datetime
    business_date: date
    active_member_profiles: int
    archived_member_profiles: int
    valid_duration_gym_card_count: int
    usable_visit_gym_card_count: int
    members_with_gym_access: int
    future_duration_gym_cards: int
    expired_duration_gym_cards: int
    exhausted_visit_gym_cards: int
    void_gym_cards: int
    remaining_visit_entries: int
    active_lesson_package_count: int
    future_lesson_packages: int
    expired_lesson_packages: int
    void_lesson_packages: int
    exhausted_lesson_packages: int
    remaining_lessons: int
    available_lessons: int
    reserved_lessons: int


# 兼容层：v2 formatters 使用的 SaleView 别名指向 v3 的 SaleOrderView
SaleView = SaleOrderView


@dataclass(frozen=True, kw_only=True)
class RevenueBreakdownView:
    sale_kind: SaleKind
    payment_count: int
    total_amount: Decimal


@dataclass(frozen=True, kw_only=True)
class RevenueView:
    window: DateWindow
    total_payment_count: int
    total_amount: Decimal
    breakdowns: tuple[RevenueBreakdownView, ...]


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
    truncated: bool = False  # 整条日志是否因 16 KiB 上限被截断


@dataclass(frozen=True, kw_only=True)
class LogSnapshot:
    """一次日志浏览使用的固定快照。"""

    captured_at: datetime
    entries: tuple[LogEntry, ...]
    skipped_lines: int


@dataclass(frozen=True, kw_only=True)
class LogQuery:
    """日志查询条件。"""

    window: DateWindow | None = None  # 时间范围
    level: str | None = None  # "INFO" | "WARNING" | "ERROR"
    operation: str | None = None  # 操作名称
    actor_id: int | None = None  # 操作人编号
    request_id: str | None = None  # 请求编号
    paging: PageRequest = field(default_factory=PageRequest)

