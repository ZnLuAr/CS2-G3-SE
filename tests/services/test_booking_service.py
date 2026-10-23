"""预约业务测试：权限、卡资格、额度占用、撞期、满员、取消与防重复。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import OperationalError

from src.db.tables import (
    accounts,
    bookings,
    coaches,
    course_sessions,
    members,
    memberships,
    operation_records,
    rooms,
)
from src.errors.business import (
    CapacityExceeded,
    CardNotEligible,
    ConflictError,
    InsufficientCredits,
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
    ScheduleConflict,
)
from src.errors.storage import OutcomeUnknownError
from src.models.contracts import (
    Actor,
    BookingInput,
    BookingQuery,
    DateWindow,
    PageRequest,
    SessionInput,
)
from src.services.booking_service import BookingService
from src.services.course_service import CourseService
from tests.conftest import ADMIN, COACH, MEMBER, RECEPTION, FakeAuth

UTC = timezone.utc
NOW_IN_TEST = datetime(2026, 10, 1, tzinfo=UTC)
SESSION_START = datetime(2026, 12, 1, 6, 0, tzinfo=UTC)


def _add_member(session_factory, member_id: int, name: str) -> None:
    """补充一名未绑定账号的会员。"""
    with session_factory() as session:
        with session.begin():
            session.execute(insert(members).values(
                id=member_id, account_id=None, name=name, phone=None,
                is_active=True, created_at=NOW_IN_TEST, updated_at=NOW_IN_TEST,
            ))


def _add_card(
    session_factory,
    *,
    card_id: int,
    member_id: int,
    kind: str = "monthly",
    valid_from: date = date(2026, 1, 1),
    valid_until: date | None = date(2027, 1, 1),
    remaining: int = 20,
    reserved: int = 0,
    status: str = "active",
) -> None:
    """插入一张会员卡；次卡按无期限、10 次入场、0 赠课构造。"""
    with session_factory() as session:
        with session.begin():
            session.execute(insert(memberships).values(
                id=card_id,
                member_id=member_id,
                product_id=1,
                name="次卡" if kind == "count" else "月卡",
                kind=kind,
                price=Decimal("199.00"),
                private_lesson_credits=0 if kind == "count" else remaining,
                access_uses=10 if kind == "count" else None,
                valid_days=None if kind == "count" else 30,
                valid_from=valid_from,
                valid_until=None if kind == "count" else valid_until,
                remaining_accesses=10 if kind == "count" else None,
                remaining_private_lessons=0 if kind == "count" else remaining,
                reserved_private_lessons=reserved,
                status=status,
                created_at=NOW_IN_TEST,
                updated_at=NOW_IN_TEST,
            ))


def _add_coach_and_room(session_factory, *, coach_id: int, account_id: int, room_id: int) -> None:
    """补充教练账号、教练档案和场地，用于构造不撞期的第二节课。"""
    with session_factory() as session:
        with session.begin():
            session.execute(insert(accounts).values(
                id=account_id, username=f"coach{coach_id}", password_hash="x",
                role="coach", is_active=True,
                created_at=NOW_IN_TEST, updated_at=NOW_IN_TEST,
            ))
            session.execute(insert(coaches).values(
                id=coach_id, account_id=account_id, name=f"教练{coach_id}",
                specialty="", is_active=True,
                created_at=NOW_IN_TEST, updated_at=NOW_IN_TEST,
            ))
            session.execute(insert(rooms).values(
                id=room_id, name=f"教室{room_id}", capacity=1, is_active=True,
                created_at=NOW_IN_TEST, updated_at=NOW_IN_TEST,
            ))


def _credits(session_factory, card_id: int) -> tuple[int, int]:
    """读取一张卡的 (剩余节数, 已占用节数)。"""
    with session_factory() as session:
        row = session.execute(
            select(
                memberships.c.remaining_private_lessons,
                memberships.c.reserved_private_lessons,
            ).where(memberships.c.id == card_id)
        ).one()
        return int(row[0]), int(row[1])


def _booking_count(session_factory, member_id: int | None = None) -> int:
    """统计预约数量，可限定会员。"""
    with session_factory() as session:
        statement = select(func.count()).select_from(bookings)
        if member_id is not None:
            statement = statement.where(bookings.c.member_id == member_id)
        return int(session.scalar(statement) or 0)


@pytest.fixture()
def service(session_factory) -> BookingService:
    """使用上海时区和假身份校验构造预约服务。"""
    return BookingService(session_factory, FakeAuth(), timezone_name="Asia/Shanghai")


@pytest.fixture()
def course_service(session_factory) -> CourseService:
    """构造课程服务，用于在测试中排课。"""
    return CourseService(session_factory, FakeAuth())


def _new_session(
    course_service: CourseService,
    request_id: str,
    *,
    coach_id: int = 1,
    room_id: int = 1,
    start: datetime = SESSION_START,
) -> int:
    """通过课程服务排一节 60 分钟私教课，返回课次编号。"""
    from datetime import timedelta

    view = course_service.create_session(
        ADMIN,
        SessionInput(
            course_id=1,
            coach_id=coach_id,
            room_id=room_id,
            starts_at=start,
            ends_at=start + timedelta(minutes=60),
            capacity=1,
        ),
        request_id,
    )
    return view.id


def test_member_books_own_session_and_reserves_credit(session_factory, seed, service) -> None:
    """会员预约成功：写预约、占用 1 节，会员/教练/前台都可按权限查询。"""
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-book-1",
    )
    assert created.member_id == 1
    assert created.member_name == "张三"
    assert created.session.id == 1
    assert created.status == "reserved"
    assert created.booked_at is not None
    assert created.checked_in_at is None
    assert created.closed_at is None
    assert _credits(session_factory, 1) == (20, 1)

    assert service.get_booking(MEMBER, created.id).id == created.id
    assert service.get_booking(COACH, created.id).id == created.id
    assert service.get_booking(RECEPTION, created.id).id == created.id

    page = service.list_bookings(MEMBER, BookingQuery())
    assert page.total == 1
    assert page.items[0].id == created.id
    assert service.list_bookings(COACH, BookingQuery()).total == 1


def test_staff_can_book_for_member_and_member_cannot_verify_staff_request(
    session_factory, seed, service,
) -> None:
    """前台可代会员预约；按请求编号核实只允许原操作者。"""
    created = service.book(
        RECEPTION, BookingInput(member_id=1, session_id=1, membership_id=1), "req-staff",
    )
    assert created.member_id == 1
    assert service.get_booking_by_request(RECEPTION, "req-staff").id == created.id
    with pytest.raises(NotFoundError):
        service.get_booking_by_request(MEMBER, "req-staff")


def test_booking_permissions_and_visibility(session_factory, seed, service) -> None:
    """会员不能替别人约、教练不能预约；越权查看按不存在处理。"""
    _add_member(session_factory, 2, "李四")
    _add_card(session_factory, card_id=2, member_id=2)
    other_member = Actor(account_id=20, role="member", member_id=2, coach_id=None)

    with pytest.raises(PermissionDenied):
        service.book(MEMBER, BookingInput(member_id=2, session_id=1, membership_id=2), "req-other")
    with pytest.raises(PermissionDenied):
        service.book(COACH, BookingInput(member_id=1, session_id=1, membership_id=1), "req-coach")

    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-own",
    )
    with pytest.raises(NotFoundError):
        service.get_booking(other_member, created.id)
    assert service.list_bookings(other_member, BookingQuery()).total == 0
    with pytest.raises(PermissionDenied):
        service.list_bookings(other_member, BookingQuery(member_id=1))


def test_duplicate_and_request_idempotency(session_factory, seed, service) -> None:
    """同一请求编号返回原预约；不同编号重复预约被拒绝，额度只占一次。"""
    _add_card(session_factory, card_id=2, member_id=1)
    first = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-idem",
    )
    second = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-idem",
    )
    assert second.id == first.id
    assert _booking_count(session_factory) == 1
    assert _credits(session_factory, 1) == (20, 1)

    with pytest.raises(ConflictError):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-idem-2",
        )
    with pytest.raises(ConflictError):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=1, membership_id=2), "req-idem",
        )


def test_capacity_exceeded_leaves_other_member_untouched(session_factory, seed, service) -> None:
    """课次容量为 1，第二位会员预约得到满员提示，额度不占用。"""
    _add_member(session_factory, 2, "李四")
    _add_card(session_factory, card_id=2, member_id=2)
    service.book(MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-first")
    with pytest.raises(CapacityExceeded):
        service.book(
            RECEPTION, BookingInput(member_id=2, session_id=1, membership_id=2), "req-full",
        )
    assert _booking_count(session_factory) == 1
    assert _credits(session_factory, 2) == (20, 0)


def test_member_time_conflict(session_factory, seed, service, course_service) -> None:
    """同一会员在重叠时段已有预约时，第二节课被拒绝。"""
    _add_coach_and_room(session_factory, coach_id=2, account_id=20, room_id=2)
    from datetime import timedelta

    overlapping = _new_session(
        course_service,
        "req-overlap",
        coach_id=2,
        room_id=2,
        start=SESSION_START + timedelta(minutes=30),
    )
    service.book(MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-base")
    with pytest.raises(ScheduleConflict):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=overlapping, membership_id=1),
            "req-overlap-book",
        )
    assert _booking_count(session_factory) == 1
    assert _credits(session_factory, 1) == (20, 1)


def test_card_eligibility_rules(session_factory, seed, service) -> None:
    """次卡、过期卡、他人卡、作废卡被拒绝；未来生效卡可约有效期内的课。"""
    _add_member(session_factory, 2, "李四")
    _add_card(session_factory, card_id=2, member_id=2)
    _add_card(session_factory, card_id=3, member_id=1, kind="count")
    _add_card(
        session_factory, card_id=4, member_id=1,
        valid_until=date(2026, 11, 30),
    )
    _add_card(session_factory, card_id=5, member_id=1, status="void")
    _add_card(
        session_factory, card_id=6, member_id=1,
        valid_from=date(2026, 12, 1), valid_until=date(2027, 1, 1),
    )

    for card_id, reason in [
        (2, "他人卡"),
        (3, "次卡"),
        (4, "过期卡"),
        (5, "作废卡"),
    ]:
        with pytest.raises(CardNotEligible):
            service.book(
                MEMBER,
                BookingInput(member_id=1, session_id=1, membership_id=card_id),
                f"req-card-{card_id}",
            )

    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=6), "req-future-card",
    )
    assert created.membership_id == 6
    assert _credits(session_factory, 6) == (20, 1)


def test_card_date_uses_store_timezone(session_factory, seed, service, course_service) -> None:
    """上海时间 00:30 的课归属当天，按门店日期判断卡有效期。"""
    _add_card(
        session_factory, card_id=2, member_id=1,
        valid_from=date(2026, 12, 1), valid_until=date(2026, 12, 2),
    )
    # 2026-11-30 16:30 UTC = 2026-12-01 00:30 上海时间。
    session_id = _new_session(
        course_service,
        "req-midnight",
        start=datetime(2026, 11, 30, 16, 30, tzinfo=UTC),
    )
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=session_id, membership_id=2),
        "req-midnight-book",
    )
    assert created.session.id == session_id


def test_insufficient_credits(session_factory, seed, service, course_service) -> None:
    """剩余减占用为 0 时拒绝；成功占用后第二节课额度不足。"""
    with session_factory() as session:
        with session.begin():
            session.execute(
                update(memberships)
                .where(memberships.c.id == 1)
                .values(remaining_private_lessons=1, reserved_private_lessons=0)
            )
    service.book(MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-credit-1")
    assert _credits(session_factory, 1) == (1, 1)

    from datetime import timedelta
    second = _new_session(
        course_service, "req-credit-session", start=SESSION_START + timedelta(hours=2),
    )
    with pytest.raises(InsufficientCredits):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=second, membership_id=1),
            "req-credit-2",
        )
    assert _booking_count(session_factory) == 1
    assert _credits(session_factory, 1) == (1, 1)


def test_cancel_releases_credit_and_is_idempotent(session_factory, seed, service) -> None:
    """开课前取消释放占用；同一请求编号重试返回原结果，不同请求再次取消被拒绝。"""
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-book-cancel",
    )
    _add_member(session_factory, 2, "李四")
    other_member = Actor(account_id=20, role="member", member_id=2, coach_id=None)
    with pytest.raises(PermissionDenied):
        service.cancel(other_member, created.id, "req-other-cancel")
    with pytest.raises(PermissionDenied):
        service.cancel(COACH, created.id, "req-coach-cancel")

    cancelled = service.cancel(MEMBER, created.id, "req-cancel")
    assert cancelled.status == "cancelled"
    assert cancelled.closed_at is not None
    assert _credits(session_factory, 1) == (20, 0)
    assert service.cancel(MEMBER, created.id, "req-cancel").status == "cancelled"

    with pytest.raises(InvalidState):
        service.cancel(MEMBER, created.id, "req-cancel-again")


def test_cancel_rejects_started_or_checked_in_booking(session_factory, seed, service) -> None:
    """已签到或已开课的预约不能取消，额度不释放。"""
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-start-cancel",
    )
    with session_factory() as session:
        with session.begin():
            session.execute(
                update(bookings)
                .where(bookings.c.id == created.id)
                .values(status="checked_in", checked_in_at=NOW_IN_TEST)
            )
    with pytest.raises(InvalidState):
        service.cancel(MEMBER, created.id, "req-checked-cancel")
    assert _credits(session_factory, 1) == (20, 1)

    with session_factory() as session:
        with session.begin():
            session.execute(
                update(bookings)
                .where(bookings.c.id == created.id)
                .values(status="reserved", checked_in_at=None)
            )
            session.execute(
                update(course_sessions)
                .where(course_sessions.c.id == 1)
                .values(starts_at=datetime(2026, 10, 1, 1, 0),
                       ends_at=datetime(2026, 10, 1, 2, 0))
            )
    with pytest.raises(InvalidState):
        service.cancel(MEMBER, created.id, "req-started-cancel")
    assert _credits(session_factory, 1) == (20, 1)


def test_get_booking_by_request_checks_operation_and_owner(session_factory, seed, service) -> None:
    """按请求编号核实预约；操作类型不符或非原操作者被拒绝。"""
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-verify",
    )
    assert service.get_booking_by_request(MEMBER, "req-verify").id == created.id
    with pytest.raises(NotFoundError):
        service.get_booking_by_request(MEMBER, "req-unknown")
    with pytest.raises(NotFoundError):
        service.get_booking_by_request(ADMIN, "req-verify")

    with session_factory() as session:
        with session.begin():
            session.execute(insert(operation_records).values(
                request_id="req-wrong-op", actor_id=3, operation="create_session",
                payload_hash="x" * 64, result_id=created.id, created_at=NOW_IN_TEST,
            ))
    with pytest.raises(ConflictError):
        service.get_booking_by_request(MEMBER, "req-wrong-op")


def test_booking_commit_failure_reports_unknown_and_rolls_back(
    session_factory, seed,
) -> None:
    """提交失败时抛 OutcomeUnknownError，预约和额度占用都不留下。"""
    def broken_factory():
        session = session_factory()

        def fail_commit() -> None:
            raise OperationalError("COMMIT", {}, Exception("模拟提交失败"))

        session.commit = fail_commit  # type: ignore[method-assign]
        return session

    service = BookingService(broken_factory, FakeAuth(), timezone_name="Asia/Shanghai")
    with pytest.raises(OutcomeUnknownError) as error:
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1),
            "req-broken",
        )
    assert error.value.request_id == "req-broken"
    assert _booking_count(session_factory) == 0
    assert _credits(session_factory, 1) == (20, 0)


def test_coach_booking_list_is_scoped_to_own_sessions(
    session_factory, seed, service, course_service,
) -> None:
    """教练只能看到自己课次的学员名单，看不到其他教练的预约。"""
    _add_coach_and_room(session_factory, coach_id=2, account_id=20, room_id=2)
    from datetime import timedelta

    other_session = _new_session(
        course_service, "req-other-session", coach_id=2, room_id=2,
        start=SESSION_START + timedelta(days=1),
    )
    _add_member(session_factory, 2, "李四")
    _add_card(session_factory, card_id=2, member_id=2)
    service.book(MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-coach-a")
    service.book(
        RECEPTION, BookingInput(member_id=2, session_id=other_session, membership_id=2),
        "req-coach-b",
    )

    coach_two = Actor(account_id=20, role="coach", member_id=None, coach_id=2)
    page_one = service.list_bookings(COACH, BookingQuery())
    page_two = service.list_bookings(coach_two, BookingQuery())
    assert page_one.total == 1
    assert page_one.items[0].member_id == 1
    assert page_two.total == 1
    assert page_two.items[0].member_id == 2
    with pytest.raises(NotFoundError):
        service.get_booking(COACH, page_two.items[0].id)


def test_inactive_member_or_account_cannot_book(session_factory, seed, service) -> None:
    """会员档案或登录账号停用后不能新预约，也不占用额度。"""
    with session_factory() as session:
        with session.begin():
            session.execute(update(members).where(members.c.id == 1).values(is_active=False))
    with pytest.raises(InvalidState):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-inactive"
        )

    with session_factory() as session:
        with session.begin():
            session.execute(update(members).where(members.c.id == 1).values(is_active=True))
            session.execute(update(accounts).where(accounts.c.id == 3).values(is_active=False))
    with pytest.raises(InvalidState):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-account-off"
        )
    assert _booking_count(session_factory) == 0
    assert _credits(session_factory, 1) == (20, 0)


def test_cancelled_or_started_session_cannot_be_booked(session_factory, seed, service) -> None:
    """取消的课次和已开始的课次不能预约。"""
    with session_factory() as session:
        with session.begin():
            session.execute(
                update(course_sessions).where(course_sessions.c.id == 1)
                .values(status="cancelled")
            )
    with pytest.raises(InvalidState):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-session-off"
        )

    with session_factory() as session:
        with session.begin():
            session.execute(
                update(course_sessions).where(course_sessions.c.id == 1).values(
                    status="scheduled",
                    starts_at=datetime(2026, 10, 1, 1, 0),
                    ends_at=datetime(2026, 10, 1, 2, 0),
                )
            )
    with pytest.raises(InvalidState):
        service.book(
            MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-session-past"
        )
    assert _booking_count(session_factory) == 0


def test_card_date_boundaries(session_factory, seed, service) -> None:
    """valid_from 包含当天，valid_until 不包含当天。"""
    _add_card(
        session_factory, card_id=7, member_id=1,
        valid_from=date(2026, 12, 2), valid_until=date(2027, 1, 1),
    )
    _add_card(
        session_factory, card_id=8, member_id=1,
        valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 1),
    )
    _add_card(
        session_factory, card_id=9, member_id=1,
        valid_from=date(2026, 12, 1), valid_until=date(2026, 12, 2),
    )
    for card_id in (7, 8):
        with pytest.raises(CardNotEligible):
            service.book(
                MEMBER, BookingInput(member_id=1, session_id=1, membership_id=card_id),
                f"req-boundary-{card_id}",
            )
    assert service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=9), "req-boundary-ok"
    ).membership_id == 9


def test_receptionist_can_cancel_and_verify_result(session_factory, seed, service) -> None:
    """前台可以代会员取消，并能按原请求编号核实取消结果。"""
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-staff-cancel-book",
    )
    cancelled = service.cancel(RECEPTION, created.id, "req-staff-cancel")
    assert cancelled.status == "cancelled"
    assert _credits(session_factory, 1) == (20, 0)
    assert service.get_booking_by_request(RECEPTION, "req-staff-cancel").status == "cancelled"


def test_list_bookings_filters_by_status_and_window(session_factory, seed, service) -> None:
    """预约列表按状态和课次时间窗口筛选，空结果返回 Page。"""
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-list-book",
    )
    assert service.list_bookings(MEMBER, BookingQuery(status="reserved")).total == 1
    assert service.list_bookings(MEMBER, BookingQuery(status="cancelled")).total == 0
    outside = service.list_bookings(MEMBER, BookingQuery(
        window=DateWindow(
            start=datetime(2026, 12, 2, 0, 0, tzinfo=UTC),
            end=datetime(2026, 12, 3, 0, 0, tzinfo=UTC),
        )
    ))
    assert outside.items == []
    assert outside.total == 0
    assert service.get_booking(MEMBER, created.id).id == created.id


def test_cancel_after_session_cancelled_is_rejected(session_factory, seed, service, course_service) -> None:
    """课次已被管理员取消后，不能再走取消预约入口重复处理。"""
    created = service.book(
        MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-before-session-cancel",
    )
    course_service.cancel_session(ADMIN, 1, "req-cancel-session")
    assert _credits(session_factory, 1) == (20, 0)
    with pytest.raises(InvalidState):
        service.cancel(MEMBER, created.id, "req-after-session-cancel")


def test_booking_list_paging_and_staff_scope(session_factory, seed, service, course_service) -> None:
    """前台和管理员能查全部；会员只查自己；分页参数越界时明确报错。"""
    from datetime import timedelta

    _add_member(session_factory, 2, "李四")
    _add_card(session_factory, card_id=2, member_id=2)
    second = _new_session(
        course_service, "req-list-second", start=SESSION_START + timedelta(hours=2),
    )
    service.book(MEMBER, BookingInput(member_id=1, session_id=1, membership_id=1), "req-list-a")
    service.book(
        RECEPTION, BookingInput(member_id=2, session_id=second, membership_id=2), "req-list-b",
    )

    assert service.list_bookings(ADMIN, BookingQuery()).total == 2
    assert service.list_bookings(RECEPTION, BookingQuery()).total == 2
    assert service.list_bookings(MEMBER, BookingQuery()).total == 1
    page = service.list_bookings(ADMIN, BookingQuery(paging=PageRequest(page=2, page_size=1)))
    assert page.page == 2
    assert page.total == 2
    assert len(page.items) == 1
    with pytest.raises(InvalidInputError):
        service.list_bookings(ADMIN, BookingQuery(paging=PageRequest(page=0)))
