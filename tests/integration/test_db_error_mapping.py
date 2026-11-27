"""MEM-01 / TEST-06：在真实 MySQL 上固定完整性错误在驱动下的异常类别。

建档重试只认唯一键重复（错误码 1062，合同 12.7.3）：它必须是 IntegrityError。
外键失败同属 IntegrityError 但错误码不同，CHECK 违反不属于 IntegrityError，
两者都不会被误当作并发同编号而重试。驱动升级改变映射时由这些用例发现。
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


INSERT_ACCOUNT = text(
    "INSERT INTO accounts (id, username, password_hash, role) "
    "VALUES (:id, 'mapping_user', 'test-unused', 'member')"
)
INSERT_OPERATION = text(
    "INSERT INTO operation_records (request_id, actor_id, operation, payload_hash, result_id) "
    "VALUES ('6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11', :actor_id, 'create_member', :payload_hash, 1)"
)


def test_duplicate_key_is_integrity_error_1062(initialized_mysql_database):
    engine = initialized_mysql_database
    with engine.begin() as connection:
        connection.execute(INSERT_ACCOUNT, {"id": 1})
    with pytest.raises(IntegrityError) as info:
        with engine.begin() as connection:
            connection.execute(INSERT_ACCOUNT, {"id": 2})
    assert info.value.orig.args[0] == 1062


def test_foreign_key_failure_is_integrity_error_with_other_code(initialized_mysql_database):
    engine = initialized_mysql_database
    with pytest.raises(IntegrityError) as info:
        with engine.begin() as connection:
            connection.execute(INSERT_OPERATION, {"actor_id": 999_999, "payload_hash": "0" * 64})
    assert info.value.orig.args[0] == 1452


def test_check_violation_is_not_integrity_error(initialized_mysql_database):
    engine = initialized_mysql_database
    with pytest.raises(SQLAlchemyError) as info:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO members (name, status) VALUES ('Mapping', 'unknown')"))
    assert not isinstance(info.value, IntegrityError)
    assert info.value.orig.args[0] == 3819
