"""课程与预约模块测试共用的数据库夹具。

测试使用 SQLite 内存库，表结构由 `src/db/tables.py` 的同一份 SQLAlchemy Core
定义创建，因此列名、约束和索引与生产 MySQL 脚本保持一致。SQLite 不支持
`SELECT ... FOR UPDATE` 的加锁语义，仓储层可以执行，但并发行为仍需在真实
MySQL 测试库中验证，详见测试笔记。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterator

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.tables import (
    accounts,
    coaches,
    course_sessions,
    courses,
    members,
    memberships,
    rooms,
)
from src.models.contracts import Actor


@pytest.fixture()
def engine() -> Iterator[Engine]:
    """创建内存 SQLite 引擎并建表；测试结束自动销毁。"""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        """SQLite 默认关闭外键检查，测试中显式打开以贴近 MySQL 行为。"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from src.db.tables import metadata

    metadata.create_all(engine)
    try:
        yield engine
    finally:
        metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """返回与测试引擎绑定的会话工厂。"""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture()
def seed(session_factory) -> dict[str, int]:
    """写入一套最小可用数据：管理员、教练、会员、期限卡、模板、场地和课次。

    课次时间选在 2026-12-01 06:00–07:00 UTC，即上海时间 14:00–15:00，
    便于同时验证门店日期转换和时区显示。
    """
    now = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    with session_factory() as session:
        with session.begin():
            session.execute(insert(accounts), [
                {
                    "id": 1, "username": "admin", "password_hash": "x",
                    "role": "admin", "is_active": True,
                    "created_at": now, "updated_at": now,
                },
                {
                    "id": 2, "username": "coach", "password_hash": "x",
                    "role": "coach", "is_active": True,
                    "created_at": now, "updated_at": now,
                },
                {
                    "id": 3, "username": "member", "password_hash": "x",
                    "role": "member", "is_active": True,
                    "created_at": now, "updated_at": now,
                },
                {
                    "id": 4, "username": "reception", "password_hash": "x",
                    "role": "receptionist", "is_active": True,
                    "created_at": now, "updated_at": now,
                },
            ])
            session.execute(insert(members), [{
                "id": 1, "account_id": 3, "name": "张三", "phone": "13800000000",
                "is_active": True, "created_at": now, "updated_at": now,
            }])
            session.execute(insert(memberships), [{
                "id": 1, "member_id": 1, "product_id": 1, "name": "月卡",
                "kind": "monthly", "price": Decimal("199.00"),
                "private_lesson_credits": 20, "access_uses": None,
                "valid_days": 30, "valid_from": date(2026, 1, 1),
                "valid_until": date(2027, 1, 1), "remaining_accesses": None,
                "remaining_private_lessons": 20, "reserved_private_lessons": 0,
                "status": "active", "created_at": now, "updated_at": now,
            }])
            session.execute(insert(coaches), [{
                "id": 1, "account_id": 2, "name": "李教练",
                "specialty": "力量训练", "is_active": True,
                "created_at": now, "updated_at": now,
            }])
            session.execute(insert(courses), [{
                "id": 1, "name": "私教体验课", "kind": "private",
                "duration_minutes": 60, "is_active": True,
                "created_at": now, "updated_at": now,
            }])
            session.execute(insert(rooms), [{
                "id": 1, "name": "A 教室", "capacity": 4, "is_active": True,
                "created_at": now, "updated_at": now,
            }])
            session.execute(insert(course_sessions), [{
                "id": 1, "course_id": 1, "course_name": "私教体验课",
                "kind": "private", "coach_id": 1, "room_id": 1,
                "starts_at": datetime(2026, 12, 1, 6, 0),
                "ends_at": datetime(2026, 12, 1, 7, 0),
                "capacity": 1, "status": "scheduled",
                "created_at": now, "updated_at": now,
            }])
    return {
        "admin_account": 1,
        "coach_account": 2,
        "member_account": 3,
        "reception_account": 4,
        "member": 1,
        "membership": 1,
        "coach": 1,
        "course": 1,
        "room": 1,
        "session": 1,
    }


ADMIN = Actor(account_id=1, role="admin", member_id=None, coach_id=None)
COACH = Actor(account_id=2, role="coach", member_id=None, coach_id=1)
MEMBER = Actor(account_id=3, role="member", member_id=1, coach_id=None)
RECEPTION = Actor(account_id=4, role="receptionist", member_id=None, coach_id=None)


class FakeAuth:
    """替代账号服务的最小实现：只返回传入身份，不查数据库。

    课程与预约服务的权限检查、事务边界和 SQL 仍会执行；账号停用、角色变化等
    身份校验由账号模块实现后联调验证。
    """

    def __init__(self) -> None:
        self.calls = 0

    def verify_actor(self, session: Session, actor: Actor) -> Actor:  # noqa: ARG002
        self.calls += 1
        return actor
