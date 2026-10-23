"""核对课程/预约 MySQL 建表片段与 SQLAlchemy Core 表定义是否同步。

只做静态检查：不连接 MySQL，不能代替真实建表、约束和事务验证。
"""

from __future__ import annotations

import re
from pathlib import Path

from src.db.tables import metadata

SQL_FILE = Path(__file__).resolve().parents[2] / "sql" / "course_booking.sql"
MODULE_TABLES = {
    "coaches",
    "courses",
    "rooms",
    "course_sessions",
    "bookings",
    "operation_records",
}


def _sql_tables() -> dict[str, str]:
    """提取 SQL 文件中的表名和表体。"""
    text = SQL_FILE.read_text(encoding="utf-8")
    return dict(re.findall(r"CREATE TABLE (\w+) \((.*?)\) ENGINE=InnoDB", text, re.S))


def _sql_columns(body: str) -> set[str]:
    """提取列名，跳过 KEY、CONSTRAINT 等表级定义。"""
    body = re.sub(r"--[^\n]*", "", body)
    pattern = (
        r"(?:^|,)\s*(\w+)\s+"
        r"(BIGINT|INT|BOOLEAN|VARCHAR\(\d+\)|CHAR\(\d+\)|"
        r"DECIMAL\(\d+,\d+\)|DATETIME\(6\)|DATE)(?=\s|,|$)"
    )
    return {match[1] for match in re.finditer(pattern, body)}


def test_sql_fragment_matches_core_tables() -> None:
    """片段中的表、列与代码定义一致，避免只改其中一边。"""
    tables = _sql_tables()
    assert set(tables) == MODULE_TABLES
    for name in MODULE_TABLES:
        assert _sql_columns(tables[name]) == set(metadata.tables[name].columns.keys()), name


def test_sql_fragment_keeps_business_checks() -> None:
    """固定课程类型、时长、容量、课次时间和状态约束不能被删掉。"""
    text = SQL_FILE.read_text(encoding="utf-8")
    for fragment in [
        "CHECK (kind = 'private')",
        "CHECK (duration_minutes BETWEEN 1 AND 150)",
        "CHECK (capacity > 0)",
        "CHECK (ends_at > starts_at)",
        "CHECK (status IN ('scheduled', 'completed', 'cancelled'))",
        "CHECK (status IN ('reserved', 'cancelled', 'checked_in', 'completed', 'no_show'))",
        "UNIQUE (member_id, session_id)",
        "UNIQUE (request_id)",
    ]:
        assert fragment in text, fragment
