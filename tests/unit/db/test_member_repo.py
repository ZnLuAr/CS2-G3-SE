"""MemberRepository 单元测试：建档、详情读取、锁定、分页筛选与资料更新。

会话用替身记录语句并返回预设行；真实 CHECK 约束、DATETIME(6) 精度、
LIKE 转义的实际匹配和 FOR UPDATE 的锁效果由 MySQL 集成用例验证。
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.db.member_repo import MemberRepository
from src.errors.storage import StorageError
from src.models.contracts import MemberInput, MemberQuery, PageRequest
from tests.support.clock import AWARE_NOW, UtcClock

NAIVE_UTC = datetime(2026, 10, 23, 2, 0, 0)
AWARE_UTC = NAIVE_UTC.replace(tzinfo=timezone.utc)
COLUMNS = "id, name, phone, status, archived_at, created_at, updated_at"
SELECT_BY_ID_SQL = f"SELECT {COLUMNS} FROM members WHERE id = :member_id"
INSERT_SQL = (
    "INSERT INTO members (name, phone, status, archived_at, created_at, updated_at) "
    "VALUES (:name, :phone, :status, NULL, :created_at, :updated_at)"
)
UPDATE_SQL = (
    "UPDATE members SET name = :name, phone = :phone, updated_at = :updated_at "
    "WHERE id = :member_id"
)
LIKE_CLAUSE = "name LIKE :keyword ESCAPE '\\\\'"
# SQLAlchemy Core 语句渲染时带换行，断言前合并空白。
LOCK_SQL = (
    "SELECT members.id, members.name, members.phone, members.status, members.archived_at, "
    "members.created_at, members.updated_at FROM members WHERE members.id = :id_1 FOR UPDATE"
)


class _FakeResult:
    def __init__(self, row=None, lastrowid=None, scalar=None, rows=None) -> None:
        self._row = row
        self.lastrowid = lastrowid
        self._scalar = scalar
        self._rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self._row

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


class _FakeSession:
    """记录执行过的语句，并按语句形状返回预设结果。"""

    def __init__(self, rows=None, inserted_id=7, count=0, page_rows=None) -> None:
        self.calls: list[tuple[str, dict | None]] = []
        self._rows = rows or {}
        self._inserted_id = inserted_id
        self._count = count
        self._page_rows = page_rows or []

    def execute(self, statement, params=None) -> _FakeResult:
        sql = str(statement)
        # Core 语句（FOR UPDATE 锁定）的绑定参数随语句对象携带，调用方不单独传。
        bound = statement.compile().params if params is None else params
        self.calls.append((sql, bound))
        upper = sql.lstrip().upper()
        if upper.startswith("INSERT"):
            return _FakeResult(lastrowid=self._inserted_id)
        if upper.startswith("SELECT COUNT(*)"):
            return _FakeResult(scalar=self._count)
        if "ORDER BY ID ASC" in upper:
            return _FakeResult(rows=self._page_rows)
        if "FOR UPDATE" in upper:
            return _FakeResult(row=self._rows.get(bound["id_1"]))
        return _FakeResult(row=self._rows.get(params["member_id"]))


def _row(member_id=7, *, phone="13800000000") -> dict:
    return {
        "id": member_id,
        "name": "张三",
        "phone": phone,
        "status": "active",
        "archived_at": None,
        "created_at": NAIVE_UTC,
        "updated_at": NAIVE_UTC,
    }


def _where_fragment(sql: str) -> str:
    """取出 `FROM members WHERE` 之后、排序分页之前的条件片段。"""
    tail = sql.split("FROM members WHERE ", 1)[1]
    return tail.split(" ORDER BY ", 1)[0]


def _flat(sql: str) -> str:
    """合并空白，便于对 Core 语句做全文断言。"""
    return " ".join(sql.split())


class CreateMemberTest(unittest.TestCase):
    def test_insert_writes_active_member_without_archive_time(self):
        session = _FakeSession(rows={7: _row()})
        MemberRepository(session).create(MemberInput(name="张三", phone="13800000000"))

        sql, params = session.calls[0]
        self.assertEqual(sql, INSERT_SQL)
        self.assertEqual(params["name"], "张三")
        self.assertEqual(params["phone"], "13800000000")
        self.assertEqual(params["status"], "active")
        self.assertEqual(
            set(params), {"name", "phone", "status", "created_at", "updated_at"}
        )
        self.assertIsNone(params["created_at"].tzinfo)
        self.assertIsNone(params["updated_at"].tzinfo)

    def test_create_timestamps_come_from_utc_clock(self):
        """合同 12.6：created_at 与 updated_at 由仓储按 UTC 生成，不依赖本机时区。"""
        session = _FakeSession(rows={7: _row()})
        with patch("datetime.datetime", UtcClock):
            MemberRepository(session).create(MemberInput(name="张三", phone=None))

        params = session.calls[0][1]
        self.assertEqual(params["created_at"], AWARE_NOW.replace(tzinfo=None))
        self.assertEqual(params["updated_at"], AWARE_NOW.replace(tzinfo=None))

    def test_returns_member_read_back_by_new_id(self):
        """返回值取自按自增编号回读的行：编号与时间戳只有库里有，INSERT 参数里没有。"""
        session = _FakeSession(rows={41: _row(41, phone=None)}, inserted_id=41)
        created = MemberRepository(session).create(MemberInput(name="张三", phone=None))

        self.assertEqual(session.calls[1][0], SELECT_BY_ID_SQL)
        self.assertEqual(session.calls[1][1], {"member_id": 41})
        self.assertEqual(created.id, 41)
        self.assertEqual(created.name, "张三")
        self.assertIsNone(created.phone)
        self.assertEqual(created.status, "active")
        self.assertIsNone(created.archived_at)
        self.assertEqual(created.created_at, AWARE_UTC)
        self.assertEqual(created.updated_at, AWARE_UTC)

    def test_raises_storage_error_when_read_back_missing(self):
        session = _FakeSession(rows={})
        with self.assertRaises(StorageError):
            MemberRepository(session).create(MemberInput(name="张三", phone=None))


class GetMemberTest(unittest.TestCase):
    def test_returns_none_when_missing(self):
        session = _FakeSession(rows={})
        self.assertIsNone(MemberRepository(session).get(99))
        self.assertEqual(session.calls[0], (SELECT_BY_ID_SQL, {"member_id": 99}))

    def test_attaches_utc_and_keeps_null_fields(self):
        session = _FakeSession(rows={7: _row(phone=None)})
        member = MemberRepository(session).get(7)

        self.assertIsNotNone(member)
        self.assertIsNone(member.phone)
        self.assertIsNone(member.archived_at)
        self.assertEqual(member.created_at, AWARE_UTC)
        self.assertEqual(member.updated_at, AWARE_UTC)


class LockTest(unittest.TestCase):
    """合同 12.3.1 / 12.4.4：改资料前用 SELECT ... FOR UPDATE 锁定目标行。"""

    def test_locks_target_row_and_returns_member(self):
        session = _FakeSession(rows={7: _row()})
        member = MemberRepository(session).lock(7)

        sql, params = session.calls[0]
        self.assertEqual(_flat(sql), LOCK_SQL)
        self.assertEqual(params, {"id_1": 7})
        self.assertIsNotNone(member)
        self.assertEqual(member.created_at, AWARE_UTC)

    def test_returns_none_when_target_missing(self):
        session = _FakeSession(rows={})
        self.assertIsNone(MemberRepository(session).lock(99))
        self.assertEqual(session.calls[0][1], {"id_1": 99})
        self.assertTrue(_flat(session.calls[0][0]).endswith("FOR UPDATE"))


class UpdateProfileTest(unittest.TestCase):
    def test_writes_name_phone_and_rereads(self):
        session = _FakeSession(rows={7: _row(phone="13900000000")})
        member = MemberRepository(session).update_profile(7, "李四", "13900000000")

        sql, params = session.calls[0]
        # 只改姓名、联系方式和更新时刻，不能顺带改动状态或归档时刻。
        self.assertEqual(sql, UPDATE_SQL)
        self.assertEqual(params["name"], "李四")
        self.assertEqual(params["phone"], "13900000000")
        self.assertEqual(params["member_id"], 7)
        self.assertIsNone(params["updated_at"].tzinfo)
        self.assertEqual(session.calls[1], (SELECT_BY_ID_SQL, {"member_id": 7}))
        self.assertEqual(member.updated_at.tzinfo, timezone.utc)

    def test_updated_at_comes_from_utc_clock(self):
        session = _FakeSession(rows={7: _row()})
        with patch("datetime.datetime", UtcClock):
            MemberRepository(session).update_profile(7, "李四", None)

        self.assertEqual(session.calls[0][1]["updated_at"], AWARE_NOW.replace(tzinfo=None))

    def test_clears_phone_when_none(self):
        session = _FakeSession(rows={7: _row(phone=None)})
        MemberRepository(session).update_profile(7, "张三", None)
        self.assertIsNone(session.calls[0][1]["phone"])

    def test_raises_when_row_disappears(self):
        session = _FakeSession(rows={})
        with self.assertRaises(StorageError):
            MemberRepository(session).update_profile(7, "张三", None)


class ListMembersTest(unittest.TestCase):
    # 每页条数与偏移量取不同值，绑定互换时断言才会失败。
    PAGE = 3
    PAGE_SIZE = 5

    def _call(self, *, count=0, page_rows=None, **query_kwargs):
        session = _FakeSession(count=count, page_rows=page_rows or [])
        query = MemberQuery(paging=PageRequest(page=self.PAGE, page_size=self.PAGE_SIZE), **query_kwargs)
        rows, total = MemberRepository(session).list(query)
        return session, query, rows, total

    def test_orders_by_id_and_applies_paging(self):
        session = _FakeSession(count=3, page_rows=[_row(7), _row(8)])
        MemberRepository(session).list(
            MemberQuery(paging=PageRequest(page=self.PAGE, page_size=self.PAGE_SIZE))
        )

        count_sql, count_params = session.calls[0]
        page_sql, page_params = session.calls[1]
        self.assertEqual(count_sql, "SELECT COUNT(*) FROM members WHERE 1 = 1")
        self.assertEqual(count_params, {})
        self.assertEqual(
            page_sql,
            f"SELECT {COLUMNS} FROM members WHERE 1 = 1 ORDER BY id ASC LIMIT :limit OFFSET :offset",
        )
        self.assertEqual(page_params, {"limit": self.PAGE_SIZE, "offset": 10})

    def test_count_and_page_queries_share_filters(self):
        """合同 12.9.1：总数与当页使用同一组筛选条件，避免口径不一致。"""
        session, query, _, _ = self._call(
            count=1, member_id=7, keyword="  张  ", status="active",
        )

        count_sql, count_params = session.calls[0]
        page_sql, page_params = session.calls[1]
        expected_filters = {"member_id": 7, "keyword": "%张%", "status": "active"}
        for sql in (count_sql, page_sql):
            self.assertIn("id = :member_id", sql)
            self.assertIn(LIKE_CLAUSE, sql)
            self.assertIn("status = :status", sql)
            self.assertNotIn("1 = 1", sql)
        # WHERE 片段逐字相同，总数与当页才不会一个带条件、一个不带。
        self.assertEqual(_where_fragment(count_sql), _where_fragment(page_sql))
        self.assertEqual(count_params, expected_filters)
        self.assertEqual(
            page_params,
            {**expected_filters, "limit": self.PAGE_SIZE, "offset": 10},
        )

    def test_escapes_like_wildcards(self):
        session = _FakeSession()
        MemberRepository(session).list(MemberQuery(keyword="50%_\\", paging=PageRequest()))

        count_sql, params = session.calls[0]
        self.assertIn(LIKE_CLAUSE, count_sql)
        self.assertEqual(params["keyword"], "%50\\%\\_\\\\%")

    def test_blank_keyword_does_not_filter(self):
        """纯空白关键词表示不按姓名过滤，不能变成匹配空白串的 LIKE 条件。"""
        session = _FakeSession()
        MemberRepository(session).list(MemberQuery(keyword="   ", paging=PageRequest()))

        self.assertNotIn("LIKE", session.calls[0][0])
        self.assertEqual(session.calls[0][1], {})

    def test_returns_page_rows_and_total(self):
        _, _, rows, total = self._call(count=2, page_rows=[_row(7), _row(8)])

        self.assertEqual(total, 2)
        self.assertEqual([r.id for r in rows], [7, 8])
        self.assertEqual(rows[0].created_at.tzinfo, timezone.utc)


class PlaceholderTest(unittest.TestCase):
    """MEM-06 尚未实现，占位方法保持显式失败。"""

    def test_set_status_still_placeholder(self):
        with self.assertRaises(NotImplementedError):
            MemberRepository(_FakeSession()).set_status(7, "archived", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
