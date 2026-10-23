"""教练、课程模板与场地业务服务测试。

这些用例直接调用服务层（不经过菜单），验证权限、输入边界、事务提交和
固定返回格式。账号身份校验由 `FakeAuth` 代替，真实账号停用等行为需在
账号模块实现后联调。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import OperationalError

from src.db.tables import accounts, coaches, course_sessions, courses, rooms
from src.errors.business import (
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
)
from src.errors.storage import StorageError
from src.models.contracts import (
    CoachInput,
    CoachUpdateInput,
    CourseInput,
    CourseQuery,
    NamedQuery,
    PageRequest,
    RoomInput,
)
from src.services.course_service import CourseService
from tests.conftest import ADMIN, COACH, MEMBER, RECEPTION, FakeAuth


def _add_coach_account(session_factory, account_id: int = 10, username: str = "coach2") -> None:
    """补充一个启用中的教练账号，供建档用例使用。"""
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


def _count(session_factory, table) -> int:
    """统计表内记录数，用于确认失败操作没有留下半条数据。"""
    with session_factory() as session:
        return int(session.scalar(select(func.count()).select_from(table)) or 0)


@pytest.fixture()
def service(session_factory) -> CourseService:
    """使用假身份校验构造课程服务。"""
    return CourseService(session_factory, FakeAuth())


def test_admin_can_create_read_update_and_deactivate_coach(session_factory, seed, service) -> None:
    """管理员可以完整维护教练档案，新教练没有课次时可直接停用。"""
    _add_coach_account(session_factory)
    created = service.create_coach(
        ADMIN, CoachInput(account_id=10, name=" 王教练 ", specialty=" 康复 ")
    )
    assert created.name == "王教练"
    assert created.specialty == "康复"
    assert created.is_active is True

    assert service.get_coach(MEMBER, created.id).id == created.id
    assert service.list_coaches(MEMBER, NamedQuery(keyword="王")).total == 1

    updated = service.update_coach(
        ADMIN, created.id, CoachUpdateInput(name="王教练", specialty="体态调整")
    )
    assert updated.specialty == "体态调整"
    assert service.set_coach_active(ADMIN, created.id, False).is_active is False
    assert service.set_coach_active(ADMIN, created.id, True).is_active is True


def test_only_admin_can_write_coach_course_and_room(session_factory, seed, service) -> None:
    """会员、教练、前台都不能维护教练、模板和场地，服务层直接拒绝。"""
    for actor in (COACH, MEMBER, RECEPTION):
        with pytest.raises(PermissionDenied):
            service.create_coach(actor, CoachInput(account_id=10, name="王教练", specialty=""))
        with pytest.raises(PermissionDenied):
            service.create_course(actor, CourseInput(name="拉伸", kind="private", duration_minutes=30))
        with pytest.raises(PermissionDenied):
            service.create_room(actor, RoomInput(name="B 教室", capacity=2))
        with pytest.raises(PermissionDenied):
            service.set_course_active(actor, 1, False)
        with pytest.raises(PermissionDenied):
            service.set_room_active(actor, 1, False)


def test_coach_input_validation_leaves_no_record(session_factory, seed, service) -> None:
    """空姓名、超长姓名或超长专长被拒绝，数据库不新增教练。"""
    before = _count(session_factory, coaches)
    with pytest.raises(InvalidInputError):
        service.create_coach(ADMIN, CoachInput(account_id=10, name="   ", specialty=""))
    with pytest.raises(InvalidInputError):
        service.create_coach(ADMIN, CoachInput(account_id=10, name="名" * 101, specialty=""))
    with pytest.raises(InvalidInputError):
        service.create_coach(ADMIN, CoachInput(account_id=10, name="王教练", specialty="专" * 201))
    with pytest.raises(InvalidInputError):
        service.update_coach(ADMIN, 1, CoachUpdateInput(name="", specialty=""))
    assert _count(session_factory, coaches) == before
    with session_factory() as session:
        name = session.execute(select(coaches.c.name).where(coaches.c.id == 1)).scalar_one()
        assert name == "李教练"


def test_course_validation(session_factory, seed, service) -> None:
    """课程类型只能是 private，时长只能是 1–150 的整数分钟。"""
    before = _count(session_factory, courses)
    cases = [
        CourseInput(name="拉伸", kind="group", duration_minutes=60),  # type: ignore[arg-type]
        CourseInput(name="拉伸", kind="private", duration_minutes=0),
        CourseInput(name="拉伸", kind="private", duration_minutes=151),
        CourseInput(name="拉伸", kind="private", duration_minutes=True),  # type: ignore[arg-type]
        CourseInput(name=" ", kind="private", duration_minutes=60),
    ]
    for data in cases:
        with pytest.raises(InvalidInputError):
            service.create_course(ADMIN, data)
    assert _count(session_factory, courses) == before


def test_room_validation(session_factory, seed, service) -> None:
    """场地名称不能为空，容量必须为正整数。"""
    before = _count(session_factory, rooms)
    for data in [
        RoomInput(name="", capacity=2),
        RoomInput(name="B 教室", capacity=0),
        RoomInput(name="B 教室", capacity=-1),
        RoomInput(name="B 教室", capacity=True),  # type: ignore[arg-type]
    ]:
        with pytest.raises(InvalidInputError):
            service.create_room(ADMIN, data)
    assert _count(session_factory, rooms) == before


def test_course_crud_and_query(session_factory, seed, service) -> None:
    """课程模板可创建、查询、修改、归档，列表返回 Page 且可按关键词筛选。"""
    created = service.create_course(
        ADMIN, CourseInput(name=" 拉伸课 ", kind="private", duration_minutes=45)
    )
    assert created.name == "拉伸课"
    assert service.get_course(MEMBER, created.id).name == "拉伸课"

    page = service.list_courses(
        MEMBER,
        CourseQuery(keyword="拉伸", kind="private", is_active=True, paging=PageRequest(page_size=10)),
    )
    assert page.total == 1
    assert page.items[0].id == created.id

    updated = service.update_course(
        ADMIN, created.id, CourseInput(name="拉伸恢复课", kind="private", duration_minutes=60)
    )
    assert updated.name == "拉伸恢复课"
    assert updated.duration_minutes == 60

    archived = service.set_course_active(ADMIN, created.id, False)
    assert archived.is_active is False
    assert service.list_courses(ADMIN, CourseQuery(is_active=True)).total == 1


def test_room_crud_and_deactivation_requires_finished_sessions(session_factory, seed, service) -> None:
    """场地可维护；有未结束课次时停用被拒绝，取消课次后可停用。"""
    created = service.create_room(ADMIN, RoomInput(name=" B 教室 ", capacity=2))
    assert created.name == "B 教室"
    assert service.get_room(MEMBER, created.id).capacity == 2

    updated = service.update_room(ADMIN, created.id, RoomInput(name="B 教室", capacity=3))
    assert updated.capacity == 3
    assert service.set_room_active(ADMIN, created.id, False).is_active is False

    with pytest.raises(InvalidState):
        service.set_room_active(ADMIN, 1, False)

    with session_factory() as session:
        with session.begin():
            session.execute(
                update(course_sessions)
                .where(course_sessions.c.id == 1)
                .values(status="cancelled")
            )
    assert service.set_room_active(ADMIN, 1, False).is_active is False


def test_coach_deactivation_requires_finished_sessions(session_factory, seed, service) -> None:
    """有未结束课次的教练不能停用，取消课次后可以停用。"""
    with pytest.raises(InvalidState):
        service.set_coach_active(ADMIN, 1, False)
    with session_factory() as session:
        with session.begin():
            session.execute(
                update(course_sessions)
                .where(course_sessions.c.id == 1)
                .values(status="completed")
            )
    assert service.set_coach_active(ADMIN, 1, False).is_active is False


def test_missing_records_raise_not_found(session_factory, seed, service) -> None:
    """查询、修改不存在的记录统一抛 NotFoundError。"""
    with pytest.raises(NotFoundError):
        service.get_coach(ADMIN, 999)
    with pytest.raises(NotFoundError):
        service.update_coach(ADMIN, 999, CoachUpdateInput(name="无", specialty=""))
    with pytest.raises(NotFoundError):
        service.get_course(ADMIN, 999)
    with pytest.raises(NotFoundError):
        service.get_room(ADMIN, 999)
    with pytest.raises(NotFoundError):
        service.update_room(ADMIN, 999, RoomInput(name="无", capacity=1))


def test_read_operations_verify_actor_each_time(session_factory, seed) -> None:
    """每次操作都调用身份校验，而不是只在登录时检查一次。"""
    auth = FakeAuth()
    service = CourseService(session_factory, auth)
    service.get_coach(MEMBER, 1)
    service.list_courses(MEMBER, CourseQuery())
    service.list_rooms(MEMBER, NamedQuery())
    assert auth.calls == 3


def test_invalid_paging_is_rejected(session_factory, seed, service) -> None:
    """分页参数越界时明确报错，不悄悄改成默认值。"""
    with pytest.raises(InvalidInputError):
        service.list_coaches(ADMIN, NamedQuery(paging=PageRequest(page=0)))
    with pytest.raises(InvalidInputError):
        service.list_courses(ADMIN, CourseQuery(paging=PageRequest(page_size=0)))
    with pytest.raises(InvalidInputError):
        service.list_rooms(ADMIN, NamedQuery(paging=PageRequest(page_size=101)))


def test_database_failure_rolls_back_course_creation(session_factory, seed) -> None:
    """提交失败时回滚，不留下半条课程模板，并把数据库异常转成 StorageError。"""
    before = _count(session_factory, courses)

    def broken_factory():
        session = session_factory()

        def fail_commit() -> None:
            raise OperationalError("COMMIT", {}, Exception("模拟提交失败"))

        session.commit = fail_commit  # type: ignore[method-assign]
        return session

    service = CourseService(broken_factory, FakeAuth())
    with pytest.raises(StorageError):
        service.create_course(
            ADMIN, CourseInput(name="不会保存", kind="private", duration_minutes=30)
        )
    assert _count(session_factory, courses) == before
