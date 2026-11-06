"""MemberService 单元测试：校验、权限、幂等三个分支与详情可见范围。

本机未安装 sqlalchemy，这里注入最小替身（text 与 exc.SQLAlchemyError）；
仓储与幂等记录用替身对象替换，真实 SQL 与约束由 MySQL 集成用例验证。
"""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


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
    for name in ("text", "Numeric", "DateTime", "bindparam"):
        if not hasattr(existing, name):
            setattr(existing, name, lambda *args, **kwargs: None)
    if not hasattr(existing, "exc"):
        exc = types.ModuleType("sqlalchemy.exc")

        class SQLAlchemyError(Exception):
            pass

        exc.SQLAlchemyError = SQLAlchemyError
        sys.modules["sqlalchemy.exc"] = exc
        existing.exc = exc


_install_sqlalchemy_stub()

import src.services.member_service as member_service_module  # noqa: E402
from src.errors.business import ConflictError, InvalidInputError, NotFoundError, PermissionDenied  # noqa: E402
from src.models.contracts import Actor, MemberInput, MemberQuery, PageRequest  # noqa: E402
from src.models.member import Member  # noqa: E402
from src.services.member_service import MemberService  # noqa: E402  # noqa: E402

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
OTHER_REQUEST_ID = "0b7a3d5e-2c4f-4a8b-9e6d-1f2a3b4c5d6e"
NOW = datetime(2026, 10, 23, 3, 0, 0, tzinfo=timezone.utc)


def _actor(role="receptionist", account_id=10, member_id=None):
    return Actor(account_id=account_id, role=role, member_id=member_id, coach_id=None)


def _member(member_id=7, name="张三", phone="13800000000", status="active"):
    return Member(
        id=member_id, name=name, phone=phone, status=status,
        archived_at=None, created_at=NOW, updated_at=NOW,
    )


class _Record:
    def __init__(self, *, operation="create_member", actor_id=10, payload_hash="a" * 64, result_id=7):
        self.operation = operation
        self.actor_id = actor_id
        self.payload_hash = payload_hash
        self.result_id = result_id


class _FakeAuth:
    def __init__(self, *, actor=None, error=None):
        self.calls = 0
        self._actor = actor
        self._error = error

    def verify_actor(self, session, actor):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._actor if self._actor is not None else actor


class _FakeMemberRepo:
    """仓储替身：行数据放在类上，保证同一用例内多次构造实例也能读到。"""

    instances = []
    rows: dict[int, Member] = {}
    next_id = 7
    list_result: tuple[list[Member], int] = ([], 0)
    last_query = None
    calls: list[str] = []

    def __init__(self, session):
        self._session = session
        self.created: list[MemberInput] = []
        _FakeMemberRepo.instances.append(self)

    def create(self, data):
        self.created.append(data)
        member = _member(member_id=_FakeMemberRepo.next_id, name=data.name, phone=data.phone)
        _FakeMemberRepo.rows[member.id] = member
        return member

    def get(self, member_id):
        return _FakeMemberRepo.rows.get(member_id)

    def list(self, query):
        type(self).last_query = query
        return type(self).list_result

    def lock(self, member_id):
        type(self).calls.append("lock")
        return type(self).rows.get(member_id)

    def update_profile(self, member_id, name, phone):
        type(self).calls.append("update")
        member = _member(member_id=member_id, name=name, phone=phone)
        type(self).rows[member_id] = member
        return member


class _FakeOperationRepo:
    instances = []
    existing = None
    created: list[dict] = []

    def __init__(self, session):
        self._session = session
        _FakeOperationRepo.instances.append(self)

    def get_by_request(self, request_id):
        return _FakeOperationRepo.existing

    def create(self, **kwargs):
        _FakeOperationRepo.created.append(kwargs)
        return kwargs


class MemberServiceTestBase(unittest.TestCase):
    def setUp(self):
        _FakeMemberRepo.instances.clear()
        _FakeMemberRepo.rows.clear()
        _FakeMemberRepo.next_id = 7
        _FakeMemberRepo.list_result = ([], 0)
        _FakeMemberRepo.last_query = None
        _FakeMemberRepo.calls = []
        _FakeOperationRepo.instances.clear()
        _FakeOperationRepo.existing = None
        _FakeOperationRepo.created = []
        self._patches = [
            patch.object(member_service_module, "MemberRepository", _FakeMemberRepo),
            patch.object(member_service_module, "OperationRepository", _FakeOperationRepo),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self._patches])


class CreateMemberTest(MemberServiceTestBase):
    def test_creates_member_and_records_request(self):
        auth = _FakeAuth()
        service = MemberService(auth)

        view = service.create_member(None, _actor(), MemberInput(name="张三", phone="13800000000"), REQUEST_ID)

        self.assertEqual(view.name, "张三")
        self.assertEqual(view.status, "active")
        self.assertEqual(auth.calls, 1)
        repo = _FakeMemberRepo.instances[-1]
        self.assertEqual(len(repo.created), 1)
        self.assertEqual(len(_FakeOperationRepo.created), 1)
        record = _FakeOperationRepo.created[0]
        self.assertEqual(record["request_id"], REQUEST_ID)
        self.assertEqual(record["actor_id"], 10)
        self.assertEqual(record["operation"], "create_member")
        self.assertEqual(record["result_id"], 7)
        self.assertRegex(record["payload_hash"], r"^[0-9a-f]{64}$")

    def test_payload_hash_matches_contract_field_order(self):
        import hashlib
        import json

        expected = hashlib.sha256(
            json.dumps({"name": "张三", "phone": None}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        service = MemberService(_FakeAuth())
        service.create_member(None, _actor(), MemberInput(name="张三", phone=None), REQUEST_ID)

        self.assertEqual(_FakeOperationRepo.created[0]["payload_hash"], expected)

    def test_strips_whitespace_and_treats_blank_phone_as_none(self):
        service = MemberService(_FakeAuth())

        service.create_member(None, _actor(), MemberInput(name="  张三  ", phone="   "), REQUEST_ID)

        saved = _FakeMemberRepo.instances[-1].created[0]
        self.assertEqual(saved.name, "张三")
        self.assertIsNone(saved.phone)

    def test_rejects_blank_name(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(InvalidInputError):
            service.create_member(None, _actor(), MemberInput(name="   ", phone=None), REQUEST_ID)
        self.assertEqual(_FakeOperationRepo.created, [])

    def test_rejects_name_over_100_chars(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(InvalidInputError):
            service.create_member(None, _actor(), MemberInput(name="张" * 101, phone=None), REQUEST_ID)

    def test_rejects_phone_over_32_chars(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(InvalidInputError):
            service.create_member(None, _actor(), MemberInput(name="张三", phone="1" * 33), REQUEST_ID)

    def test_rejects_member_role(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(PermissionDenied):
            service.create_member(None, _actor(role="member", member_id=7), MemberInput(name="张三", phone=None), REQUEST_ID)

    def test_rejects_coach_role(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(PermissionDenied):
            service.create_member(None, _actor(role="coach"), MemberInput(name="张三", phone=None), REQUEST_ID)

    def test_rejects_non_canonical_request_id(self):
        service = MemberService(_FakeAuth())
        for bad in (REQUEST_ID.upper(), "not-a-uuid", 123, ""):
            with self.subTest(request_id=bad), self.assertRaises(InvalidInputError):
                service.create_member(None, _actor(), MemberInput(name="张三", phone=None), bad)


class IdempotentCreateTest(MemberServiceTestBase):
    def _hash_of(self, name="张三", phone="13800000000"):
        service = MemberService(_FakeAuth())
        _FakeMemberRepo.instances.clear()
        _FakeOperationRepo.created = []
        service.create_member(None, _actor(), MemberInput(name=name, phone=phone), REQUEST_ID)
        return _FakeOperationRepo.created[0]["payload_hash"]

    def test_replay_with_same_payload_returns_original_member(self):
        payload_hash = self._hash_of()
        _FakeMemberRepo.instances.clear()
        _FakeOperationRepo.created = []
        _FakeOperationRepo.existing = _Record(payload_hash=payload_hash)

        service = MemberService(_FakeAuth())
        # 原会员已在库中，重放时不应再插入
        _FakeMemberRepo.instances.clear()
        view = service.create_member(None, _actor(), MemberInput(name="张三", phone="13800000000"), REQUEST_ID)

        self.assertEqual(view.id, 7)
        self.assertEqual(_FakeOperationRepo.created, [])

    def test_replay_with_different_payload_raises_conflict(self):
        _FakeOperationRepo.existing = _Record(payload_hash="b" * 64)
        service = MemberService(_FakeAuth())
        with self.assertRaises(ConflictError):
            service.create_member(None, _actor(), MemberInput(name="李四", phone=None), REQUEST_ID)

    def test_replay_from_other_actor_raises_conflict(self):
        _FakeOperationRepo.existing = _Record(actor_id=99, payload_hash="a" * 64)
        service = MemberService(_FakeAuth())
        with self.assertRaises(ConflictError):
            service.create_member(None, _actor(account_id=10), MemberInput(name="张三", phone=None), REQUEST_ID)

    def test_replay_of_other_operation_raises_conflict(self):
        _FakeOperationRepo.existing = _Record(operation="sell_gym_card")
        service = MemberService(_FakeAuth())
        with self.assertRaises(ConflictError):
            service.create_member(None, _actor(), MemberInput(name="张三", phone=None), REQUEST_ID)


class GetMemberByRequestTest(MemberServiceTestBase):
    def test_missing_record_raises_not_found(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(NotFoundError):
            service.get_member_by_request(None, _actor(), REQUEST_ID)

    def test_record_of_other_actor_raises_not_found(self):
        _FakeOperationRepo.existing = _Record(actor_id=99)
        service = MemberService(_FakeAuth())
        with self.assertRaises(NotFoundError):
            service.get_member_by_request(None, _actor(account_id=10), REQUEST_ID)

    def test_operation_mismatch_raises_conflict(self):
        _FakeOperationRepo.existing = _Record(operation="sell_gym_card", actor_id=10)
        service = MemberService(_FakeAuth())
        with self.assertRaises(ConflictError):
            service.get_member_by_request(None, _actor(account_id=10), REQUEST_ID)

    def test_admin_can_verify_request_of_other_actor(self):
        _FakeOperationRepo.existing = _Record(actor_id=99, result_id=7)
        repo = _FakeMemberRepo(None)
        repo.rows[7] = _member()
        service = MemberService(_FakeAuth())
        with patch.object(member_service_module, "MemberRepository", lambda session: repo):
            view = service.get_member_by_request(None, _actor(role="admin"), REQUEST_ID)
        self.assertEqual(view.id, 7)

    def test_returns_view_for_original_request(self):
        _FakeOperationRepo.existing = _Record(actor_id=10, result_id=7)
        repo = _FakeMemberRepo(None)
        repo.rows[7] = _member()
        service = MemberService(_FakeAuth())
        with patch.object(member_service_module, "MemberRepository", lambda session: repo):
            view = service.get_member_by_request(None, _actor(account_id=10), REQUEST_ID)
        self.assertEqual(view.id, 7)


class GetMemberTest(MemberServiceTestBase):
    def _service_with_member(self):
        repo = _FakeMemberRepo(None)
        repo.rows[7] = _member()
        service = MemberService(_FakeAuth())
        self._repo_patch = patch.object(member_service_module, "MemberRepository", lambda session: repo)
        self._repo_patch.start()
        self.addCleanup(self._repo_patch.stop)
        return service

    def test_staff_can_read_any_member(self):
        service = self._service_with_member()
        self.assertEqual(service.get_member(None, _actor(role="admin"), 7).id, 7)

    def test_member_can_read_self(self):
        service = self._service_with_member()
        view = service.get_member(None, _actor(role="member", member_id=7), 7)
        self.assertEqual(view.id, 7)

    def test_member_cannot_read_others(self):
        service = self._service_with_member()
        with self.assertRaises(NotFoundError):
            service.get_member(None, _actor(role="member", member_id=8), 7)

    def test_coach_cannot_read_profile(self):
        service = self._service_with_member()
        with self.assertRaises(NotFoundError):
            service.get_member(None, _actor(role="coach"), 7)

    def test_missing_member_raises_not_found(self):
        service = self._service_with_member()
        with self.assertRaises(NotFoundError):
            service.get_member(None, _actor(), 999)

    def test_rejects_bool_member_id(self):
        service = self._service_with_member()
        with self.assertRaises(InvalidInputError):
            service.get_member(None, _actor(), True)


class ListMembersTest(MemberServiceTestBase):
    def test_staff_filter_is_passed_through(self):
        _FakeMemberRepo.list_result = ([_member(7)], 1)
        service = MemberService(_FakeAuth())

        page = service.list_members(
            None,
            _actor(role="admin"),
            MemberQuery(member_id=7, keyword="张", paging=PageRequest(page=2, page_size=5)),
        )

        self.assertEqual(page.total, 1)
        self.assertEqual(page.page, 2)
        self.assertEqual(page.page_size, 5)
        self.assertEqual([v.id for v in page.items], [7])
        scoped = _FakeMemberRepo.last_query
        self.assertEqual(scoped.member_id, 7)
        self.assertEqual(scoped.keyword, "张")

    def test_member_is_forced_to_own_profile(self):
        _FakeMemberRepo.list_result = ([_member(7)], 1)
        service = MemberService(_FakeAuth())

        service.list_members(None, _actor(role="member", member_id=7), MemberQuery(paging=PageRequest()))

        self.assertEqual(_FakeMemberRepo.last_query.member_id, 7)

    def test_member_querying_other_profile_gets_empty_page(self):
        service = MemberService(_FakeAuth())

        page = service.list_members(
            None,
            _actor(role="member", member_id=7),
            MemberQuery(member_id=8, paging=PageRequest()),
        )

        self.assertEqual(page.items, [])
        self.assertEqual(page.total, 0)
        self.assertIsNone(_FakeMemberRepo.last_query)

    def test_coach_cannot_list_members(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(PermissionDenied):
            service.list_members(None, _actor(role="coach"), MemberQuery(paging=PageRequest()))

    def test_rejects_invalid_paging(self):
        service = MemberService(_FakeAuth())
        for paging in (
            PageRequest(page=0),
            PageRequest(page_size=0),
            PageRequest(page_size=101),
        ):
            with self.subTest(paging=paging), self.assertRaises(InvalidInputError):
                service.list_members(None, _actor(), MemberQuery(paging=paging))

    def test_maps_rows_to_views(self):
        _FakeMemberRepo.list_result = ([_member(7), _member(8)], 2)
        service = MemberService(_FakeAuth())

        page = service.list_members(None, _actor(), MemberQuery(paging=PageRequest()))

        self.assertEqual([v.id for v in page.items], [7, 8])
        self.assertEqual(page.total, 2)


class UpdateMemberTest(MemberServiceTestBase):
    def test_staff_updates_and_returns_latest_value(self):
        _FakeMemberRepo.rows[7] = _member(7)
        service = MemberService(_FakeAuth())

        view = service.update_member(None, _actor(), 7, MemberInput(name="  李四  ", phone=" 13900000000 "))

        self.assertEqual(view.id, 7)
        self.assertEqual(view.name, "李四")
        self.assertEqual(view.phone, "13900000000")
        self.assertEqual(_FakeMemberRepo.calls, ["lock", "update"])

    def test_missing_member_raises_not_found(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(NotFoundError):
            service.update_member(None, _actor(), 7, MemberInput(name="李四", phone=None))
        self.assertEqual(_FakeMemberRepo.calls, ["lock"])

    def test_member_role_cannot_update(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(PermissionDenied):
            service.update_member(None, _actor(role="member", member_id=7), 7, MemberInput(name="李四", phone=None))

    def test_coach_cannot_update(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(PermissionDenied):
            service.update_member(None, _actor(role="coach"), 7, MemberInput(name="李四", phone=None))

    def test_blank_name_rejected_before_touching_storage(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(InvalidInputError):
            service.update_member(None, _actor(), 7, MemberInput(name="   ", phone=None))
        self.assertEqual(_FakeMemberRepo.calls, [])

    def test_rejects_bool_member_id(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(InvalidInputError):
            service.update_member(None, _actor(), True, MemberInput(name="李四", phone=None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
