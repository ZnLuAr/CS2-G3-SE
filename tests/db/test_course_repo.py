"""数据访问层测试：验证 SQL、约束、分页和状态检查的实际结果。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import insert, select, update

from src.db.course_repo import (
    CoachRepository,
    CourseRepository,
    RoomRepository,
    SessionRepository,
)
from src.db.tables import accounts, bookings, course_sessions, members, memberships
from src.errors.business import (
    ConflictError,
    InvalidInputError,
    InvalidState,
    NotFoundError,
)
from src.models.contracts import (
    CoachInput,
    CoachUpdateInput,
    CourseInput,
    CourseQuery,
    DateWindow,
    NamedQuery,
    PageRequest,
    RoomInput,
    SessionInput,
    SessionQuery,
)
from tests.conftest import ADMIN


def _coach_account(session_factory, account_id: int, username: str) -> None:
    """补充一个启用中的教练账号，供创建教练测试使用。"""
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with session_factory() as session:
        with session.begin():
            session.execute(insert(accounts).values(
                id=account_id,
                username=username,
                password_hash="x",
                role="coach",
                is_active=True,
                created_at=now,
                updated_at=now,
            ))


def test_coach_create_checks_account_role_and_link(session_factory, seed) -> None:
    """创建教练要求账号存在、角色为教练且未重复绑定。"""
    _coach_account(session_factory, 10, "coach2")
    with session_factory() as session:
        repo = CoachRepository(session)

        with pytest.raises(NotFoundError):
            repo.create(CoachInput(account_id=999, name="王教练", specialty=""))

        with pytest.raises(InvalidState):
            repo.create(CoachInput(account_id=4, name="王教练", specialty=""))

        with pytest.raises(ConflictError):
            repo.create(CoachInput(account_id=2, name="王教练", specialty=""))

        created = repo.create(CoachInput(account_id=10, name="王教练", specialty="康复"))
        assert created.account_id == 10
        assert created.name == "王教练"
        assert created.is_active is True
        assert repo.get(created.id) == created


def test_coach_list_filters_and_stable_paging(session_factory, seed) -> None:
    """教练列表按姓名包含匹配和启用状态筛选，并按编号稳定分页。"""
    with session_factory() as session:
        repo = CoachRepository(session)
        page = repo.list(NamedQuery(keyword="李"))
        assert page.total == 1
        assert [item.name for item in page.items] == ["李教练"]

        page = repo.list(NamedQuery(keyword="不存在"))
        assert page.items == []
        assert page.total == 0

        page = repo.list(NamedQuery(paging=PageRequest(page=2, page_size=1)))
        assert page.page == 2
        assert page.total == 1
        assert page.items == []

        with pytest.raises(InvalidInputError):
            repo.list(NamedQuery(paging=PageRequest(page=0)))
        with pytest.raises(InvalidInputError):
            repo.list(NamedQuery(paging=PageRequest(page_size=101)))


def test_coach_update_and_deactivation_rules(session_factory, seed) -> None:
    """教练资料可修改；有未结束课次时不能停用，取消课次后可以停用。"""
    with session_factory() as session:
        repo = CoachRepository(session)
        updated = repo.update(1, CoachUpdateInput(name="李教练（资深）", specialty="力量"))
        assert updated.name == "李教练（资深）"
        assert updated.account_id == 2

        with pytest.raises(InvalidState):
            repo.set_active(1, False)

        session.execute(
            update(course_sessions)
            .where(course_sessions.c.id == 1)
            .values(status="cancelled")
        )
        session.commit()
        inactive = repo.set_active(1, False)
        assert inactive.is_active is False
        assert repo.set_active(1, True).is_active is True


def test_course_create_update_and_list(session_factory, seed) -> None:
    """课程模板保存名称与时长；修改模板不改变已有课次快照。"""
    with session_factory() as session:
        repo = CourseRepository(session)
        created = repo.create(CourseInput(name="拉伸课", kind="private", duration_minutes=45))
        assert created.duration_minutes == 45

        updated = repo.update(created.id, CourseInput(name="拉伸恢复课", kind="private", duration_minutes=60))
        assert updated.name == "拉伸恢复课"

        page = repo.list(CourseQuery(keyword="拉伸", is_active=True))
        assert [item.id for item in page.items] == [created.id]

        with pytest.raises(NotFoundError):
            repo.update(999, CourseInput(name="无", kind="private", duration_minutes=30))


def test_room_create_update_and_deactivation(session_factory, seed) -> None:
    """场地容量必须能容纳已排课次；有未结束课次时不能停用。"""
    with session_factory() as session:
        repo = RoomRepository(session)
        created = repo.create(RoomInput(name="B 教室", capacity=2))
        assert created.capacity == 2
        assert repo.update(created.id, RoomInput(name="B 教室（大）", capacity=3)).capacity == 3

        with pytest.raises(InvalidState):
            repo.set_active(1, False)

        session.execute(
            update(course_sessions)
            .where(course_sessions.c.id == 1)
            .values(status="completed")
        )
        session.commit()
        assert repo.set_active(1, False).is_active is False


def test_room_capacity_cannot_shrink_below_occupied(session_factory, seed) -> None:
    """缩小场地容量时，不能低于未结束课次的占用人数。"""
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with session_factory() as session:
        with session.begin():
            # 同一课次安排 2 名会员，检验容量校验不是只检查场地原容量。
            session.execute(insert(members).values(
                id=2, account_id=None, name="李四", phone=None,
                is_active=True, created_at=now, updated_at=now,
            ))
            session.execute(insert(memberships).values(
                id=2, member_id=2, product_id=1, name="月卡", kind="monthly",
                price="199.00", private_lesson_credits=20, access_uses=None,
                valid_days=30, valid_from=datetime(2026, 1, 1).date(),
                valid_until=datetime(2027, 1, 1).date(), remaining_accesses=None,
                remaining_private_lessons=20, reserved_private_lessons=0,
                status="active", created_at=now, updated_at=now,
            ))
            session.execute(
                update(course_sessions)
                .where(course_sessions.c.id == 1)
                .values(capacity=2)
            )
            session.execute(insert(bookings), [
                {
                    "id": 1, "member_id": 1, "session_id": 1, "membership_id": 1,
                    "status": "reserved", "booked_at": now,
                    "checked_in_at": None, "closed_at": None,
                    "created_at": now, "updated_at": now,
                },
                {
                    "id": 2, "member_id": 2, "session_id": 1, "membership_id": 2,
                    "status": "reserved", "booked_at": now,
                    "checked_in_at": None, "closed_at": None,
                    "created_at": now, "updated_at": now,
                },
            ])
        repo = RoomRepository(session)
        with pytest.raises(InvalidState):
            repo.update(1, RoomInput(name="A 教室", capacity=1))


def test_session_conflict_uses_half_open_intervals(session_factory, seed) -> None:
    """相邻时段不冲突，重叠时段冲突；取消的课次不占用时间。"""
    with session_factory() as session:
        repo = SessionRepository(session)
        adjacent = DateWindow(
            start=datetime(2026, 12, 1, 7, 0, tzinfo=timezone.utc),
            end=datetime(2026, 12, 1, 8, 0, tzinfo=timezone.utc),
        )
        assert repo.has_conflict(coach_id=1, room_id=1, window=adjacent) is False

        overlap = DateWindow(
            start=datetime(2026, 12, 1, 6, 30, tzinfo=timezone.utc),
            end=datetime(2026, 12, 1, 7, 30, tzinfo=timezone.utc),
        )
        assert repo.has_conflict(coach_id=1, room_id=1, window=overlap) is True
        assert repo.has_conflict(coach_id=2, room_id=2, window=overlap) is False

        session.execute(
            update(course_sessions)
            .where(course_sessions.c.id == 1)
            .values(status="cancelled")
        )
        session.commit()
        assert repo.has_conflict(coach_id=1, room_id=1, window=overlap) is False


def test_session_create_snapshot_and_list_window(session_factory, seed) -> None:
    """课次保存课程名称快照；课表按开始时间窗口筛选并统计占用人数。"""
    with session_factory() as session:
        course_repo = CourseRepository(session)
        session_repo = SessionRepository(session)
        session.execute(
            update(course_sessions)
            .where(course_sessions.c.id == 1)
            .values(status="cancelled")
        )
        session.commit()
        created = session_repo.create(
            SessionInput(
                course_id=1,
                coach_id=1,
                room_id=1,
                starts_at=datetime(2026, 12, 2, 6, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 12, 2, 7, 0, tzinfo=timezone.utc),
                capacity=1,
            ),
            course_name="排课时名称",
            kind="private",
        )
        course_repo.update(1, CourseInput(name="改名后", kind="private", duration_minutes=60))
        session.commit()
        assert session_repo.get(created.id).course_name == "排课时名称"

        page = session_repo.list(SessionQuery(
            window=DateWindow(
                start=datetime(2026, 12, 2, 0, 0, tzinfo=timezone.utc),
                end=datetime(2026, 12, 3, 0, 0, tzinfo=timezone.utc),
            ),
            coach_id=1,
            status="scheduled",
        ))
        assert page.total == 1
        assert page.items[0].coach_name == "李教练"
        assert page.items[0].room_name == "A 教室"
        assert page.items[0].occupied_count == 0
        assert page.items[0].available_count == 1


def test_session_queries_return_none_and_lock(session_factory, seed) -> None:
    """不存在的课次返回 None；锁定查询在 SQLite 中可执行。"""
    with session_factory() as session:
        repo = SessionRepository(session)
        assert repo.get(999) is None
        assert repo.lock(999) is None
        locked = repo.lock(1)
        assert locked is not None
        assert locked.capacity == 1
        assert locked.starts_at == datetime(2026, 12, 1, 6, 0, tzinfo=timezone.utc)
