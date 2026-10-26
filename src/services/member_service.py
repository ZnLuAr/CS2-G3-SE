"""会员档案服务；建档、按请求编号核实与详情查询已实现。

其余方法（列表、改资料、启停）属 MEM-02 / MEM-03 / MEM-06，保留显式占位。
权限在服务层校验：调用方传入的 actor 先经 AuthService.verify_actor 在当前事务内复核。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import TYPE_CHECKING

from src.db.member_repo import MemberRepository
from src.db.operation_repo import OperationRepository
from src.errors.business import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDenied,
)
from src.models.contracts import (
    Actor,
    MemberInput,
    MemberQuery,
    MemberStatus,
    MemberView,
    Page,
    PageRequest,
)
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.models.member import Member
    from src.models.operation import OperationRecord

# 可以登记会员档案的角色；会员与教练不能代替前台建档。
_MEMBER_CREATE_ROLES = ("receptionist", "admin")
# 可以按编号查看任意会员档案的角色；会员只能看本人。
_MEMBER_READ_ALL_ROLES = ("receptionist", "admin")


class MemberService:
    """会员档案服务。

    actor 来自可信登录会话，每个方法仍先复核身份与数据归属。
    写操作不提交：数据变更由调用方 Logic 在本次事务中提交或回滚。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_member(self, session: Session, actor: Actor, data: MemberInput, request_id: str) -> MemberView:
        """创建会员档案（幂等）。

        相同 request_id、相同操作者与相同内容重试时返回原会员，不重复建档。
        返回：MemberView。
        异常：InvalidInputError 输入不合法；PermissionDenied 角色不允许；
        ConflictError 请求编号已被其他请求使用；StorageError 原记录缺失。
        """
        current = self._auth.verify_actor(session, actor)
        if current.role not in _MEMBER_CREATE_ROLES:
            raise PermissionDenied("当前角色不能登记会员档案")

        normalized = _normalize_member_input(data)
        canonical_request_id = _normalize_request_id(request_id)
        payload_hash = _payload_hash(normalized)

        members = MemberRepository(session)
        operations = OperationRepository(session)

        existing = operations.get_by_request(canonical_request_id)
        if existing is not None:
            return self._replay_create(existing, current, payload_hash, members)

        member = members.create(normalized)
        # 12.4.2：取得业务锁后应以锁定当前读复核 operation_records，避免与并发的同编号请求交错；
        # 该步骤依赖 OperationRepository.lock_by_request（当前为占位实现），落地后在此处补上。
        operations.create(
            request_id=canonical_request_id,
            actor_id=current.account_id,
            operation="create_member",
            payload_hash=payload_hash,
            result_id=member.id,
        )
        return _to_view(member)

    def get_member_by_request(self, session: Session, actor: Actor, request_id: str) -> MemberView:
        """按幂等请求编号查会员。

        权限：原操作者本人或管理员（12.3.1 核实接口）。
        返回：MemberView。不修改业务数据。
        异常：InvalidInputError 编号格式不合法；ConflictError 该编号对应其他操作；
        NotFoundError 没有该编号的结果，或结果对当前身份不可见。
        """
        current = self._auth.verify_actor(session, actor)
        canonical_request_id = _normalize_request_id(request_id)

        record = OperationRepository(session).get_by_request(canonical_request_id)
        if record is None:
            raise NotFoundError("该请求编号没有对应的会员建档结果")
        if record.operation != "create_member":
            raise ConflictError("该请求编号对应其他操作")
        if record.actor_id != current.account_id and current.role != "admin":
            raise NotFoundError("该请求编号没有对应的会员建档结果")

        member = MemberRepository(session).get(record.result_id)
        if member is None:
            raise NotFoundError("原请求的会员档案不存在")
        return _to_view(member)

    def get_member(self, session: Session, actor: Actor, member_id: int) -> MemberView:
        """查询会员详情。

        会员只能查看本人；前台与管理员可查看任意会员。教练查看学员资料
        由 BOOK-04 学员名单入口提供，这里拒绝。
        返回：MemberView。不修改业务数据。
        异常：NotFoundError 记录不存在或对操作者不可见。
        """
        current = self._auth.verify_actor(session, actor)
        if not _can_read(current, member_id):
            raise NotFoundError("会员档案不存在")

        member = MemberRepository(session).get(_normalize_member_id(member_id))
        if member is None:
            raise NotFoundError("会员档案不存在")
        return _to_view(member)

    def list_members(self, session: Session, actor: Actor, query: MemberQuery) -> Page[MemberView]:
        """分页查询会员。

        权限：会员只能查到本人档案；前台与管理员可按条件分页；教练不能查询。
        返回：按 id 升序稳定分页的 Page[MemberView]；空结果返回空 Page。
        异常：PermissionDenied 角色不允许；InvalidInputError 筛选或分页参数不合法。
        """
        current = self._auth.verify_actor(session, actor)
        if not isinstance(query, MemberQuery):
            raise InvalidInputError("查询条件不合法")
        paging = _normalize_paging(query.paging)

        if current.role == "member":
            if current.member_id is None:
                raise PermissionDenied("当前登录身份缺少会员档案")
            if query.member_id is not None and query.member_id != current.member_id:
                return Page(items=[], total=0, page=paging.page, page_size=paging.page_size)
            member_id = current.member_id
        elif current.role in _MEMBER_READ_ALL_ROLES:
            member_id = None if query.member_id is None else _normalize_member_id(query.member_id)
        else:
            raise PermissionDenied("当前角色不能查询会员列表")

        keyword = query.keyword if isinstance(query.keyword, str) else None
        if keyword is None:
            raise InvalidInputError("搜索关键词不合法")
        if query.status is not None and query.status not in ("active", "archived"):
            raise InvalidInputError("状态筛选不合法")

        scoped = MemberQuery(
            member_id=member_id,
            keyword=keyword,
            status=query.status,
            paging=paging,
        )
        rows, total = MemberRepository(session).list(scoped)
        return Page(
            items=[_to_view(member) for member in rows],
            total=total,
            page=paging.page,
            page_size=paging.page_size,
        )

    def update_member(self, session: Session, actor: Actor, member_id: int, data: MemberInput) -> MemberView:
        """修改会员资料。

        权限：前台与管理员。完整提交姓名与 phone，先锁档案再写入，返回锁内最新值。
        只改会员档案字段，不动账号、健身房卡与私教课包。
        返回：MemberView。数据变更由调用方 Logic 在本次事务中提交。
        异常：PermissionDenied、NotFoundError、InvalidInputError。
        """
        current = self._auth.verify_actor(session, actor)
        if current.role not in _MEMBER_CREATE_ROLES:
            raise PermissionDenied("当前角色不能修改会员资料")

        target_id = _normalize_member_id(member_id)
        normalized = _normalize_member_input(data)

        members = MemberRepository(session)
        if members.lock(target_id) is None:
            raise NotFoundError("会员档案不存在")
        return _to_view(members.update_profile(target_id, normalized.name, normalized.phone))

    def set_member_status(self, session: Session, actor: Actor, member_id: int, status: MemberStatus) -> MemberView:
        """设置会员状态（启用/归档）。

        返回：MemberView。数据变更由调用方 Logic 在本次事务中提交。
        异常：当前为 NotImplementedError；属于 MEM-06。
        """
        raise NotImplementedError("MemberService.set_member_status 尚未实现")

    # ---------- 内部工具 ----------

    def _replay_create(
        self,
        record: OperationRecord,
        current: Actor,
        payload_hash: str,
        members: MemberRepository,
    ) -> MemberView:
        """核对已存在的请求记录并返回原结果；内容不同时抛冲突。"""
        if (
            record.operation != "create_member"
            or record.actor_id != current.account_id
            or record.payload_hash != payload_hash
        ):
            raise ConflictError("该请求编号已用于其他内容，请使用新的请求编号")

        member = members.get(record.result_id)
        if member is None:
            from src.errors.storage import StorageError

            raise StorageError("原请求的会员档案不存在，无法重放结果")
        return _to_view(member)


# ---------- 校验与转换 ----------

def _normalize_member_input(data: MemberInput) -> MemberInput:
    """去首尾空白并校验长度；联系方式为空串时视为未填写。"""
    if not isinstance(data, MemberInput):
        raise InvalidInputError("会员资料格式不合法")

    name = data.name.strip() if isinstance(data.name, str) else ""
    if not 1 <= len(name) <= 100:
        raise InvalidInputError("姓名不能为空，且不超过 100 个字符")

    phone: str | None
    if data.phone is None:
        phone = None
    elif not isinstance(data.phone, str):
        raise InvalidInputError("联系方式格式不合法")
    else:
        stripped = data.phone.strip()
        if stripped == "":
            phone = None
        elif len(stripped) > 32:
            raise InvalidInputError("联系方式不超过 32 个字符")
        else:
            phone = stripped

    return MemberInput(name=name, phone=phone)


def _normalize_member_id(member_id: int) -> int:
    """会员编号必须是 1 到 2^63-1 的整数，且不接受 bool。"""
    if type(member_id) is not int or not 1 <= member_id <= 2**63 - 1:
        raise InvalidInputError("会员编号不合法")
    return member_id


def _normalize_request_id(request_id: str) -> str:
    """请求编号必须是标准小写 UUID 字符串（36 位、带短横线）。"""
    if not isinstance(request_id, str):
        raise InvalidInputError("请求编号格式不合法")
    try:
        parsed = uuid.UUID(request_id)
    except (AttributeError, TypeError, ValueError) as exc:
        raise InvalidInputError("请求编号格式不合法") from exc
    canonical = str(parsed)
    if canonical != request_id:
        raise InvalidInputError("请求编号必须是标准小写 UUID")
    return canonical


def _payload_hash(data: MemberInput) -> str:
    """按后端合同 12.7.1 计算请求内容摘要。

    规范载荷按合同表内字段顺序写出（create_member 为 name, phone），
    不含 request_id；使用 separators=(",", ":")、ensure_ascii=False，
    再对 UTF-8 字节取 SHA-256 小写十六进制。
    """
    payload = {"name": data.name, "phone": data.phone}
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_paging(paging: PageRequest) -> PageRequest:
    """按后端合同校验分页：page 从 1 开始，page_size 取 1 到 100。"""
    if not isinstance(paging, PageRequest):
        raise InvalidInputError("分页参数不合法")
    if type(paging.page) is not int or paging.page < 1:
        raise InvalidInputError("页码必须是不小于 1 的整数")
    if type(paging.page_size) is not int or not 1 <= paging.page_size <= 100:
        raise InvalidInputError("每页条数必须为 1 到 100")
    return PageRequest(page=paging.page, page_size=paging.page_size)


def _can_read(actor: Actor, member_id: int) -> bool:
    """判断当前身份能否查看目标会员档案。"""
    if actor.role in _MEMBER_READ_ALL_ROLES:
        return True
    if actor.role == "member":
        return actor.member_id == member_id
    return False


def _to_view(member: Member) -> MemberView:
    """把存储模型转换为对外的 MemberView（含归档时刻与两个时间戳）。"""
    return MemberView(
        id=member.id,
        name=member.name,
        phone=member.phone,
        status=member.status,
        archived_at=member.archived_at,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )
