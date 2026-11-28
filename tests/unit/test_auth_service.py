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
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
    ResourceError,
)
from src.models.contracts import (
    AccountInput,
    CoachAccountLinkInput,
    LogQuery,
    MemberAccountLinkInput,
    NamedQuery,
    PageRequest,
)
from src.security import passwords
from src.security.passwords import hash_password
from src.services import auth_service
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
    # 状态筛选与分页独立生效：停用两个会员账号后启用筛选只剩四个；每页 2 条时按编号升序切分。
    db.execute(text("UPDATE accounts SET is_active = 0 WHERE id IN (3, 5)"))
    active = _service().list_accounts(db, admin, NamedQuery(is_active=True))
    assert [item.id for item in active.items] == [1, 2, 4, 6] and active.total == 4
    page2 = _service().list_accounts(db, admin, NamedQuery(paging=PageRequest(page=2, page_size=2)))
    assert [item.id for item in page2.items] == [3, 4] and page2.total == 6


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


def _assert_rejected_after_one_hash(monkeypatch, service, db, username, password):
    """登录被拒且恰好执行一次 Argon2 校验：所有失败分支响应时间一致。"""
    calls = []
    real_verify = auth_service.verify_password

    def counting_verify(password, password_hash):
        calls.append(password)
        return real_verify(password, password_hash)

    monkeypatch.setattr(auth_service, "verify_password", counting_verify)
    with pytest.raises(AuthenticationError):
        service.login(db, username, password)
    assert len(calls) == 1


def test_login_rejects_inactive_account_and_profile_mismatches(db, monkeypatch):
    """账号停用、档案停用或关联形状不符时都抛 AuthenticationError，且都先跑一次密码校验。

    每个拒绝分支都必须在 Argon2 之后返回：若某个分支提前返回，响应时间会比
    密码错误分支短，可据此判断账号状态。 AuthService 直接绑定 verify_password，
    所以计数器要打在 auth_service 模块上。
    """
    service = _service()
    db.execute(text("UPDATE accounts SET is_active = 0 WHERE id = 1"))
    _assert_rejected_after_one_hash(monkeypatch, service, db, "admin_1", "admin_1")
    db.execute(text("UPDATE accounts SET is_active = 1 WHERE id = 1"))

    # 教练账号关联的教练档案停用后不能登录。
    db.execute(text("UPDATE coaches SET is_active = 0 WHERE id = 20"))
    _assert_rejected_after_one_hash(monkeypatch, service, db, "coach_1", "coach_1")
    db.execute(text("UPDATE coaches SET is_active = 1 WHERE id = 20"))

    # 会员账号同时带教练关联：身份不变量被破坏。
    db.execute(text(
        "INSERT INTO coach_account_links VALUES (3, 22, :now, 1)"
    ), {"now": datetime.now(timezone.utc)})
    _assert_rejected_after_one_hash(monkeypatch, service, db, "member_1", "member_1")
    db.execute(text("DELETE FROM coach_account_links WHERE account_id = 3"))

    # 教练账号没有关联档案。
    db.execute(text("DELETE FROM coach_account_links WHERE account_id = 4"))
    _assert_rejected_after_one_hash(monkeypatch, service, db, "coach_1", "coach_1")
    db.execute(text(
        "INSERT INTO coach_account_links VALUES (4, 20, :now, 1)"
    ), {"now": datetime.now(timezone.utc)})

    # 未知角色不能按管理员放行。
    db.execute(text("UPDATE accounts SET role = 'owner' WHERE id = 1"))
    _assert_rejected_after_one_hash(monkeypatch, service, db, "admin_1", "admin_1")


def test_unknown_username_still_runs_password_hashing(db, monkeypatch):
    """账号不存在时也执行一次哈希校验，响应时间不随账号是否存在而变化。"""
    calls = []
    real_verify = passwords.verify_password

    def counting_verify(password, password_hash):
        calls.append(password_hash)
        return real_verify(password, password_hash)

    monkeypatch.setattr(passwords, "verify_password", counting_verify)
    with pytest.raises(AuthenticationError):
        _service().login(db, "nobody_here", "whatever_1")
    assert len(calls) == 1


def test_dummy_hash_is_prepared_before_login_requests(db, monkeypatch):
    """占位哈希在 AuthService 构造时生成；请求路径内只校验、不生成哈希。

    若留到请求内惰性生成，进程内第一个账号不存在的请求会多一次 Argon2 运算，
    耗时仍可与其他请求区分。
    """
    monkeypatch.setattr(passwords, "_DUMMY_HASH", None)
    service = _service()
    assert passwords._DUMMY_HASH is not None

    hashes: list[str] = []
    real_hash = passwords.hash_password

    def counting_hash(password):
        hashes.append(password)
        return real_hash(password)

    monkeypatch.setattr(passwords, "hash_password", counting_hash)
    with pytest.raises(AuthenticationError):
        service.login(db, "nobody_here", "whatever_1")
    with pytest.raises(AuthenticationError):
        service.login(db, "nobody_here_2", "whatever_1")
    assert hashes == []


def test_verify_against_dummy_requires_preparation(monkeypatch):
    """未预热时 verify_against_dummy 抛 ResourceError，而不是在请求内生成哈希。"""
    monkeypatch.setattr(passwords, "_DUMMY_HASH", None)
    with pytest.raises(ResourceError):
        passwords.verify_against_dummy("whatever_1")


def test_link_rejects_account_with_wrong_role(db):
    """会员档案只能关联会员账号，教练档案只能关联教练账号。"""
    admin = _service().login(db, "admin_1", "admin_1")
    with pytest.raises(InvalidState):
        _service().link_member(
            db, admin, MemberAccountLinkInput(account_id=1, member_id=11),
        )
    with pytest.raises(InvalidState):
        _service().link_coach(
            db, admin, CoachAccountLinkInput(account_id=3, coach_id=22),
        )


def test_repeating_same_relink_after_deactivation_returns_current_result(db):
    """对已停用教练重复提交相同移交仍返回当前结果，与 link_coach 一致。"""
    admin = _service().login(db, "admin_1", "admin_1")
    db.execute(text("UPDATE coaches SET is_active = 0 WHERE id = 20"))
    view = _service().relink_coach(db, admin, 4, 20)
    assert view.coach_id == 20
    # 换成另一名停用教练才是新的关联，应当拒绝。
    with pytest.raises(InvalidState, match="教练档案已停用"):
        _service().relink_coach(db, admin, 4, 21)


def test_log_query_denies_non_admin(db, tmp_path):
    """open_log_snapshot 与 query_logs 都只允许管理员。"""
    (tmp_path / "app.log").write_text("", encoding="utf-8")
    service = AuthService(log_config=LogConfig(directory=tmp_path))
    member = service.login(db, "member_1", "member_1")
    with pytest.raises(PermissionDenied):
        service.open_log_snapshot(db, member)
    admin = service.login(db, "admin_1", "admin_1")
    snapshot = service.open_log_snapshot(db, admin)
    with pytest.raises(PermissionDenied):
        service.query_logs(db, member, LogQuery(), snapshot=snapshot)


@pytest.mark.parametrize(
    ("call", "error"),
    [
        pytest.param(lambda s, a, db: s.create_account(
            db, a, AccountInput(username="role_x", password="secret_1", role="owner"),
        ), InvalidInputError, id="create-role"),
        pytest.param(lambda s, a, db: s.set_account_active(db, a, 5, "yes"), InvalidInputError, id="active-type"),
        pytest.param(lambda s, a, db: s.get_account(db, a, True), InvalidInputError, id="id-bool"),
        pytest.param(lambda s, a, db: s.get_account(db, a, 999), NotFoundError, id="account-missing"),
        pytest.param(lambda s, a, db: s.set_account_active(db, a, 999, False), NotFoundError, id="target-missing"),
        pytest.param(lambda s, a, db: s.link_member(
            db, a, MemberAccountLinkInput(account_id=5, member_id=999),
        ), NotFoundError, id="member-missing"),
        pytest.param(lambda s, a, db: s.link_coach(
            db, a, CoachAccountLinkInput(account_id=6, coach_id=999),
        ), NotFoundError, id="coach-missing"),
        pytest.param(lambda s, a, db: s.relink_member(db, a, 5, 999), NotFoundError, id="relink-member-missing"),
        pytest.param(lambda s, a, db: s.relink_coach(db, a, 6, 999), NotFoundError, id="relink-coach-missing"),
    ],
)
def test_service_rejects_invalid_inputs_and_missing_records(db, call, error):
    """输入校验分支与 NotFoundError 分支按合同 9.2 抛出对应异常。"""
    admin = _service().login(db, "admin_1", "admin_1")
    with pytest.raises(error):
        call(_service(), admin, db)
