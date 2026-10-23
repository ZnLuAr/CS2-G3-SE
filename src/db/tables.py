"""课程与预约模块的 SQLAlchemy Core 表定义。

v3 生产结构在 sql/001_initial_schema.sql 中；这里只声明本模块服务需要读写的
表，供仓储在 MySQL 与测试 SQLite 上使用同一套查询。生产表的外键、生成列和
CHECK 约束仍以 SQL 脚本为准。
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Integer, MetaData,
    String, Table, UniqueConstraint, text,
)

metadata = MetaData()


def _pk() -> Column:
    """BIGINT 自增主键；SQLite 用 INTEGER 才能复用 rowid 自动编号。"""
    return Column("id", BigInteger().with_variant(Integer, "sqlite"),
                  primary_key=True, autoincrement=True)


members = Table(
    "members", metadata,
    _pk(),
    Column("name", String(100), nullable=False),
    Column("phone", String(32), nullable=True),
    Column("status", String(16), nullable=False, server_default=text("'active'")),
    Column("archived_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

coaches = Table(
    "coaches", metadata,
    _pk(),
    Column("name", String(100), nullable=False),
    Column("phone", String(32), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

coach_account_links = Table(
    "coach_account_links", metadata,
    Column("account_id", BigInteger, primary_key=True),
    Column("coach_id", BigInteger, nullable=False, unique=True),
    Column("linked_at", DateTime, nullable=False),
    Column("linked_by", BigInteger, nullable=False),
)

courses = Table(
    "courses", metadata,
    _pk(),
    Column("name", String(100), nullable=False),
    Column("description", String(1000), nullable=True),
    Column("kind", String(16), nullable=False, server_default=text("'private'")),
    Column("duration_minutes", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

rooms = Table(
    "rooms", metadata,
    _pk(),
    Column("name", String(100), nullable=False),
    Column("location", String(200), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

course_sessions = Table(
    "course_sessions", metadata,
    _pk(),
    Column("course_id", BigInteger, nullable=False),
    Column("coach_id", BigInteger, nullable=False),
    Column("room_id", BigInteger, nullable=False),
    Column("course_name", String(100), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("starts_at", DateTime, nullable=False),
    Column("ends_at", DateTime, nullable=False),
    Column("capacity", Integer, nullable=False),
    Column("status", String(16), nullable=False, server_default=text("'scheduled'")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

lesson_packages = Table(
    "lesson_packages", metadata,
    _pk(),
    Column("member_id", BigInteger, nullable=False),
    Column("product_id", BigInteger, nullable=False),
    Column("purchase_sale_item_id", BigInteger, nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("total_lessons", Integer, nullable=False),
    Column("remaining_lessons", Integer, nullable=False),
    Column("reserved_lessons", Integer, nullable=False),
    Column("valid_from", Date, nullable=False),
    Column("valid_until", Date, nullable=True),
    Column("status", String(16), nullable=False, server_default=text("'active'")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

bookings = Table(
    "bookings", metadata,
    _pk(),
    Column("member_id", BigInteger, nullable=False),
    Column("session_id", BigInteger, nullable=False),
    Column("lesson_package_id", BigInteger, nullable=False),
    Column("status", String(16), nullable=False, server_default=text("'reserved'")),
    Column("booked_at", DateTime, nullable=False),
    Column("checked_in_at", DateTime, nullable=True),
    Column("closed_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    UniqueConstraint("member_id", "session_id", name="uq_booking_member_session"),
)

operation_records = Table(
    "operation_records", metadata,
    _pk(),
    Column("request_id", String(36), nullable=False, unique=True),
    Column("actor_id", BigInteger, nullable=False),
    Column("operation", String(50), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("result_id", BigInteger, nullable=False),
    Column("created_at", DateTime, nullable=False),
)


gym_entries = Table(
    "gym_entries", metadata,
    _pk(),
    Column("member_id", BigInteger, nullable=False),
    Column("source_kind", String(24), nullable=False),
    Column("duration_gym_card_id", BigInteger, nullable=True),
    Column("visit_gym_card_id", BigInteger, nullable=True),
    Column("booking_id", BigInteger, nullable=True),
    Column("business_date", Date, nullable=False),
    Column("entered_at", DateTime, nullable=False),
    Column("operator_id", BigInteger, nullable=False),
)
