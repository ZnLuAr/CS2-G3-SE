"""课程与预约模块涉及的数据库表定义。

仓库当前用普通 dataclass 表示存储模型，还没有 ORM 映射。为了让数据访问层能在
MySQL（生产）和 SQLite（测试）上执行同一套代码，这里用 SQLAlchemy Core 显式
声明表、列、约束和索引；仓储只引用这些 Table 对象，不写拼接 SQL。

共享表说明：
- `accounts`、`members`、`memberships` 由账号和产品模块写入，本模块只读取或
  更新预约相关的 `reserved_private_lessons`；
- `coaches`、`courses`、`rooms`、`course_sessions`、`bookings`、
  `operation_records` 由本模块读写。

时间列统一保存 UTC，且不带时区，转换规则见 `src/db/support.py`。
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    text,
)

metadata = MetaData()


def _primary_key() -> Column:
    """主键列：MySQL 使用 BIGINT 自增，SQLite 使用 INTEGER 才能自增。

    SQLite 只有 `INTEGER PRIMARY KEY` 会复用 rowid 并自动编号；直接把 BIGINT
    作为主键时插入会要求显式提供 id。测试用 SQLite，生产用 MySQL，因此用
    `with_variant` 让同一份表定义在两边都按预期工作。
    """
    return Column(
        "id", BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True, autoincrement=True,
    )

# ---------------- 账号与会员（其他模块负责写入，本模块只读） ----------------

accounts = Table(
    "accounts",
    metadata,
    _primary_key(),
    Column("username", String(50), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(16), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

members = Table(
    "members",
    metadata,
    _primary_key(),
    Column("account_id", BigInteger, ForeignKey("accounts.id"), nullable=True, unique=True),
    Column("name", String(100), nullable=False),
    Column("phone", String(32), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

memberships = Table(
    "memberships",
    metadata,
    _primary_key(),
    Column("member_id", BigInteger, ForeignKey("members.id"), nullable=False),
    Column("product_id", BigInteger, nullable=False),
    Column("name", String(100), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("price", Numeric(10, 2), nullable=False),
    Column("private_lesson_credits", Integer, nullable=False),
    Column("access_uses", Integer, nullable=True),
    Column("valid_days", Integer, nullable=True),
    Column("valid_from", Date, nullable=False),
    Column("valid_until", Date, nullable=True),
    Column("remaining_accesses", Integer, nullable=True),
    Column("remaining_private_lessons", Integer, nullable=False),
    Column("reserved_private_lessons", Integer, nullable=False),
    Column("status", String(16), nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)
Index("ix_memberships_member_status", memberships.c.member_id, memberships.c.status, memberships.c.id)

# ---------------- 教练、课程模板与场地 ----------------

coaches = Table(
    "coaches",
    metadata,
    _primary_key(),
    Column("account_id", BigInteger, ForeignKey("accounts.id"), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("specialty", String(200), nullable=False, server_default=text("''")),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

courses = Table(
    "courses",
    metadata,
    _primary_key(),
    Column("name", String(100), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("duration_minutes", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

rooms = Table(
    "rooms",
    metadata,
    _primary_key(),
    Column("name", String(100), nullable=False),
    Column("capacity", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

# ---------------- 课次与预约 ----------------

course_sessions = Table(
    "course_sessions",
    metadata,
    _primary_key(),
    Column("course_id", BigInteger, ForeignKey("courses.id"), nullable=False),
    Column("course_name", String(100), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("coach_id", BigInteger, ForeignKey("coaches.id"), nullable=False),
    Column("room_id", BigInteger, ForeignKey("rooms.id"), nullable=False),
    Column("starts_at", DateTime, nullable=False),
    Column("ends_at", DateTime, nullable=False),
    Column("capacity", Integer, nullable=False),
    Column("status", String(16), nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)
Index("ix_course_sessions_coach_start", course_sessions.c.coach_id, course_sessions.c.starts_at, course_sessions.c.id)
Index("ix_course_sessions_room_start", course_sessions.c.room_id, course_sessions.c.starts_at, course_sessions.c.id)
Index("ix_course_sessions_start", course_sessions.c.starts_at, course_sessions.c.id)

bookings = Table(
    "bookings",
    metadata,
    _primary_key(),
    Column("member_id", BigInteger, ForeignKey("members.id"), nullable=False),
    Column("session_id", BigInteger, ForeignKey("course_sessions.id"), nullable=False),
    Column("membership_id", BigInteger, ForeignKey("memberships.id"), nullable=False),
    Column("status", String(16), nullable=False),
    Column("booked_at", DateTime, nullable=False),
    Column("checked_in_at", DateTime, nullable=True),
    Column("closed_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    UniqueConstraint("member_id", "session_id", name="uq_bookings_member_session"),
)
Index("ix_bookings_session_status", bookings.c.session_id, bookings.c.status, bookings.c.id)
Index("ix_bookings_member_status", bookings.c.member_id, bookings.c.status, bookings.c.id)

operation_records = Table(
    "operation_records",
    metadata,
    _primary_key(),
    Column("request_id", String(64), nullable=False, unique=True),
    Column("actor_id", BigInteger, ForeignKey("accounts.id"), nullable=False),
    Column("operation", String(32), nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("result_id", BigInteger, nullable=False),
    Column("created_at", DateTime, nullable=False),
)
