"""MemberRepository 建档与详情读取的单元测试。

本机未安装 sqlalchemy，这里注入一个最小替身：
`text()` 返回带 SQL 文本的对象，会话返回可注入的行与 lastrowid。
数据库真实行为（CHECK 约束、DATETIME(6) 精度、SELECT ... FOR UPDATE）由 MySQL 集成用例验证。
"""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone


class _Text:
    """替身：只保留 SQL 文本，便于断言语句内容。"""

    def __init__(self, sql: str) -> None:
        self.sql = sql

    def __str__(self) -> str:
        return self.sql


def _install_sqlalchemy_stub() -> None:
    """仓库环境装了 sqlalchemy 时用真包；只在缺依赖的本机注入带标记的替身。"""
    existing = sys.modules.get("sqlalchemy")
    if existing is not None and not getattr(existing, "__dsh_stub__", False):
        return
    if existing is None:
        try:
            import sqlalchemy as existing  # noqa: F401
        except ModuleNotFoundError:
            existing = None
        if existing is not None:
            return
    if existing is None:
        existing = types.ModuleType("sqlalchemy")
        existing.__dsh_stub__ = True
        existing.__path__ = []
        sys.modules["sqlalchemy"] = existing
    for name in ("Numeric", "DateTime", "bindparam"):
        if not hasattr(existing, name):
            setattr(existing, name, lambda *args, **kwargs: None)
    existing.text = lambda sql: _Text(sql)


_install_sqlalchemy_stub()

from src.db.member_repo import MemberRepository  # noqa: E402
from src.errors.storage import StorageError  # noqa: E402
from src.models.contracts import MemberInput  # noqa: E402

NAIVE_UTC = datetime(2026, 10, 23, 2, 0, 0)
AWARE_UTC = NAIVE_UTC.replace(tzinfo=timezone.utc)


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
        self.calls.append((sql, params))
        upper = sql.lstrip().upper()
        if upper.startswith("INSERT"):
            return _FakeResult(lastrowid=self._inserted_id)
        if upper.startswith("SELECT COUNT(*)"):
            return _FakeResult(scalar=self._count)
        if "ORDER BY ID ASC" in upper:
            return _FakeResult(rows=self._page_rows)
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


class CreateMemberTest(unittest.TestCase):
    def test_insert_writes_active_member_without_archive_time(self):
        session = _FakeSession(rows={7: _row()})
        MemberRepository(session).create(MemberInput(name="张三", phone="13800000000"))

        sql, params = session.calls[0]
        self.assertIn("INSERT INTO members", sql)
        self.assertEqual(params["name"], "张三")
        self.assertEqual(params["phone"], "13800000000")
        self.assertEqual(params["status"], "active")
        self.assertNotIn("archived_at", params)
        self.assertIsNone(params["created_at"].tzinfo)
        self.assertIsNone(params["updated_at"].tzinfo)

    def test_returns_member_read_back_by_new_id(self):
        session = _FakeSession(rows={7: _row()})
        created = MemberRepository(session).create(MemberInput(name="张三", phone=None))

        self.assertEqual(created.id, 7)
        self.assertEqual(created.name, "张三")
        self.assertEqual(created.status, "active")
        self.assertIsNone(created.archived_at)
        self.assertEqual(created.created_at, AWARE_UTC)

    def test_raises_storage_error_when_read_back_missing(self):
        session = _FakeSession(rows={})
        with self.assertRaises(StorageError):
            MemberRepository(session).create(MemberInput(name="张三", phone=None))


class GetMemberTest(unittest.TestCase):
    def test_returns_none_when_missing(self):
        session = _FakeSession(rows={})
        self.assertIsNone(MemberRepository(session).get(99))
        sql, params = session.calls[0]
        self.assertIn("FROM members", sql)
        self.assertEqual(params["member_id"], 99)

    def test_attaches_utc_and_keeps_null_fields(self):
        session = _FakeSession(rows={7: _row(phone=None)})
        member = MemberRepository(session).get(7)

        self.assertIsNotNone(member)
        self.assertIsNone(member.phone)
        self.assertEqual(member.created_at.tzinfo, timezone.utc)
        self.assertEqual(member.updated_at, AWARE_UTC)

    def test_selects_all_member_columns(self):
        session = _FakeSession(rows={7: _row()})
        MemberRepository(session).get(7)
        sql = session.calls[0][0]
        for column in ("id", "name", "phone", "status", "archived_at", "created_at", "updated_at"):
            self.assertIn(column, sql)


class UpdateProfileTest(unittest.TestCase):
    def test_writes_name_phone_and_rereads(self):
        session = _FakeSession(rows={7: _row(phone="13900000000")})
        member = MemberRepository(session).update_profile(7, "李四", "13900000000")

        sql, params = session.calls[0]
        self.assertIn("UPDATE members SET name = :name, phone = :phone", sql)
        self.assertIn("WHERE id = :member_id", sql)
        self.assertEqual(params["name"], "李四")
        self.assertEqual(params["phone"], "13900000000")
        self.assertEqual(params["member_id"], 7)
        self.assertIsNone(params["updated_at"].tzinfo)
        self.assertIn("FROM members", session.calls[1][0])
        self.assertEqual(member.updated_at.tzinfo, timezone.utc)

    def test_clears_phone_when_none(self):
        session = _FakeSession(rows={7: _row(phone=None)})
        MemberRepository(session).update_profile(7, "张三", None)
        self.assertIsNone(session.calls[0][1]["phone"])

    def test_raises_when_row_disappears(self):
        session = _FakeSession(rows={})
        with self.assertRaises(StorageError):
            MemberRepository(session).update_profile(7, "张三", None)


class PlaceholderTest(unittest.TestCase):
    """MEM-06 尚未实现，占位方法保持显式失败。"""

    def test_set_status_still_placeholder(self):
        with self.assertRaises(NotImplementedError):
            MemberRepository(_FakeSession()).set_status(7, "archived", None)


class ListMembersTest(unittest.TestCase):
    def _call(self, *, count=0, page_rows=None, **query_kwargs):
        from src.models.contracts import MemberQuery, PageRequest

        session = _FakeSession(count=count, page_rows=page_rows or [])
        query = MemberQuery(paging=PageRequest(page=1, page_size=20), **query_kwargs)
        rows, total = MemberRepository(session).list(query)
        return session, rows, total

    def test_orders_by_id_and_applies_paging(self):
        from src.models.contracts import MemberQuery, PageRequest

        session = _FakeSession(count=3, page_rows=[_row(7), _row(8)])
        MemberRepository(session).list(MemberQuery(paging=PageRequest(page=2, page_size=10)))

        count_sql, count_params = session.calls[0]
        page_sql, page_params = session.calls[1]
        self.assertIn("SELECT COUNT(*)", count_sql)
        self.assertIn("ORDER BY id ASC LIMIT :limit OFFSET :offset", page_sql)
        self.assertEqual(page_params["limit"], 10)
        self.assertEqual(page_params["offset"], 10)
        self.assertEqual(count_params, {})

    def test_filters_by_member_keyword_and_status(self):
        from src.models.contracts import MemberQuery, PageRequest

        session = _FakeSession()
        MemberRepository(session).list(
            MemberQuery(member_id=7, keyword="  张  ", status="active", paging=PageRequest())
        )

        count_sql, params = session.calls[0]
        self.assertIn("id = :member_id", count_sql)
        self.assertIn("name LIKE :keyword", count_sql)
        self.assertIn("status = :status", count_sql)
        self.assertEqual(params["member_id"], 7)
        self.assertEqual(params["keyword"], "%张%")
        self.assertEqual(params["status"], "active")

    def test_escapes_like_wildcards(self):
        from src.models.contracts import MemberQuery, PageRequest

        session = _FakeSession()
        MemberRepository(session).list(MemberQuery(keyword="50%_\\", paging=PageRequest()))

        _, params = session.calls[0]
        self.assertEqual(params["keyword"], "%50\\%\\_\\\\%")
        self.assertIn("ESCAPE", session.calls[0][0])

    def test_returns_page_rows_and_total(self):
        _, rows, total = self._call(count=2, page_rows=[_row(7), _row(8)])

        self.assertEqual(total, 2)
        self.assertEqual([r.id for r in rows], [7, 8])
        self.assertEqual(rows[0].created_at.tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
