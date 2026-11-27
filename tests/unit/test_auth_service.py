from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.config import LogConfig
from src.db.account_repo import AccountRepository
from src.errors.business import (
    AuthenticationError,
    ConflictError,
    InvalidState,
    PermissionDenied,
)
from src.models.contracts import (
    AccountInput,
    Actor,
    CoachAccountLinkInput,
    LogQuery,
    MemberAccountLinkInput,
    NamedQuery,
)
from src.security.passwords import hash_password
from src.services.auth_service import AuthService


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username TEXT UNIQUE, password_hash TEXT, role TEXT, is_active INTEGER, "
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, status TEXT, "
            "archived_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE coaches (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, is_active INTEGER, "
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE member_account_links (account_id INTEGER PRIMARY KEY, "
            "member_id INTEGER UNIQUE, linked_at DATETIME, linked_by INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE coach_account_links (account_id INTEGER PRIMARY KEY, "
            "coach_id INTEGER UNIQUE, linked_at DATETIME, linked_by INTEGER)"
        )
        connection.execute(text(
            "INSERT INTO accounts (id, username, password_hash, role, is_active) VALUES "
            "(1, 'admin_1', :admin, 'admin', 1), "
            "(2, 'admin_2', :admin, 'admin', 1), "
            "(3, 'member_1', :member, 'member', 1), "
            "(4, 'coach_1', :coach, 'coach', 1), "
            "(5, 'member_2', :member, 'member', 1), "
            "(6, 'coach_2', :coach, 'coach', 1)"
        ), {
            "admin": hash_password("admin_1"),
            "member": hash_password("member_1"),
            "coach": hash_password("coach_1"),
        })
        connection.execute(text(
            "INSERT INTO members (id, name, phone, status) VALUES "
            "(10, '会员甲', NULL, 'active'), (11, '会员乙', NULL, 'archived')"
        ))
        connection.execute(text(
            "INSERT INTO coaches (id, name, phone, is_active) VALUES "
            "(20, '教练甲', NULL, 1), (21, '教练乙', NULL, 0), (22, '教练丙', NULL, 1)"
        ))
        connection.execute(text(
            "INSERT INTO member_account_links VALUES (3, 10, :now, 1)"
        ), {"now": datetime.now(timezone.utc)})
        connection.execute(text(
            "INSERT INTO coach_account_links VALUES (4, 20, :now, 1)"
        ), {"now": datetime.now(timezone.utc)})
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def _service() -> AuthService:
    return AuthService(log_config=LogConfig())


def test_login_roles_and_failures(db):
    admin = _service().login(db, "ADMIN_1", "admin_1")
    assert admin.role == "admin" and admin.member_id is None
    member = _service().login(db, "member_1 ", "member_1")
    assert member.role == "member" and member.member_id == 10
    with pytest.raises(AuthenticationError):
        _service().login(db, "admin_1", "wrong_1")
    with pytest.raises(AuthenticationError):
        _service().login(db, "admin_1", " admin_1 ")


def test_create_account_hashes_and_rejects_duplicate(db):
    admin = _service().login(db, "admin_1", "admin_1")
    view = _service().create_account(
        db, admin, AccountInput(username=" New_User ", password="secret_1", role="receptionist"),
    )
    assert view.username == "new_user" and view.is_active
    stored = db.execute(
        text("SELECT password_hash FROM accounts WHERE id = :id"), {"id": view.id},
    ).scalar_one()
    assert stored != "secret_1"
    with pytest.raises(ConflictError):
        _service().create_account(
            db, admin, AccountInput(username="new_user", password="secret_1", role="member"),
        )


def test_non_admin_is_denied(db):
    member = _service().login(db, "member_1", "member_1")
    with pytest.raises(PermissionDenied):
        _service().get_account(db, member, 1)
    # 会员和教练有合法档案关联，调用管理员写操作仍应报权限不足，
    # 不能误报成身份失效而触发重新登录。
    with pytest.raises(PermissionDenied):
        _service().set_account_active(db, member, 3, False)
    with pytest.raises(PermissionDenied):
        _service().link_member(
            db, member, MemberAccountLinkInput(account_id=3, member_id=10),
        )


def test_active_admin_lock_does_not_include_member_accounts(db):
    rows = AccountRepository(db).lock_active_admins((1, 2))
    assert {row.id for row in rows} == {1, 2}
    assert all(row.role == "admin" for row in rows)


def test_last_active_admin_cannot_be_deactivated(db):
    admin = _service().login(db, "admin_1", "admin_1")
    _service().set_account_active(db, admin, 2, False)
    with pytest.raises(InvalidState):
        _service().set_account_active(db, admin, 1, False)


def test_link_member_is_idempotent_and_conflicts(db):
    admin = _service().login(db, "admin_1", "admin_1")
    first = _service().link_member(
        db, admin, MemberAccountLinkInput(account_id=3, member_id=10),
    )
    assert first.member_id == 10
    again = _service().link_member(
        db, admin, MemberAccountLinkInput(account_id=3, member_id=10),
    )
    assert again.member_id == 10
    with pytest.raises(ConflictError):
        _service().link_member(
            db, admin, MemberAccountLinkInput(account_id=3, member_id=11),
        )


def test_repeating_same_coach_link_after_deactivation_returns_current_result(db):
    """重复关联已停用教练仍返回当前结果；新关联才拒绝停用档案。"""
    admin = _service().login(db, "admin_1", "admin_1")
    first = _service().link_coach(
        db, admin, CoachAccountLinkInput(account_id=4, coach_id=20),
    )
    assert first.coach_id == 20
    db.execute(text("UPDATE coaches SET is_active = 0 WHERE id = 20"))
    again = _service().link_coach(
        db, admin, CoachAccountLinkInput(account_id=4, coach_id=20),
    )
    assert again.coach_id == 20
    with pytest.raises(InvalidState, match="教练档案已停用"):
        _service().link_coach(
            db, admin, CoachAccountLinkInput(account_id=6, coach_id=20),
        )


def test_relink_member_releases_old_link(db):
    admin = _service().login(db, "admin_1", "admin_1")
    view = _service().relink_member(db, admin, 3, 11)
    assert view.member_id == 11
    rows = db.execute(text(
        "SELECT member_id FROM member_account_links WHERE account_id = 3"
    )).scalars().all()
    assert rows == [11]


def test_relink_coach_releases_old_link_and_rejects_inactive_target(db):
    admin = _service().login(db, "admin_1", "admin_1")
    with pytest.raises(InvalidState, match="教练档案已停用"):
        _service().relink_coach(db, admin, 4, 21)
    view = _service().relink_coach(db, admin, 4, 22)
    assert view.coach_id == 22
    assert db.execute(text(
        "SELECT coach_id FROM coach_account_links WHERE account_id = 4"
    )).scalar_one() == 22


def test_relink_rejects_profile_owned_by_another_account(db):
    admin = _service().login(db, "admin_1", "admin_1")
    with pytest.raises(ConflictError):
        _service().relink_member(db, admin, 5, 10)


def test_deactivate_and_activate_return_views(db):
    admin = _service().login(db, "admin_1", "admin_1")
    stopped = _service().set_account_active(db, admin, 5, False)
    assert not stopped.is_active
    resumed = _service().set_account_active(db, admin, 5, True)
    assert resumed.is_active


def test_list_accounts_filters_by_keyword_and_state(db):
    admin = _service().login(db, "admin_1", "admin_1")
    members = _service().list_accounts(db, admin, NamedQuery(keyword=" member "))
    assert [item.id for item in members.items] == [3, 5]
    admins = _service().list_accounts(db, admin, NamedQuery(keyword="admin"))
    assert [item.id for item in admins.items] == [1, 2]


def test_first_coach_link_creates_link_and_repeat_returns_current_result(db):
    """未关联的教练账号首次关联走创建分支；重复提交返回当前结果。"""
    admin = _service().login(db, "admin_1", "admin_1")
    first = _service().link_coach(
        db, admin, CoachAccountLinkInput(account_id=6, coach_id=22),
    )
    assert first.coach_id == 22
    assert db.execute(text(
        "SELECT coach_id FROM coach_account_links WHERE account_id = 6"
    )).scalar_one() == 22
    again = _service().link_coach(
        db, admin, CoachAccountLinkInput(account_id=6, coach_id=22),
    )
    assert again.coach_id == 22
    assert db.execute(text(
        "SELECT COUNT(*) FROM coach_account_links WHERE account_id = 6"
    )).scalar_one() == 1


def test_log_snapshot_and_query_use_the_same_fixed_snapshot(db, tmp_path):
    """管理员打开快照后按条件查询，查询只读取该快照。"""
    (tmp_path / "app.log").write_text(
        json.dumps({
            "timestamp": "2026-11-27T01:00:00+00:00",
            "level": "INFO",
            "operation": "account.create",
            "outcome": "success",
            "actor_id": 1,
            "result_id": 7,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    service = AuthService(log_config=LogConfig(directory=tmp_path))
    admin = service.login(db, "admin_1", "admin_1")
    snapshot = service.open_log_snapshot(db, admin)
    assert len(snapshot.entries) == 1

    page = service.query_logs(
        db, admin, LogQuery(operation="account.create"), snapshot=snapshot,
    )
    assert page.total == 1
    assert page.items[0].actor_id == 1
    assert page.items[0].result_id == 7


def test_transferred_profile_invalidates_admin_operations_for_stale_actor(db):
    """档案移交后的旧身份在详情和写操作中统一抛 AuthenticationError。"""
    member = _service().login(db, "member_1", "member_1")
    db.execute(text("UPDATE member_account_links SET member_id = 11 WHERE account_id = 3"))
    with pytest.raises(AuthenticationError):
        _service().get_account(db, member, 1)
    with pytest.raises(AuthenticationError):
        _service().set_account_active(db, member, 5, False)
