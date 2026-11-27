"""AUTH-04/AUTH-07：MySQL 8.4 下的关联并发、管理员停用、锁定范围与回滚。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import LogConfig
from src.db.account_repo import AccountRepository
from src.db.connection import transaction
from src.errors import AuthenticationError, InvalidState, StorageError
from src.logic.auth_logic import AuthLogic
from src.models.contracts import Actor, MemberAccountLinkInput
from src.services.auth_service import AuthService

ADMIN_1 = Actor(account_id=1, role="admin", member_id=None, coach_id=None)
ADMIN_2 = Actor(account_id=2, role="admin", member_id=None, coach_id=None)


@pytest.fixture
def auth_engine(initialized_mysql_database):
    """预置两名管理员、两个会员账号和三个会员档案；每个用例重新装载。"""
    with initialized_mysql_database.begin() as connection:
        connection.execute(text(
            "INSERT INTO accounts (id, username, password_hash, role, is_active) VALUES "
            "(1, 'auth_admin1', 'unused', 'admin', 1), "
            "(2, 'auth_admin2', 'unused', 'admin', 1), "
            "(3, 'auth_member1', 'unused', 'member', 1), "
            "(4, 'auth_member2', 'unused', 'member', 1)"
        ))
        connection.execute(text(
            "INSERT INTO members (id, name) VALUES (10, 'M1'), (11, 'M2'), (12, 'M3')"
        ))
    return initialized_mysql_database


def _factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_two_admins_link_different_members_without_gap_lock_deadlock(auth_engine):
    """两位管理员停在各自 INSERT 之前同时放行；两笔关联都成功。"""
    engine = auth_engine
    barrier = Barrier(2)
    service = AuthService(log_config=LogConfig())
    factory = _factory(engine)

    def pause_before_insert(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.split()).upper()
        if normalized.startswith("INSERT INTO MEMBER_ACCOUNT_LINKS"):
            barrier.wait(timeout=10)

    def link(actor: Actor, account_id: int, member_id: int):
        with factory() as session, transaction(session):
            return service.link_member(
                session, actor,
                MemberAccountLinkInput(account_id=account_id, member_id=member_id),
            )

    event.listen(engine, "before_cursor_execute", pause_before_insert)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(link, ADMIN_1, 3, 10), pool.submit(link, ADMIN_2, 4, 11)]
            results = [future.result(timeout=30) for future in futures]
    finally:
        event.remove(engine, "before_cursor_execute", pause_before_insert)

    assert sorted((view.id, view.member_id) for view in results) == [(3, 10), (4, 11)]


def test_concurrent_deactivation_keeps_at_least_one_active_admin(auth_engine):
    """两名管理员互相停用；按编号升序锁定后只有一方成功，系统仍保留管理员。

    同步点放在账号锁定读之前：两笔事务都先进入等待，再同时发出锁定读。
    正确实现下后到的一方要等先到者提交，因此另一方的账号此时已被停用；
    若锁定读没有串行化，两方都可能通过复核并各自停用对方。
    """
    engine = auth_engine
    barrier = Barrier(2)
    service = AuthService(log_config=LogConfig())
    factory = _factory(engine)

    def pause_before_account_lock(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.split()).upper()
        if normalized.startswith("SELECT * FROM ACCOUNTS"):
            barrier.wait(timeout=10)

    def deactivate(actor: Actor, target: int):
        with factory() as session, transaction(session):
            return service.set_account_active(session, actor, target, False)

    def run(actor: Actor, target: int):
        try:
            deactivate(actor, target)
        except (InvalidState, AuthenticationError) as exc:
            return type(exc).__name__
        return "success"

    event.listen(engine, "before_cursor_execute", pause_before_account_lock)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, ADMIN_1, 2), pool.submit(run, ADMIN_2, 1)]
            outcomes = [future.result(timeout=30) for future in futures]
    finally:
        event.remove(engine, "before_cursor_execute", pause_before_account_lock)

    assert sorted(outcomes) == ["AuthenticationError", "success"]
    with engine.connect() as connection:
        active = connection.scalar(text(
            "SELECT COUNT(*) FROM accounts WHERE role = 'admin' AND is_active = 1"
        ))
    assert active == 1


def test_lock_helpers_use_ordered_locking_reads_with_expected_scope(auth_engine):
    """lock_many 与 lock_active_admins 使用 FOR UPDATE 并按编号排序。"""
    engine = auth_engine
    statements: list[str] = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.split())
        if "FOR UPDATE" in normalized.upper():
            statements.append(normalized)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        with Session(engine) as session:
            admins = AccountRepository(session).lock_active_admins((1,))
            assert {row.id for row in admins} == {1, 2}
            ordered = AccountRepository(session).lock_many((4, 2))
            assert [row.id for row in ordered] == [2, 4]
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert len(statements) == 2
    assert "role = 'admin'" in statements[0]
    assert statements[0].startswith("SELECT * FROM accounts WHERE")
    assert statements[0].endswith("ORDER BY id FOR UPDATE")
    # 第二条必须来自 lock_many：按账号主键 IN 过滤并升序锁定，
    # 不能由 lock_active_admins 的语句顶替。
    assert statements[1].startswith("SELECT * FROM accounts WHERE id IN (")
    assert statements[1].endswith("ORDER BY id FOR UPDATE")


def test_failed_relink_rolls_back_released_old_link(auth_engine, monkeypatch):
    """移交写入失败时，事务回滚，原关联仍然存在。"""
    engine = auth_engine
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO member_account_links (account_id, member_id, linked_at, linked_by) "
            "VALUES (3, 10, '2026-11-01 10:00:00', 1)"
        ))
    logic = AuthLogic(_factory(engine), AuthService(log_config=LogConfig()))

    def fail(*args, **kwargs):
        raise StorageError("关联会员档案失败")

    deleted: list[int] = []
    original_delete = AccountRepository.delete_member_link

    def record_delete(self, account_id):
        deleted.append(account_id)
        return original_delete(self, account_id)

    monkeypatch.setattr(AccountRepository, "create_member_link", fail)
    monkeypatch.setattr(AccountRepository, "delete_member_link", record_delete)
    # 只接受注入点抛出的 StorageError：前置步骤若失败，消息不同，本行不通过。
    with pytest.raises(StorageError, match="关联会员档案失败"):
        logic.relink_member(ADMIN_1, 3, 11)

    # 流程必须真正执行过“删除旧关联”，才能证明写入失败后旧关联被回滚保留。
    assert deleted == [3]
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT member_id FROM member_account_links WHERE account_id = 3"
        )) == 10
        assert connection.scalar(text("SELECT COUNT(*) FROM member_account_links")) == 1
