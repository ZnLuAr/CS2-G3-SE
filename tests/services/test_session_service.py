"""排课、课表查询、课次取消与收尾的业务测试。

用例覆盖：时长与容量校验、教练/场地撞期、按身份查看课表、请求编号防重、
取消课次释放额度，以及完成课次前的待处理预约检查。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import OperationalError

from src.db.tables import (
    accounts,
    bookings,
    coaches,
    course_sessions,
    courses,
    members,
    memberships,
    operation_records,
    rooms,
)
from src.errors.business import (
    ConflictError,
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
    ScheduleConflict,
)
from src.errors.storage import OutcomeUnknownError, StorageError
from src.models.contracts import (
    Actor,
    DateWindow,
    PageRequest,
    SessionInput,
    SessionQuery,
)
from src.services.course_service import CourseService
from tests.conftest import ADMIN, COACH, MEMBER, FakeAuth

UTC = timezone.utc
BASE = datetime(2026, 12, 5, 6, 0, tzinfo=UTC)


def _input(**overrides) -> SessionInput:
    """构造一节默认 60 分钟的私教课，按需覆盖字段。"""
    values = {
        "course_id": 1,
        "coach_id": 1,
        "room_id": 1,
        "starts_at": BASE,
        "ends_at": datetime(2026, 12, 5, 7, 0, tzinfo=UTC),
        "capacity": 1,
    }
    values.update(overrides)
    return SessionInput(**values)


def _add_coach(session_factory, *, account_id: int, coach_id: int, name: str) -> None:
    """补充教练账号和档案，用于测试跨教练权限。"""
    now = datetime(2026, 10, 1, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.execute(insert(accounts).values(
                id=account_id, username=f"coach{coach_id}", password_hash="x",
                role="coach", is_active=True, created_at=now, updated_at=now,
            ))
            session.execute(insert(coaches).values(
                id=coach_id, account_id=account_id, name=name, specialty="",
                is_active=True, created_at=now, updated_at=now,
            ))


def _add_admin(session_factory, account_id: int) -> Actor:
    """补充另一个管理员账号，测试请求编号跨操作者复用。"""
    now = datetime(2026, 10, 1, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.execute(insert(accounts).values(
                id=account_id, username=f"admin{account_id}", password_hash="x",
                role="admin", is_active=True, created_at=now, updated_at=now,
            ))
    return Actor(account_id=account_id, role="admin", member_id=None, coach_id=None)


def _count_sessions(session_factory) -> int:
    """统计课次数量，确认失败排课没有留下记录。"""
    with session_factory() as session:
        return int(session.scalar(select(func.count()).select_from(course_sessions)) or 0)


@pytest.fixture()
def service(session_factory) -> CourseService:
    """使用假身份校验构造课程服务。"""
    return CourseService(session_factory, FakeAuth())


def test_admin_creates_session_and_queries_it(session_factory, seed, service) -> None:
    """管理员排课后可按详情、时间窗口和请求编号查询，快照与余位正确。"""
    created = service.create_session(ADMIN, _input(), "req-create-1")
    assert created.course_name == "私教体验课"
    assert created.kind == "private"
    assert created.coach_name == "李教练"
    assert created.room_name == "A 教室"
    assert created.capacity == 1
    assert created.occupied_count == 0
    assert created.available_count == 1
    assert created.status == "scheduled"
    assert created.starts_at == BASE

    assert service.get_session(MEMBER, created.id).id == created.id
    page = service.list_sessions(MEMBER, SessionQuery(
        window=DateWindow(
            start=datetime(2026, 12, 5, 0, 0, tzinfo=UTC),
            end=datetime(2026, 12, 6, 0, 0, tzinfo=UTC),
        ),
        status="scheduled",
    ))
    assert page.total == 1
    assert page.items[0].id == created.id

    assert service.get_session_by_request(ADMIN, "req-create-1").id == created.id
    with pytest.raises(NotFoundError):
        service.get_session_by_request(ADMIN, "req-not-exist")


def test_session_validation_rejects_bad_time_and_references(session_factory, seed, service) -> None:
    """容量、时长、时区和启停状态不合规时拒绝排课，不写记录。"""
    before = _count_sessions(session_factory)
    cases = [
        _input(capacity=2),
        _input(ends_at=datetime(2026, 12, 5, 6, 30, tzinfo=UTC)),
        _input(starts_at=datetime(2026, 12, 5, 6, 0)),
        _input(ends_at=datetime(2026, 12, 5, 6, 0, tzinfo=UTC)),
        _input(coach_id=999),
        _input(course_id=999),
        _input(room_id=999),
    ]
    for data in cases:
        with pytest.raises((InvalidInputError, NotFoundError)):
            service.create_session(ADMIN, data, f"req-bad-{id(data)}")
    assert _count_sessions(session_factory) == before

    with session_factory() as session:
        with session.begin():
            session.execute(update(courses).where(courses.c.id == 1).values(is_active=False))
    with pytest.raises(InvalidState):
        service.create_session(ADMIN, _input(), "req-archived-course")

    with session_factory() as session:
        with session.begin():
            session.execute(update(coaches).where(coaches.c.id == 1).values(is_active=False))
    with pytest.raises(InvalidState):
        service.create_session(ADMIN, _input(), "req-inactive-coach")

    with session_factory() as session:
        with session.begin():
            session.execute(update(courses).where(courses.c.id == 1).values(is_active=True))
            session.execute(update(coaches).where(coaches.c.id == 1).values(is_active=True))
            session.execute(update(rooms).where(rooms.c.id == 1).values(is_active=False))
    with pytest.raises(InvalidState):
        service.create_session(ADMIN, _input(), "req-inactive-room")


def test_only_admin_can_create_or_cancel_session(session_factory, seed, service) -> None:
    """教练、会员、前台不能排课，也不能取消课次。"""
    for actor in (COACH, MEMBER):
        with pytest.raises(PermissionDenied):
            service.create_session(actor, _input(), "req-perm")
        with pytest.raises(PermissionDenied):
            service.cancel_session(actor, 1, "req-perm-cancel")
    created = service.create_session(ADMIN, _input(), "req-cancel-perm")
    with pytest.raises(PermissionDenied):
        service.cancel_session(COACH, created.id, "req-cancel-perm-2")


def test_session_conflict_and_cancelled_session_release_slot(session_factory, seed, service) -> None:
    """教练或场地重叠时拒绝；相邻时段可以排；取消后时段重新可用。"""
    now = datetime(2026, 10, 1, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.execute(insert(rooms).values(
                id=2, name="B 教室", capacity=1, is_active=True,
                created_at=now, updated_at=now,
            ))
    first = service.create_session(ADMIN, _input(), "req-conflict-a")

    with pytest.raises(ScheduleConflict):
        service.create_session(
            ADMIN,
            _input(
                room_id=2,
                starts_at=datetime(2026, 12, 5, 6, 30, tzinfo=UTC),
                ends_at=datetime(2026, 12, 5, 7, 30, tzinfo=UTC),
            ),
            "req-conflict-coach",
        )

    _add_coach(session_factory, account_id=20, coach_id=2, name="赵教练")
    with pytest.raises(ScheduleConflict):
        service.create_session(
            ADMIN,
            _input(
                coach_id=2,
                starts_at=datetime(2026, 12, 5, 6, 30, tzinfo=UTC),
                ends_at=datetime(2026, 12, 5, 7, 30, tzinfo=UTC),
            ),
            "req-conflict-room",
        )

    adjacent = service.create_session(
        ADMIN,
        _input(
            starts_at=datetime(2026, 12, 5, 7, 0, tzinfo=UTC),
            ends_at=datetime(2026, 12, 5, 8, 0, tzinfo=UTC),
        ),
        "req-adjacent",
    )
    assert adjacent.starts_at == datetime(2026, 12, 5, 7, 0, tzinfo=UTC)

    service.cancel_session(ADMIN, first.id, "req-cancel-first")
    again = service.create_session(
        ADMIN,
        _input(
            starts_at=datetime(2026, 12, 5, 6, 0, tzinfo=UTC),
            ends_at=datetime(2026, 12, 5, 7, 0, tzinfo=UTC),
        ),
        "req-reuse-slot",
    )
    assert again.status == "scheduled"


def test_session_request_id_is_idempotent_and_payload_is_checked(session_factory, seed, service) -> None:
    """同一请求编号返回原课次；输入或操作者不同则拒绝。"""
    first = service.create_session(ADMIN, _input(), "req-idem")
    second = service.create_session(ADMIN, _input(), "req-idem")
    assert second.id == first.id
    assert _count_sessions(session_factory) == 2  # 种子课次 + 新建课次

    with pytest.raises(ConflictError):
        service.create_session(
            ADMIN,
            _input(starts_at=datetime(2026, 12, 5, 8, 0, tzinfo=UTC),
                   ends_at=datetime(2026, 12, 5, 9, 0, tzinfo=UTC)),
            "req-idem",
        )

    other_admin = _add_admin(session_factory, 30)
    with pytest.raises(ConflictError):
        service.create_session(other_admin, _input(), "req-idem")


def test_coach_sees_only_own_schedule_but_member_sees_public_schedule(
    session_factory, seed, service,
) -> None:
    """教练只能查看自己的课表；会员可浏览课表但不含其他学员资料。"""
    _add_coach(session_factory, account_id=20, coach_id=2, name="赵教练")
    own = service.create_session(ADMIN, _input(), "req-own")
    other = service.create_session(
        ADMIN,
        _input(
            coach_id=2,
            starts_at=datetime(2026, 12, 6, 6, 0, tzinfo=UTC),
            ends_at=datetime(2026, 12, 6, 7, 0, tzinfo=UTC),
        ),
        "req-other-coach",
    )

    page = service.list_sessions(COACH, SessionQuery())
    assert {item.id for item in page.items} == {1, own.id}
    with pytest.raises(PermissionDenied):
        service.list_sessions(COACH, SessionQuery(coach_id=2))
    with pytest.raises(NotFoundError):
        service.get_session(COACH, other.id)

    assert service.get_session(MEMBER, other.id).coach_id == 2
    assert service.list_sessions(MEMBER, SessionQuery()).total == 3
    # 会员可见的 SessionView 不包含预约会员名单。
    assert not hasattr(service.get_session(MEMBER, own.id), "member_names")


def test_get_session_by_request_checks_operation_and_owner(session_factory, seed, service) -> None:
    """核实接口只返回本人原请求；请求类型不符或操作者不符时拒绝。"""
    created = service.create_session(ADMIN, _input(), "req-verify")
    with session_factory() as session:
        with session.begin():
            session.execute(insert(operation_records).values(
                request_id="req-wrong-type",
                actor_id=1,
                operation="book",
                payload_hash="x" * 64,
                result_id=created.id,
                created_at=datetime(2026, 10, 1, tzinfo=UTC),
            ))
    with pytest.raises(ConflictError):
        service.get_session_by_request(ADMIN, "req-wrong-type")

    other_admin = _add_admin(session_factory, 30)
    with pytest.raises(NotFoundError):
        service.get_session_by_request(other_admin, "req-verify")  # 只有原操作者能核实

    _add_coach(session_factory, account_id=20, coach_id=2, name="赵教练")
    other = service.create_session(
        ADMIN,
        _input(
            coach_id=2,
            starts_at=datetime(2026, 12, 6, 6, 0, tzinfo=UTC),
            ends_at=datetime(2026, 12, 6, 7, 0, tzinfo=UTC),
        ),
        "req-other-verify",
    )
    with pytest.raises(NotFoundError):
        service.get_session_by_request(COACH, "req-other-verify")
    assert other.coach_id == 2


def test_cancel_session_cancels_bookings_and_releases_credits(session_factory, seed, service) -> None:
    """取消课次把未取消预约改为 cancelled，并释放全部私教额度占用。"""
    created = service.create_session(ADMIN, _input(), "req-create-for-cancel")
    now = datetime(2026, 10, 1, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.execute(insert(bookings).values(
                id=1, member_id=1, session_id=created.id, membership_id=1,
                status="reserved", booked_at=now,
                checked_in_at=None, closed_at=None,
                created_at=now, updated_at=now,
            ))
            session.execute(
                update(memberships)
                .where(memberships.c.id == 1)
                .values(reserved_private_lessons=1)
            )

    cancelled = service.cancel_session(ADMIN, created.id, "req-cancel")
    assert cancelled.status == "cancelled"
    with session_factory() as session:
        booking = session.execute(
            select(bookings).where(bookings.c.id == 1)
        ).mappings().one()
        assert booking["status"] == "cancelled"
        assert booking["closed_at"] is not None
        reserved = session.execute(
            select(memberships.c.reserved_private_lessons).where(memberships.c.id == 1)
        ).scalar_one()
        assert reserved == 0

    # 同一请求编号重试返回当前结果，不重复释放。
    assert service.cancel_session(ADMIN, created.id, "req-cancel").status == "cancelled"
    with pytest.raises(InvalidState):
        service.cancel_session(ADMIN, created.id, "req-cancel-again")


def test_cancel_session_rejects_started_or_completed_sessions(session_factory, seed, service) -> None:
    """已开始、已完成或已取消的课次不能再次取消。"""
    past = service.create_session(
        ADMIN,
        _input(
            starts_at=datetime(2026, 10, 1, 1, 0, tzinfo=UTC),
            ends_at=datetime(2026, 10, 1, 2, 0, tzinfo=UTC),
        ),
        "req-past",
    )
    with pytest.raises(InvalidState):
        service.cancel_session(ADMIN, past.id, "req-past-cancel")

    completed = service.complete_session(ADMIN, past.id)
    assert completed.status == "completed"
    assert service.complete_session(ADMIN, past.id).status == "completed"
    with pytest.raises(InvalidState):
        service.cancel_session(ADMIN, past.id, "req-completed-cancel")


def test_complete_session_requires_end_time_and_no_active_bookings(
    session_factory, seed, service,
) -> None:
    """未结束或有待处理预约时不能完成；完成后重复调用返回当前状态。"""
    future = service.create_session(ADMIN, _input(), "req-future")
    with pytest.raises(InvalidState):
        service.complete_session(ADMIN, future.id)

    past = service.create_session(
        ADMIN,
        _input(
            starts_at=datetime(2026, 10, 2, 1, 0, tzinfo=UTC),
            ends_at=datetime(2026, 10, 2, 2, 0, tzinfo=UTC),
        ),
        "req-past-active",
    )
    now = datetime(2026, 10, 1, tzinfo=UTC)
    with session_factory() as session:
        with session.begin():
            session.execute(insert(bookings).values(
                id=1, member_id=1, session_id=past.id, membership_id=1,
                status="reserved", booked_at=now,
                checked_in_at=None, closed_at=None,
                created_at=now, updated_at=now,
            ))
    with pytest.raises(InvalidState):
        service.complete_session(ADMIN, past.id)

    with session_factory() as session:
        with session.begin():
            session.execute(
                update(bookings).where(bookings.c.id == 1).values(status="cancelled")
            )
    assert service.complete_session(ADMIN, past.id).status == "completed"

    _add_coach(session_factory, account_id=20, coach_id=2, name="赵教练")
    with session_factory() as session:
        with session.begin():
            session.execute(
                update(course_sessions)
                .where(course_sessions.c.id == past.id)
                .values(status="scheduled")
            )
    with pytest.raises(PermissionDenied):
        service.complete_session(
            Actor(account_id=20, role="coach", member_id=None, coach_id=2), past.id
        )


def test_create_session_commit_failure_reports_unknown(session_factory, seed) -> None:
    """带请求编号的写操作提交失败时抛 OutcomeUnknownError，提示按编号核实。"""
    def broken_factory():
        session = session_factory()

        def fail_commit() -> None:
            raise OperationalError("COMMIT", {}, Exception("模拟提交失败"))

        session.commit = fail_commit  # type: ignore[method-assign]
        return session

    service = CourseService(broken_factory, FakeAuth())
    with pytest.raises(OutcomeUnknownError) as error:
        service.create_session(ADMIN, _input(), "req-broken-commit")
    assert error.value.request_id == "req-broken-commit"
