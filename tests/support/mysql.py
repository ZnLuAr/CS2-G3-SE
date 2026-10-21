"""MySQL fixture：只允许统一入口申请的独立测试库。"""
from __future__ import annotations

import os

import pytest


EXPECTED_TABLES = (
    "schema_versions", "accounts", "members", "coaches",
    "member_account_links", "coach_account_links",
    "courses", "course_tags", "rooms", "course_sessions", "notifications",
    "equipment", "maintenance_records", "body_measurements", "operation_records",
    "gym_card_products", "duration_gym_card_products", "visit_gym_card_products",
    "lesson_package_products", "lesson_package_gift_rules",
    "sale_orders", "sale_items", "gym_card_sale_items", "lesson_package_sale_items",
    "payments", "gift_grants",
    "gym_cards", "duration_gym_cards", "visit_gym_cards", "lesson_packages",
    "bookings", "consumption_records", "waitlist_entries", "gym_entries", "reviews",
)
REVERSE_TABLES = tuple(reversed(EXPECTED_TABLES[1:]))


def _require_mysql_mode():
    if os.environ.get("GYM_TEST_MODE") not in {"mysql", "all"}:
        pytest.fail("MySQL fixture 只能由 python -m src.cmd.test mysql/all 显式申请")
    path = os.environ.get("GYM_TEST_CONFIG")
    if not path:
        pytest.fail("缺少 GYM_TEST_CONFIG")
    from src.cmd.test import load_test_config
    return load_test_config(path)


@pytest.fixture(scope="session")
def test_settings():
    """读取已由测试命令指定的测试配置。"""
    return _require_mysql_mode()


@pytest.fixture(scope="session")
def mysql_engine(test_settings):
    """创建测试引擎；测试结束时释放连接池。"""
    from src.db.connection import close_engine, create_engine
    engine = create_engine(test_settings.app)
    try:
        yield engine
    finally:
        close_engine(engine)


def _assert_database_objects(connection):
    from sqlalchemy import text
    rows = list(connection.execute(text(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_type IN ('BASE TABLE','VIEW')"
        )))
    wrong_type = [row[0] for row in rows if row[1] != "BASE TABLE"]
    if wrong_type:
        raise RuntimeError(f"测试库存在视图对象：{', '.join(sorted(wrong_type))}")
    objects = {
        row[0]
        for row in rows
    }
    unknown = objects - set(EXPECTED_TABLES)
    if unknown:
        raise RuntimeError(f"测试库存在未设计对象：{', '.join(sorted(unknown))}")
    return objects


def _assert_lock_owner(connection, database: str):
    import hashlib
    from sqlalchemy import text
    if os.environ.get("GYM_TEST_MODE") not in {"mysql", "all"}:
        raise RuntimeError("测试库清理需要 mysql/all 测试模式")
    if not database or not database.endswith("_test"):
        raise RuntimeError("测试数据库名称必须以 _test 结尾")
    current_database = connection.execute(text("SELECT DATABASE()")).scalar_one()
    if current_database != database:
        raise RuntimeError("测试连接的数据库已改变")
    lock = "cs2g3:test:" + hashlib.sha256(database.encode("utf-8")).hexdigest()[:40]
    owner = connection.execute(text("SELECT IS_USED_LOCK(:name)"), {"name": lock}).scalar_one()
    expected = os.environ.get("GYM_TEST_LOCK_OWNER")
    if not expected or str(owner) != expected:
        raise RuntimeError("测试库命名锁不属于当前测试命令")


def _drop_tables(engine, *, keep_schema: bool):
    from sqlalchemy import text
    with engine.begin() as connection:
        _assert_lock_owner(connection, engine.url.database)
        objects = _assert_database_objects(connection)
        for table in REVERSE_TABLES:
            if table in objects:
                connection.execute(text(f"DROP TABLE `{table}`"))
        if not keep_schema and "schema_versions" in objects:
            connection.execute(text("DROP TABLE `schema_versions`"))


@pytest.fixture
def empty_mysql_database(mysql_engine, cli_processes):
    """提供无设计表的测试库，测试结束后保持为空。"""
    _drop_tables(mysql_engine, keep_schema=False)
    try:
        yield mysql_engine
    finally:
        cli_processes.close()
        _drop_tables(mysql_engine, keep_schema=False)


@pytest.fixture
def initialized_mysql_database(mysql_engine, cli_processes):
    """提供当前版本结构，测试结束清除业务数据并保留版本行。"""
    from src.db.connection import CURRENT_SCHEMA_VERSION, check_schema
    from src.cmd.db import init_database
    with mysql_engine.connect() as connection:
        _assert_lock_owner(connection, mysql_engine.url.database)
        objects = _assert_database_objects(connection)
    if objects:
        _drop_tables(mysql_engine, keep_schema=False)
    with mysql_engine.connect() as connection:
        init_database(connection)
    check_schema(mysql_engine, required_version=CURRENT_SCHEMA_VERSION)
    try:
        yield mysql_engine
    finally:
        cli_processes.close()
        from sqlalchemy import text
        with mysql_engine.begin() as connection:
            _assert_lock_owner(connection, mysql_engine.url.database)
            _assert_database_objects(connection)
            for table in REVERSE_TABLES:
                connection.execute(text(f"DELETE FROM `{table}`"))
