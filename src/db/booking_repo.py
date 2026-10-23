"""预约数据访问实现，并集中处理预约与会员卡额度的原子修改。

预约和取消预约都需要在同一个事务中同时修改 `bookings` 与
`memberships.reserved_private_lessons`。额度增减放在本文件，服务负责权限、
时间和业务规则；这样不会出现“预约已取消但额度没释放”的半条数据。

锁顺序约定见各方法的说明：课次 → 会员卡（按编号升序）→ 预约。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, insert, select, update

from src.db.course_repo import load_session_views
from src.db.support import (
    from_db_utc,
    to_db_utc,
    utc_now,
    validate_paging,
    window_bounds,
)
from src.db.tables import (
    accounts,
    bookings,
    course_sessions,
    members,
    memberships,
)
from src.errors.business import InsufficientCredits, InvalidState
from src.errors.storage import StorageError
from src.models.booking import Booking
from src.models.contracts import (
    BookingInput,
    BookingQuery,
    BookingStatus,
    BookingView,
    DateWindow,
    Page,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# 未取消且仍占用课次名额/私教额度的状态。
_ACTIVE_STATUSES = ("reserved", "checked_in")


def _booking_model(row) -> Booking:
    """把一行预约记录转换成存储模型。"""
    return Booking(
        id=int(row["id"]),
        member_id=int(row["member_id"]),
        session_id=int(row["session_id"]),
        membership_id=int(row["membership_id"]),
        status=row["status"],
        booked_at=from_db_utc(row["booked_at"]),
        checked_in_at=from_db_utc(row["checked_in_at"]),
        closed_at=from_db_utc(row["closed_at"]),
        created_at=from_db_utc(row["created_at"]),
        updated_at=from_db_utc(row["updated_at"]),
    )


def lock_member(session: Session, member_id: int) -> Mapping[str, Any] | None:
    """锁定会员并读取档案状态及账号启用状态。

    返回的映射包含 members 的列和 `account_active`（未绑定账号时为 None）。
    服务用它判断会员是否可以新办业务；不存在返回 None。
    """
    row = session.execute(
        select(members, accounts.c.is_active.label("account_active"))
        .outerjoin(accounts, accounts.c.id == members.c.account_id)
        .where(members.c.id == member_id)
        .with_for_update()
    ).mappings().first()
    return row


def lock_memberships(session: Session, membership_ids: list[int]) -> dict[int, Mapping[str, Any]]:
    """按编号升序锁定多张会员卡，返回编号到行的映射。

    取消课次时可能同时释放多名会员的额度。先按升序锁卡，避免两个取消操作
    以不同顺序加锁造成死锁；调用方已经持有课次锁。
    """
    if not membership_ids:
        return {}
    ordered = sorted(set(membership_ids))
    rows = session.execute(
        select(memberships)
        .where(memberships.c.id.in_(ordered))
        .order_by(memberships.c.id)
        .with_for_update()
    ).mappings().all()
    return {int(row["id"]): row for row in rows}


def reserve_private_lesson(session: Session, membership_id: int) -> None:
    """为预约占用 1 节私教额度。

    在 SQL 的 WHERE 中再次要求“剩余减占用 > 0”，即使并发请求绕过了前面的
    检查，也不会把额度扣成负数。更新不到行时抛 InsufficientCredits。
    """
    result = session.execute(
        update(memberships)
        .where(
            memberships.c.id == membership_id,
            memberships.c.status == "active",
            memberships.c.remaining_private_lessons
            - memberships.c.reserved_private_lessons > 0,
        )
        .values(
            reserved_private_lessons=memberships.c.reserved_private_lessons + 1,
            updated_at=utc_now(),
        )
    )
    if result.rowcount == 0:
        raise InsufficientCredits("私教节数不足")


def release_private_lessons(session: Session, membership_id: int, *, count: int = 1) -> None:
    """释放预约占用的私教额度，不扣减实际剩余节数。

    消课才扣剩余节数；取消预约和缺席只释放占用。更新不到行说明占用记录
    与实际不一致，抛 InvalidState 让事务回滚。
    """
    if count <= 0:
        raise InvalidState("释放节数必须大于 0")
    result = session.execute(
        update(memberships)
        .where(
            memberships.c.id == membership_id,
            memberships.c.reserved_private_lessons >= count,
        )
        .values(
            reserved_private_lessons=memberships.c.reserved_private_lessons - count,
            updated_at=utc_now(),
        )
    )
    if result.rowcount == 0:
        raise InvalidState("预约额度占用与实际不一致，请核实")


def active_bookings_for_session(session: Session, session_id: int) -> list[Booking]:
    """读取某课次所有未取消预约，按会员编号升序，供取消课次逐个释放。"""
    rows = session.execute(
        select(bookings)
        .where(
            bookings.c.session_id == session_id,
            bookings.c.status.in_(_ACTIVE_STATUSES),
        )
        .order_by(bookings.c.member_id, bookings.c.id)
    ).mappings().all()
    return [_booking_model(row) for row in rows]


class BookingRepository:
    """预约数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get(self, booking_id: int) -> BookingView | None:
        """查询预约详情；未找到返回 None。"""
        row = self._session.execute(
            select(bookings, members.c.name.label("member_name"))
            .join(members, members.c.id == bookings.c.member_id)
            .where(bookings.c.id == booking_id)
        ).mappings().first()
        if row is None:
            return None
        session_view = load_session_views(self._session, [int(row["session_id"])]).get(
            int(row["session_id"])
        )
        if session_view is None:
            raise StorageError("预约关联的课次不存在，请联系管理员核查")
        return BookingView(
            id=int(row["id"]),
            member_id=int(row["member_id"]),
            member_name=row["member_name"],
            membership_id=int(row["membership_id"]),
            session=session_view,
            status=row["status"],
            booked_at=from_db_utc(row["booked_at"]),
            checked_in_at=from_db_utc(row["checked_in_at"]),
            closed_at=from_db_utc(row["closed_at"]),
        )

    def list(
        self,
        query: BookingQuery,
        *,
        scope_member_id: int | None,
        scope_coach_id: int | None,
    ) -> Page[BookingView]:
        """按服务明确给出的会员或教练范围分页查询。

        `scope_member_id` 用于会员只能看自己的预约；`scope_coach_id` 用于教练
        只能看自己课次的学员名单。两者由服务根据身份计算，仓储不猜测权限。
        """
        page, page_size = validate_paging(query.paging)
        conditions = []
        if query.member_id is not None:
            conditions.append(bookings.c.member_id == query.member_id)
        if query.session_id is not None:
            conditions.append(bookings.c.session_id == query.session_id)
        if query.status is not None:
            conditions.append(bookings.c.status == query.status)
        if query.window is not None:
            start, end = window_bounds(query.window)
            conditions.append(course_sessions.c.starts_at >= start)
            conditions.append(course_sessions.c.starts_at < end)
        if scope_member_id is not None:
            conditions.append(bookings.c.member_id == scope_member_id)
        if scope_coach_id is not None:
            conditions.append(course_sessions.c.coach_id == scope_coach_id)

        total = int(self._session.scalar(
            select(func.count())
            .select_from(bookings)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(*conditions)
        ) or 0)
        rows = self._session.execute(
            select(bookings, members.c.name.label("member_name"))
            .join(members, members.c.id == bookings.c.member_id)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(*conditions)
            .order_by(course_sessions.c.starts_at.desc(), bookings.c.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).mappings().all()

        session_ids = [int(row["session_id"]) for row in rows]
        session_views = load_session_views(self._session, session_ids)
        items: list[BookingView] = []
        for row in rows:
            session_view = session_views.get(int(row["session_id"]))
            if session_view is None:
                raise StorageError("预约关联的课次不存在，请联系管理员核查")
            items.append(BookingView(
                id=int(row["id"]),
                member_id=int(row["member_id"]),
                member_name=row["member_name"],
                membership_id=int(row["membership_id"]),
                session=session_view,
                status=row["status"],
                booked_at=from_db_utc(row["booked_at"]),
                checked_in_at=from_db_utc(row["checked_in_at"]),
                closed_at=from_db_utc(row["closed_at"]),
            ))
        return Page(items=items, total=total, page=page, page_size=page_size)

    def find_for_member_session(self, member_id: int, session_id: int) -> Booking | None:
        """读取同会员同课次的预约，包含已取消状态。

        唯一约束保证最多一条；返回已取消记录是业务需要：同一会员不能靠取消
        再预约同一课次来绕过“已有预约”检查。
        """
        row = self._session.execute(
            select(bookings)
            .where(
                bookings.c.member_id == member_id,
                bookings.c.session_id == session_id,
            )
            .order_by(bookings.c.id.desc())
        ).mappings().first()
        return _booking_model(row) if row is not None else None

    def create(self, data: BookingInput, booked_at: datetime) -> BookingView:
        """保存预约，不在此处检查权益或提交事务。"""
        now = utc_now()
        result = self._session.execute(
            insert(bookings).values(
                member_id=data.member_id,
                session_id=data.session_id,
                membership_id=data.membership_id,
                status="reserved",
                booked_at=to_db_utc(booked_at),
                checked_in_at=None,
                closed_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        booking_id = int(result.inserted_primary_key[0])
        view = self.get(booking_id)
        if view is None:
            raise StorageError("预约保存后无法读取")
        return view

    def restore(self, booking_id: int, *, membership_id: int, booked_at: datetime) -> BookingView:
        """恢复已取消预约并清空旧签到和结束时间。

        当前预约流程要求同一会员同一课次只保留一条记录；如果以后开放“取消后
        重新预约”，应调用本方法而不是再插一条，避免唯一约束冲突。
        """
        self._session.execute(
            update(bookings)
            .where(bookings.c.id == booking_id)
            .values(
                membership_id=membership_id,
                status="reserved",
                booked_at=to_db_utc(booked_at),
                checked_in_at=None,
                closed_at=None,
                updated_at=utc_now(),
            )
        )
        view = self.get(booking_id)
        if view is None:
            raise StorageError("预约不存在")
        return view

    def set_state(
        self,
        booking_id: int,
        *,
        status: BookingStatus,
        checked_in_at: datetime | None,
        closed_at: datetime | None,
    ) -> BookingView:
        """写入状态和时间，私教节数结算由服务协调。"""
        self._session.execute(
            update(bookings)
            .where(bookings.c.id == booking_id)
            .values(
                status=status,
                checked_in_at=(
                    to_db_utc(checked_in_at) if checked_in_at is not None else None
                ),
                closed_at=to_db_utc(closed_at) if closed_at is not None else None,
                updated_at=utc_now(),
            )
        )
        view = self.get(booking_id)
        if view is None:
            raise StorageError("预约不存在")
        return view

    def count_occupied(self, session_id: int) -> int:
        """统计该课次未取消预约数。"""
        count = self._session.scalar(
            select(func.count())
            .select_from(bookings)
            .where(
                bookings.c.session_id == session_id,
                bookings.c.status.in_(_ACTIVE_STATUSES),
            )
        )
        return int(count or 0)

    def has_member_conflict(self, member_id: int, window: DateWindow) -> bool:
        """检查会员未取消预约是否与目标时间重叠。

        同时排除已取消的课次，避免取消课次后残留数据继续阻挡新预约。
        """
        start, end = window_bounds(window)
        count = self._session.scalar(
            select(func.count())
            .select_from(bookings)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(
                bookings.c.member_id == member_id,
                bookings.c.status.in_(_ACTIVE_STATUSES),
                course_sessions.c.status != "cancelled",
                course_sessions.c.starts_at < end,
                course_sessions.c.ends_at > start,
            )
        )
        return bool(count)

    def has_current_coaching_booking(
        self, member_id: int, coach_id: int, *, at: datetime,
    ) -> bool:
        """检查体测录入所需的当前授课关系；at 由服务生成。

        要求预约 reserved/checked_in、课次 scheduled，且 booked_at <= at < ends_at。
        历史体测查看不用此条件，按设计第 3.6 节保留截止。
        """
        at_db = to_db_utc(at)
        count = self._session.scalar(
            select(func.count())
            .select_from(bookings)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(
                bookings.c.member_id == member_id,
                course_sessions.c.coach_id == coach_id,
                bookings.c.status.in_(_ACTIVE_STATUSES),
                course_sessions.c.status == "scheduled",
                bookings.c.booked_at <= at_db,
                course_sessions.c.ends_at > at_db,
            )
        )
        return bool(count)

    def lock(self, booking_id: int) -> Booking | None:
        """锁定并读取最新预约记录；不存在返回 None。"""
        row = self._session.execute(
            select(bookings).where(bookings.c.id == booking_id).with_for_update()
        ).mappings().first()
        return _booking_model(row) if row is not None else None
