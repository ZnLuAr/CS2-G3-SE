"""AUTH-06：MySQL 下发账号关键字查询使用 LOCATE 分支。"""

from __future__ import annotations

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import sessionmaker

from src.config import LogConfig
from src.models.contracts import Actor, NamedQuery
from src.services.auth_service import AuthService

ADMIN = Actor(account_id=1, role="admin", member_id=None, coach_id=None)


@pytest.fixture
def accounts_engine(initialized_mysql_database):
    """预置一名管理员和两名会员账号，用于关键字筛选。"""
    with initialized_mysql_database.begin() as connection:
        connection.execute(text(
            "INSERT INTO accounts (id, username, password_hash, role, is_active) VALUES "
            "(1, 'loc_admin', 'unused', 'admin', 1), "
            "(2, 'loc_member_a', 'unused', 'member', 1), "
            "(3, 'loc_member_b', 'unused', 'member', 0)"
        ))
    return initialized_mysql_database


def test_list_accounts_keyword_uses_mysql_locate(accounts_engine):
    """关键字筛选在 MySQL 上走 LOCATE，并只返回匹配的账号。"""
    statements: list[str] = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.split())
        if "LOCATE(" in normalized.upper():
            statements.append(normalized)

    service = AuthService(log_config=LogConfig())
    factory = sessionmaker(bind=accounts_engine, expire_on_commit=False)
    event.listen(accounts_engine, "before_cursor_execute", capture)
    try:
        with factory() as session:
            page = service.list_accounts(
                session, ADMIN, NamedQuery(keyword="loc_member"),
            )
    finally:
        event.remove(accounts_engine, "before_cursor_execute", capture)

    assert [item.id for item in page.items] == [2, 3]
    assert page.total == 2
    assert statements, "账号列表查询没有走 LOCATE 分支"

    with factory() as session:
        single = service.list_accounts(
            session, ADMIN, NamedQuery(keyword="member_a"),
        )
    assert [item.id for item in single.items] == [2]
