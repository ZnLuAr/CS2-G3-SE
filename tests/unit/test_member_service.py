"""MemberService 单元测试：校验、权限、幂等三个分支与可见范围。

仓储与幂等记录用替身对象替换；真实 SQL 与约束由 MySQL 集成用例验证。
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import src.services.member_service as member_service_module
from src.errors import StorageError
from src.errors.business import (
    AuthenticationError,
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDenied,
)
from src.models.contracts import Actor, MemberInput, MemberQuery, PageRequest
from src.models.member import Member
from src.services.member_service import MemberService

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
NOW = datetime(2026, 10, 23, 3, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 24, 3, 0, 0, tzinfo=timezone.utc)


def _actor(role="receptionist", account_id=10, member_id=None):
    return Actor(account_id=account_id, role=role, member_id=member_id, coach_id=None)


def _member(member_id=7, name="张三", phone="13800000000", status="active", archived_at=None):
    # 创建与更新时刻取不同值，视图字段互换时断言才能发现。
    return Member(
        id=member_id, name=name, phone=phone, status=status,
        archived_at=archived_at, created_at=NOW, updated_at=LATER,
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
        # 自增编号取一个输入里没有的数，返回视图与请求记录里的编号只能来自仓储写入的结果。
        _FakeMemberRepo.next_id = 41
        auth = _FakeAuth()
        service = MemberService(auth)

        view = service.create_member(None, _actor(), MemberInput(name="张三", phone="13800000000"), REQUEST_ID)

        self.assertEqual(view.id, 41)
        self.assertEqual(view.name, "张三")
        self.assertEqual(view.status, "active")
        self.assertEqual(view.phone, "13800000000")
        self.assertIsNone(view.archived_at)
        self.assertEqual(view.created_at, NOW)
        self.assertEqual(view.updated_at, LATER)
        self.assertEqual(auth.calls, 1)
        repo = _FakeMemberRepo.instances[-1]
        self.assertEqual(len(repo.created), 1)
        self.assertEqual(len(_FakeOperationRepo.created), 1)
        record = _FakeOperationRepo.created[0]
        self.assertEqual(record["request_id"], REQUEST_ID)
        self.assertEqual(record["actor_id"], 10)
        self.assertEqual(record["operation"], "create_member")
        self.assertEqual(record["result_id"], 41)
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

    def test_strips_name_whitespace(self):
        service = MemberService(_FakeAuth())

        service.create_member(None, _actor(), MemberInput(name="  张三  ", phone=None), REQUEST_ID)

        saved = _FakeMemberRepo.instances[-1].created[0]
        self.assertEqual(saved.name, "张三")
        self.assertIsNone(saved.phone)

    def test_rejects_blank_phone(self):
        """合同 12.2.2：phone=None 表示没有联系方式，空字符串不合法。"""
        service = MemberService(_FakeAuth())
        for blank in ("", "   "):
            with self.subTest(phone=blank), self.assertRaises(InvalidInputError):
                service.create_member(None, _actor(), MemberInput(name="张三", phone=blank), REQUEST_ID)
        self.assertEqual(_FakeOperationRepo.created, [])

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

    def test_role_is_checked_before_input_validation(self):
        """权限检查先于输入校验：越权角色提交非法输入时仍按权限拒绝。"""
        service = MemberService(_FakeAuth())
        with self.assertRaises(PermissionDenied):
            service.create_member(
                None, _actor(role="member", member_id=7), MemberInput(name="   ", phone=None), REQUEST_ID
            )
        self.assertEqual(_FakeMemberRepo.instances, [])

    def test_rejects_non_canonical_request_id(self):
        service = MemberService(_FakeAuth())
        for bad in (REQUEST_ID.upper(), "not-a-uuid", 123, ""):
            with self.subTest(request_id=bad), self.assertRaises(InvalidInputError):
                service.create_member(None, _actor(), MemberInput(name="张三", phone=None), bad)

    def test_admin_can_create_member(self):
        """合同 12.3.1：建档权限是前台与管理员。"""
        service = MemberService(_FakeAuth())

        view = service.create_member(None, _actor(role="admin"), MemberInput(name="张三", phone=None), REQUEST_ID)

        self.assertEqual(view.id, 7)
        self.assertEqual(len(_FakeOperationRepo.created), 1)

    def test_accepts_boundary_lengths(self):
        """合同 12.8.1：姓名恰好 100 字、联系方式恰好 32 字都合法。"""
        service = MemberService(_FakeAuth())

        service.create_member(None, _actor(), MemberInput(name="张" * 100, phone="1" * 32), REQUEST_ID)

        saved = _FakeMemberRepo.instances[-1].created[0]
        self.assertEqual(len(saved.name), 100)
        self.assertEqual(len(saved.phone), 32)

    def test_rejects_wrong_input_types(self):
        service = MemberService(_FakeAuth())
        for bad in (
            None,
            MemberInput(name=123, phone=None),
            MemberInput(name="张三", phone=13800000000),
        ):
            with self.subTest(data=bad), self.assertRaises(InvalidInputError):
                service.create_member(None, _actor(), bad, REQUEST_ID)
        self.assertEqual(_FakeOperationRepo.created, [])

    def test_verify_actor_failure_propagates_before_any_write(self):
        """合同 12.7.2：每次都先重验账号，复核失败时不能留下任何写入。"""
        auth = _FakeAuth(error=AuthenticationError("当前登录身份已失效，请重新登录"))
        service = MemberService(auth)

        with self.assertRaises(AuthenticationError):
            service.create_member(None, _actor(), MemberInput(name="张三", phone=None), REQUEST_ID)

        self.assertEqual(_FakeMemberRepo.instances, [])
        self.assertEqual(_FakeOperationRepo.created, [])


class IdempotentCreateTest(MemberServiceTestBase):
    """合同 12.7.2：request_id、操作者、操作名、摘要四项都相同才回放原结果。"""

    def _hash_of(self, name="张三", phone="13800000000"):
        service = MemberService(_FakeAuth())
        _FakeMemberRepo.instances.clear()
        _FakeOperationRepo.created = []
        service.create_member(None, _actor(), MemberInput(name=name, phone=phone), REQUEST_ID)
        return _FakeOperationRepo.created[0]["payload_hash"]

    def _replay(self, auth, make_record):
        """预置一条已存在的请求记录（摘要取真实值），再按相同内容提交。"""
        payload_hash = self._hash_of()
        _FakeMemberRepo.instances.clear()
        _FakeOperationRepo.created = []
        _FakeOperationRepo.existing = make_record(payload_hash)
        return MemberService(auth).create_member(
            None, _actor(), MemberInput(name="张三", phone="13800000000"), REQUEST_ID
        )

    def test_replay_with_same_payload_returns_original_member(self):
        auth = _FakeAuth()

        view = self._replay(auth, lambda payload_hash: _Record(payload_hash=payload_hash))

        self.assertEqual(view.id, 7)
        # 原会员已在库中，重放时不新建会员、不写记录，但仍复核一次身份（合同 12.7.2）。
        self.assertEqual(_FakeMemberRepo.instances[-1].created, [])
        self.assertEqual(_FakeOperationRepo.created, [])
        self.assertEqual(auth.calls, 1)

    def test_replay_with_different_payload_raises_conflict(self):
        with self.assertRaises(ConflictError):
            self._replay(_FakeAuth(), lambda payload_hash: _Record(payload_hash="b" * 64))

    def test_replay_from_other_actor_raises_conflict(self):
        """操作者是唯一差异：操作名和摘要都与原请求一致。"""
        with self.assertRaises(ConflictError):
            self._replay(
                _FakeAuth(), lambda payload_hash: _Record(actor_id=99, payload_hash=payload_hash)
            )

    def test_replay_of_other_operation_raises_conflict(self):
        """操作名是唯一差异：操作者和摘要都与原请求一致。"""
        with self.assertRaises(ConflictError):
            self._replay(
                _FakeAuth(),
                lambda payload_hash: _Record(operation="sell_gym_card", payload_hash=payload_hash),
            )

    def test_replay_still_reverifies_actor(self):
        """合同 12.7.2：停用账号不能凭既有 request_id 读取结果。"""
        auth = _FakeAuth(error=AuthenticationError("当前登录身份已失效，请重新登录"))

        with self.assertRaises(AuthenticationError):
            self._replay(auth, lambda payload_hash: _Record(payload_hash=payload_hash))

        self.assertEqual(_FakeOperationRepo.created, [])

    def test_record_uses_verified_actor_id(self):
        """操作记录写复核后的身份，不直接信任调用方传入的 actor。

        真实 verify_actor 遇到身份不一致会直接抛错；这里用替身固定服务层只信复核结果。
        """
        auth = _FakeAuth(actor=_actor(account_id=99))

        MemberService(auth).create_member(None, _actor(account_id=10), MemberInput(name="张三", phone=None), REQUEST_ID)

        self.assertEqual(_FakeOperationRepo.created[0]["actor_id"], 99)

    def test_replay_when_original_member_missing_raises_storage_error(self):
        """命中记录但原会员行缺失，属于存储不一致，不能当成未命中重新建档。"""
        with self.assertRaises(StorageError):
            self._replay(_FakeAuth(), lambda payload_hash: _Record(payload_hash=payload_hash, result_id=999))

        self.assertEqual(_FakeOperationRepo.created, [])


class GetMemberByRequestTest(MemberServiceTestBase):
    def test_missing_record_raises_not_found(self):
        service = MemberService(_FakeAuth())
        with self.assertRaises(NotFoundError):
            service.get_member_by_request(None, _actor(), REQUEST_ID)

    def test_record_of_other_actor_raises_not_found(self):
        """合同 12.3.1：只有原操作者和管理员可见，前台同行、会员和教练都按不可见处理。"""
        _FakeOperationRepo.existing = _Record(actor_id=99)
        # 原会员行存在：若其他身份被放行，这里会返回视图而不是抛错。
        _FakeMemberRepo.rows[7] = _member()
        service = MemberService(_FakeAuth())
        for actor in (_actor(account_id=10), _actor(role="member", member_id=7), _actor(role="coach")):
            with self.subTest(role=actor.role), self.assertRaises(NotFoundError):
                service.get_member_by_request(None, actor, REQUEST_ID)

    def test_operation_mismatch_raises_conflict(self):
        _FakeOperationRepo.existing = _Record(operation="sell_gym_card", actor_id=10)
        service = MemberService(_FakeAuth())
        with self.assertRaises(ConflictError):
            service.get_member_by_request(None, _actor(account_id=10), REQUEST_ID)

    def test_invisible_request_reports_not_found_before_operation_mismatch(self):
        """合同 12.7.1：先复核可见范围，操作类型不匹配不得泄露编号归属。"""
        _FakeOperationRepo.existing = _Record(operation="sell_gym_card", actor_id=99)
        service = MemberService(_FakeAuth())
        with self.assertRaises(NotFoundError):
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

    def test_rejects_non_canonical_request_id(self):
        """合同 12.8.1：request_id 严格校验 UUID 规范形式。"""
        service = MemberService(_FakeAuth())
        for bad in (REQUEST_ID.upper(), "not-a-uuid", None):
            with self.subTest(request_id=bad), self.assertRaises(InvalidInputError):
                service.get_member_by_request(None, _actor(), bad)

    def test_missing_original_member_raises_not_found(self):
        _FakeOperationRepo.existing = _Record(actor_id=10, result_id=999)
        service = MemberService(_FakeAuth())
        with self.assertRaises(NotFoundError):
            service.get_member_by_request(None, _actor(account_id=10), REQUEST_ID)


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
        for role in ("receptionist", "admin"):
            with self.subTest(role=role):
                self.assertEqual(service.get_member(None, _actor(role=role), 7).id, 7)

    def test_maps_archived_member_fields(self):
        """合同 12.2.2：MemberView 的状态、归档时刻和两个时间戳逐一取自档案行。"""
        service = self._service_with_member()
        _FakeMemberRepo.rows[7] = _member(7, status="archived", archived_at=LATER)

        view = service.get_member(None, _actor(), 7)

        self.assertEqual(view.status, "archived")
        self.assertEqual(view.archived_at, LATER)
        self.assertEqual(view.created_at, NOW)
        self.assertEqual(view.updated_at, LATER)

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

    def test_rejects_invalid_member_ids(self):
        """合同 12.8.1：编号为 1 至 2^63-1 的整数，拒绝 bool、0、负数和非整数。"""
        service = self._service_with_member()
        for bad in (True, 0, -1, 2**63, "7", 7.0):
            with self.subTest(member_id=bad), self.assertRaises(InvalidInputError):
                service.get_member(None, _actor(), bad)


class ListMembersTest(MemberServiceTestBase):
    def test_staff_filter_is_passed_through(self):
        _FakeMemberRepo.list_result = ([_member(7)], 1)
        service = MemberService(_FakeAuth())
        query = MemberQuery(member_id=7, keyword="张", status="active", paging=PageRequest(page=2, page_size=5))

        for role in ("receptionist", "admin"):
            with self.subTest(role=role):
                page = service.list_members(None, _actor(role=role), query)

                self.assertEqual(page.total, 1)
                self.assertEqual(page.page, 2)
                self.assertEqual(page.page_size, 5)
                self.assertEqual([v.id for v in page.items], [7])
                scoped = _FakeMemberRepo.last_query
                self.assertEqual((scoped.member_id, scoped.keyword, scoped.status), (7, "张", "active"))

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
            PageRequest(page=True),
            PageRequest(page_size="20"),
            None,
        ):
            with self.subTest(paging=paging), self.assertRaises(InvalidInputError):
                service.list_members(None, _actor(), MemberQuery(paging=paging))

    def test_rejects_invalid_filters(self):
        """合同 12.8.1：状态只接受 active/archived，关键词必须是字符串；非法筛选在触库前拒绝。"""
        service = MemberService(_FakeAuth())
        for query in (
            MemberQuery(status="enabled"),
            MemberQuery(keyword=123),
            MemberQuery(keyword=None),
            None,
        ):
            with self.subTest(query=query), self.assertRaises(InvalidInputError):
                service.list_members(None, _actor(), query)
        self.assertIsNone(_FakeMemberRepo.last_query)

    def test_rejects_invalid_member_id_filter(self):
        """合同 12.8.1：按编号筛选同样校验 1 至 2^63-1 的整数并拒绝 bool，在触库前拒绝。"""
        service = MemberService(_FakeAuth())
        for bad in (True, 0, -1, 2**63, "7", 7.0):
            with self.subTest(member_id=bad), self.assertRaises(InvalidInputError):
                service.list_members(None, _actor(), MemberQuery(member_id=bad, paging=PageRequest()))
        self.assertIsNone(_FakeMemberRepo.last_query)

    def test_member_without_linked_profile_is_denied(self):
        """复核出的会员身份没有档案时按拒绝处理，不能退化成查询全部会员。

        真实 verify_actor 对缺少关联档案的会员账号会直接抛错；这里用替身固定服务层的自保分支。
        """
        auth = _FakeAuth(actor=_actor(role="member", member_id=None))

        with self.assertRaises(PermissionDenied):
            MemberService(auth).list_members(
                None, _actor(role="member", member_id=7), MemberQuery(paging=PageRequest())
            )

        self.assertIsNone(_FakeMemberRepo.last_query)

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

    def test_admin_can_update_member(self):
        """合同 12.3.1：改资料权限是前台与管理员。"""
        _FakeMemberRepo.rows[7] = _member(7)
        service = MemberService(_FakeAuth())

        view = service.update_member(None, _actor(role="admin"), 7, MemberInput(name="李四", phone=None))

        self.assertEqual(view.id, 7)
        self.assertEqual(_FakeMemberRepo.calls, ["lock", "update"])

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
