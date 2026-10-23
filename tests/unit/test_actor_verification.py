"""使用内存 SQLite 验证当前身份复核与档案关联状态。"""

from __future__ import annotations

from dataclasses import replace
from datetime import timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.config import LogConfig
from src.db.account_repo import AccountRepository
from src.errors.business import AuthenticationError
from src.errors.storage import StorageError
from src.models.contracts import Actor
from src.services.auth_service import AuthService


@pytest.fixture
def actor_db():
    """仅创建身份复核需要的表，并在结束时释放会话及引擎。"""
    engine = create_engine("sqlite://")
    definitions = (
        "accounts (id INTEGER PRIMARY KEY, username TEXT, password_hash TEXT, "
        "role TEXT, is_active INTEGER, created_at DATETIME, updated_at DATETIME)",
        "members (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, status TEXT, "
        "archived_at DATETIME, created_at DATETIME, updated_at DATETIME)",
        "coaches (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, is_active INTEGER, "
        "created_at DATETIME, updated_at DATETIME)",
        "member_account_links (account_id INTEGER UNIQUE, member_id INTEGER UNIQUE)",
        "coach_account_links (account_id INTEGER UNIQUE, coach_id INTEGER UNIQUE)",
    )
    with engine.begin() as connection:
        for definition in definitions:
            connection.exec_driver_sql("CREATE TABLE " + definition)
        for account_id, role in ((1, "admin"), (2, "receptionist"), (3, "member"), (4, "coach")):
            connection.execute(text(
                "INSERT INTO accounts VALUES "
                "(:id, :username, 'unused-test-hash', :role, 1, :created, :created)"
            ), {"id": account_id, "username": f"account_{account_id}", "role": role,
                "created": "2026-10-20 02:00:00"})
        for member_id in (30, 31):
            connection.execute(text(
                "INSERT INTO members VALUES "
                "(:id, '测试会员', NULL, 'active', NULL, :created, :created)"
            ), {"id": member_id, "created": "2026-10-20 02:00:00"})
        for coach_id in (40, 41):
            connection.execute(text(
                "INSERT INTO coaches VALUES (:id, '测试教练', NULL, 1, :created, :created)"
            ), {"id": coach_id, "created": "2026-10-20 02:00:00"})
        connection.execute(text("INSERT INTO member_account_links VALUES (3, 30)"))
        connection.execute(text("INSERT INTO coach_account_links VALUES (4, 40)"))
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def _actor(role="member"):
    identifiers = {"admin": 1, "receptionist": 2, "member": 3, "coach": 4}
    return Actor(
        account_id=identifiers[role], role=role,
        member_id=30 if role == "member" else None,
        coach_id=40 if role == "coach" else None,
    )


def _auth():
    return AuthService(log_config=LogConfig())


@pytest.mark.parametrize("role", ["admin", "receptionist", "member", "coach"])
def test_valid_current_identity_is_returned_from_database(actor_db, role):
    actor = _actor(role)
    assert _auth().verify_actor(actor_db, actor) == actor
    assert actor_db.in_transaction()


def test_repository_reads_current_account_and_full_linked_profile(actor_db):
    repository = AccountRepository(actor_db)
    account = repository.lock(3)
    member, coach = repository.lock_profile_links(3)
    assert account.id == 3 and account.role == "member" and account.is_active
    assert account.created_at.tzinfo == timezone.utc
    assert member.id == 30 and member.name == "测试会员" and member.phone is None
    assert member.created_at.tzinfo == timezone.utc
    assert coach is None
    assert repository.lock(999) is None


@pytest.mark.parametrize("table", ["accounts", "member_account_links", "coach_account_links"])
def test_database_lock_failure_returns_safe_storage_error(actor_db, table):
    """真实 SQL 在账号或档案关联缺表时失败，服务统一异常且保留调用方事务。"""
    actor_db.execute(text(f"DROP TABLE {table}"))
    actor_db.commit()

    with pytest.raises(StorageError) as caught:
        _auth().verify_actor(actor_db, _actor())

    assert str(caught.value) == "复核当前登录身份失败"
    assert isinstance(caught.value.__cause__, SQLAlchemyError)
    assert table in str(caught.value.__cause__)
    assert actor_db.in_transaction()


@pytest.mark.parametrize("role", ["admin", "receptionist", "member", "coach"])
def test_committed_account_deactivation_invalidates_existing_actor(actor_db, role):
    actor = _actor(role)
    assert _auth().verify_actor(actor_db, actor) == actor
    actor_db.execute(text("UPDATE accounts SET is_active = 0 WHERE id = :id"), {"id": actor.account_id})
    actor_db.commit()
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, actor)


def test_committed_role_change_invalidates_old_role(actor_db):
    actor_db.execute(text("UPDATE accounts SET role = 'receptionist' WHERE id = 1"))
    actor_db.commit()
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, _actor("admin"))
    assert _auth().verify_actor(actor_db, replace(_actor("admin"), role="receptionist")).role == "receptionist"


@pytest.mark.parametrize(
    "role, table, field, new_id",
    [("member", "member_account_links", "member_id", 31), ("coach", "coach_account_links", "coach_id", 41)],
)
def test_profile_transfer_rejects_stale_actor_and_accepts_current_link(actor_db, role, table, field, new_id):
    actor = _actor(role)
    assert _auth().verify_actor(actor_db, actor) == actor
    actor_db.execute(text(f"UPDATE {table} SET {field} = :new_id"), {"new_id": new_id})
    actor_db.commit()
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, actor)
    current = replace(actor, **{field: new_id})
    assert _auth().verify_actor(actor_db, current) == current


@pytest.mark.parametrize("role", ["admin", "receptionist"])
@pytest.mark.parametrize("table, profile_id", [("member_account_links", 31), ("coach_account_links", 41)])
def test_staff_with_rogue_profile_link_is_rejected(actor_db, role, table, profile_id):
    actor = _actor(role)
    actor_db.execute(text(f"INSERT INTO {table} VALUES (:account_id, :profile_id)"), {
        "account_id": actor.account_id, "profile_id": profile_id,
    })
    actor_db.commit()
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, actor)


def test_disabled_coach_cannot_keep_using_existing_actor(actor_db):
    actor_db.execute(text("UPDATE coaches SET is_active = 0 WHERE id = 40"))
    actor_db.commit()
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, _actor("coach"))


@pytest.mark.parametrize(
    "role, table, profile_id",
    [("member", "coach_account_links", 41), ("coach", "member_account_links", 31)],
)
def test_profile_role_with_both_link_kinds_is_rejected(actor_db, role, table, profile_id):
    actor = _actor(role)
    actor_db.execute(text(f"INSERT INTO {table} VALUES (:account_id, :profile_id)"), {
        "account_id": actor.account_id, "profile_id": profile_id,
    })
    actor_db.commit()
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, actor)


def test_archived_member_can_still_read_their_existing_profile(actor_db):
    actor_db.execute(text(
        "UPDATE members SET status = 'archived', archived_at = '2026-10-21 02:00:00' WHERE id = 30"
    ))
    actor_db.commit()
    actor = _actor("member")
    assert _auth().verify_actor(actor_db, actor) == actor
    member, coach = AccountRepository(actor_db).lock_profile_links(actor.account_id)
    assert member.status == "archived" and member.archived_at.tzinfo == timezone.utc
    assert coach is None


@pytest.mark.parametrize("role, table", [("member", "member_account_links"), ("coach", "coach_account_links")])
def test_missing_required_profile_link_invalidates_identity(actor_db, role, table):
    actor_db.execute(text(f"DELETE FROM {table}"))
    actor_db.commit()
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, _actor(role))


@pytest.mark.parametrize(
    "actor",
    [
        None,
        {"account_id": 3, "role": "member", "member_id": 30},
        replace(_actor(), account_id=True),
        replace(_actor(), account_id="3"),
        replace(_actor(), account_id=0),
        replace(_actor(), account_id=-1),
        replace(_actor(), account_id=2**63),
        replace(_actor(), account_id=3.0),
        replace(_actor(), member_id=True),
        replace(_actor(), member_id=0),
        replace(_actor(), member_id=-30),
        replace(_actor(), member_id="30"),
        replace(_actor(), member_id=2**63),
        replace(_actor("coach"), coach_id=True),
        replace(_actor("coach"), coach_id=0),
        replace(_actor("coach"), coach_id="40"),
        replace(_actor(), role="owner"),
        replace(_actor(), member_id=None),
        replace(_actor(), coach_id=40),
    ],
)
def test_malformed_or_inconsistent_actor_is_rejected(actor_db, actor):
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, actor)


def test_missing_account_invalidates_actor(actor_db):
    with pytest.raises(AuthenticationError):
        _auth().verify_actor(actor_db, replace(_actor(), account_id=999))


def test_bigint_upper_bound_is_a_valid_account_id(actor_db):
    maximum = 2**63 - 1
    actor_db.execute(text("UPDATE accounts SET id = :id WHERE id = 1"), {"id": maximum})
    actor_db.commit()
    actor = replace(_actor("admin"), account_id=maximum)
    assert _auth().verify_actor(actor_db, actor) == actor
