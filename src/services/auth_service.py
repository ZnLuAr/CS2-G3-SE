"""账号与权限服务。"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.config import LogConfig
from src.db.account_repo import AccountRepository
from src.errors.business import (
    AuthenticationError,
    ConflictError,
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
)
from src.errors.storage import StorageError
from src.logging.snapshots import query_log_snapshot, read_log_snapshot
from src.models.account import Account
from src.models.contracts import (
    AccountInput,
    AccountView,
    Actor,
    CoachAccountLinkInput,
    LogEntry,
    LogQuery,
    LogSnapshot,
    MemberAccountLinkInput,
    NamedQuery,
    Page,
    PageRequest,
    Role,
)
from src.security.passwords import PASSWORD_PATTERN, hash_password, verify_password

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


USERNAME_PATTERN = re.compile(r"[a-z0-9_]{3,50}")
_ROLES: tuple[Role, ...] = ("member", "coach", "receptionist", "admin")
_AUTH_FAILED = "用户名或密码不正确"
_IDENTITY_FAILED = "当前登录身份已失效，请重新登录"


def _positive_id(value: int, label: str) -> int:
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise InvalidInputError(f"{label}必须是有效的正整数")
    return value


def _actor_shape_valid(actor: object) -> bool:
    """复核进程内 Actor 的字段类型和角色档案不变量。"""
    if not isinstance(actor, Actor):
        return False
    if type(actor.account_id) is not int or not 1 <= actor.account_id <= 2**63 - 1:
        return False
    if actor.role not in _ROLES:
        return False
    if any(
        value is not None and (type(value) is not int or not 1 <= value <= 2**63 - 1)
        for value in (actor.member_id, actor.coach_id)
    ):
        return False
    if actor.role == "member":
        return actor.member_id is not None and actor.coach_id is None
    if actor.role == "coach":
        return actor.coach_id is not None and actor.member_id is None
    return actor.member_id is None and actor.coach_id is None


class AuthService:
    """账号与权限服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现遵守 docs/architecture/backend.md 的返回、异常、权限和事务约定。
    业务方法共用传入 Session，由调用方 Logic 提交或回滚。
    """

    def __init__(self, *, log_config: LogConfig) -> None:
        """接收配置解析后的日志配置。"""
        self._log_config = log_config

    def login(self, session: Session, username: str, password: str) -> Actor:
        """校验凭据并取得当前操作者。

        用户名去首尾空白并转小写，只允许 3–50 位 ASCII 字母、数字和下划线。
        密码原样处理，允许 A–Z、a–z、0–9、短横线和下划线，共 6–32 位。
        member 角色关联唯一会员档案，active 与 archived 档案均可登录；coach 角色关联启用教练档案。
        返回：Actor。不修改业务数据。
        异常：格式、凭据、账号状态或档案关联无效时抛 AuthenticationError；存储故障抛 StorageError。
        """
        if not isinstance(username, str):
            raise AuthenticationError(_AUTH_FAILED)
        normalized = username.strip().lower()
        if USERNAME_PATTERN.fullmatch(normalized) is None:
            raise AuthenticationError(_AUTH_FAILED)
        if not isinstance(password, str) or PASSWORD_PATTERN.fullmatch(password) is None:
            raise AuthenticationError(_AUTH_FAILED)

        repository = AccountRepository(session)
        try:
            account = repository.find_by_username(normalized)
            if account is not None:
                # 按编号锁定后再校验，避免与停用、角色变更并发时读到旧状态。
                account = repository.lock(account.id)
        except SQLAlchemyError as exc:
            raise StorageError("登录失败") from exc
        if account is None:
            raise AuthenticationError(_AUTH_FAILED)

        if not verify_password(password, account.password_hash):
            raise AuthenticationError(_AUTH_FAILED)
        if not account.is_active:
            raise AuthenticationError(_AUTH_FAILED)

        try:
            # 登录事务的第一条普通读在账号锁之前，读视图可能早于档案移交；
            # 锁定档案后复核关联行，避免返回移交前的档案编号。
            member, coach = repository.lock_profile_links(account.id, recheck=True)
        except SQLAlchemyError as exc:
            raise StorageError("登录失败") from exc

        if account.role == "member":
            if member is None or coach is not None:
                raise AuthenticationError(_AUTH_FAILED)
            return Actor(
                account_id=account.id, role="member",
                member_id=member.id, coach_id=None,
            )
        if account.role == "coach":
            if coach is None or not coach.is_active or member is not None:
                raise AuthenticationError(_AUTH_FAILED)
            return Actor(
                account_id=account.id, role="coach",
                member_id=None, coach_id=coach.id,
            )
        if account.role in {"receptionist", "admin"}:
            if member is not None or coach is not None:
                raise AuthenticationError(_AUTH_FAILED)
            return Actor(
                account_id=account.id, role=account.role,
                member_id=None, coach_id=None,
            )
        raise AuthenticationError(_AUTH_FAILED)

    def create_account(self, session: Session, actor: Actor, data: AccountInput) -> AccountView:
        """管理员创建启用账号，密码以 Argon2id 哈希保存。

        返回：AccountView。数据变更由调用方 Logic 在本次事务中提交。
        异常：非管理员抛 PermissionDenied；输入非法抛 InvalidInputError；
        用户名重复抛 ConflictError；身份或存储故障按账号服务统一异常处理。
        """
        current = self._require_admin(session, actor)
        if not isinstance(data, AccountInput):
            raise InvalidInputError("账号输入格式不正确")
        username = self._normalize_new_username(data.username)
        if data.role not in _ROLES:
            raise InvalidInputError("账号角色不正确")
        if not isinstance(data.password, str) or PASSWORD_PATTERN.fullmatch(data.password) is None:
            raise InvalidInputError("密码必须为 6-32 位字母、数字、下划线或短横线")

        repository = AccountRepository(session)
        try:
            if repository.find_by_username(username) is not None:
                raise ConflictError("用户名已存在")
            password_hash = hash_password(data.password)
            account = repository.create(
                username=username, password_hash=password_hash, role=data.role,
            )
        except IntegrityError as exc:
            raise ConflictError("用户名已存在") from exc
        except SQLAlchemyError as exc:
            raise StorageError("创建账号失败") from exc
        return AccountView(
            id=account.id,
            username=account.username,
            role=account.role,
            is_active=account.is_active,
            member_id=None,
            coach_id=None,
        )

    def get_account(self, session: Session, actor: Actor, account_id: int) -> AccountView:
        """管理员查询账号详情；不返回密码哈希。

        异常：非管理员抛 PermissionDenied；账号不存在抛 NotFoundError。
        """
        self._require_admin(session, actor)
        _positive_id(account_id, "账号编号")
        repository = AccountRepository(session)
        try:
            view = repository.get_view(account_id)
        except SQLAlchemyError as exc:
            raise StorageError("查询账号失败") from exc
        if view is None:
            raise NotFoundError("账号不存在")
        return view

    def list_accounts(self, session: Session, actor: Actor, query: NamedQuery) -> Page[AccountView]:
        """管理员按用户名关键字、启用状态和分页查询账号。

        返回：按账号 id 升序稳定分页的 Page[AccountView]。
        异常：非管理员抛 PermissionDenied；条件非法抛 InvalidInputError。
        """
        self._require_admin(session, actor)
        if not isinstance(query, NamedQuery):
            raise InvalidInputError("账号查询条件格式不正确")
        if not isinstance(query.keyword, str) or len(query.keyword.strip()) > 50:
            raise InvalidInputError("用户名关键字最多 50 个字符")
        if query.is_active is not None and type(query.is_active) is not bool:
            raise InvalidInputError("启用状态筛选必须是布尔值")
        if not isinstance(query.paging, PageRequest):
            raise InvalidInputError("分页条件格式不正确")
        if (
            type(query.paging.page) is not int or query.paging.page < 1
            or type(query.paging.page_size) is not int
            or not 1 <= query.paging.page_size <= 100
        ):
            raise InvalidInputError("分页条件必须是第 1 页起、每页 1～100 条")

        from dataclasses import replace

        normalized = replace(
            query,
            keyword=query.keyword.strip().lower(),
        )
        try:
            return AccountRepository(session).list(normalized)
        except SQLAlchemyError as exc:
            raise StorageError("查询账号列表失败") from exc

    def set_account_active(self, session: Session, actor: Actor, account_id: int, active: bool) -> AccountView:
        """停用或恢复账号；停用最后一名启用管理员抛 InvalidState。

        操作者和目标账号按编号升序在同一条锁定当前读中取得；停用管理员时，
        同一条查询还包含全部启用管理员。锁内复核操作者、目标状态和管理员数量。
        返回：AccountView。数据变更由调用方 Logic 在本次事务中提交。
        """
        _positive_id(account_id, "账号编号")
        if type(active) is not bool:
            raise InvalidInputError("启用状态必须是布尔值")
        if not _actor_shape_valid(actor):
            raise AuthenticationError(_IDENTITY_FAILED)

        repository = AccountRepository(session)
        try:
            rows = repository.lock_active_admins((actor.account_id, account_id))
        except SQLAlchemyError as exc:
            raise StorageError("停用或恢复账号失败") from exc
        self._verify_locked_admin(session, actor, rows)

        target = next((row for row in rows if row.id == account_id), None)
        if target is None:
            raise NotFoundError("账号不存在")
        if not active and target.role == "admin" and target.is_active:
            active_admins = sum(
                1 for row in rows if row.role == "admin" and row.is_active
            )
            if active_admins <= 1:
                raise InvalidState("系统必须保留至少一名启用的管理员")

        try:
            if target.is_active != active:
                return repository.set_active(account_id, active)
            view = repository.get_view(account_id)
        except SQLAlchemyError as exc:
            raise StorageError("停用或恢复账号失败") from exc
        if view is None:
            raise NotFoundError("账号不存在")
        return view

    def link_member(self, session: Session, actor: Actor, data: MemberAccountLinkInput) -> AccountView:
        """将会员档案关联到会员账号。

        操作者账号和目标账号按编号升序锁定，再锁定会员档案；数据库双向唯一约束作为最终防重。
        账号角色不是 member 抛 InvalidState；重复关联返回当前结果。
        """
        if not isinstance(data, MemberAccountLinkInput):
            raise InvalidInputError("会员账号关联输入格式不正确")
        _positive_id(data.account_id, "账号编号")
        _positive_id(data.member_id, "会员编号")
        repository = AccountRepository(session)
        target = self._lock_target_account(session, actor, data.account_id)
        if target.role != "member":
            raise InvalidState("目标账号不是会员账号")

        try:
            member = repository.lock_member(data.member_id)
        except SQLAlchemyError as exc:
            raise StorageError("关联会员档案失败") from exc
        if member is None:
            raise NotFoundError("会员档案不存在")

        try:
            current_member_id = repository.get_member_account_id(data.account_id)
            if current_member_id == data.member_id:
                return self._view_for(repository, target)
            if current_member_id is not None:
                raise ConflictError("目标账号已关联其他会员档案")
            if repository.get_member_link_owner(data.member_id) is not None:
                raise ConflictError("会员档案已关联其他账号")
            repository.create_member_link(
                account_id=data.account_id,
                member_id=data.member_id,
                linked_by=actor.account_id,
                linked_at=datetime.now(timezone.utc),
            )
            return self._view_for(repository, target)
        except IntegrityError as exc:
            raise ConflictError("会员档案已关联其他账号") from exc
        except SQLAlchemyError as exc:
            raise StorageError("关联会员档案失败") from exc

    def link_coach(self, session: Session, actor: Actor, data: CoachAccountLinkInput) -> AccountView:
        """将教练档案关联到教练账号；重复关联返回当前结果。"""
        if not isinstance(data, CoachAccountLinkInput):
            raise InvalidInputError("教练账号关联输入格式不正确")
        _positive_id(data.account_id, "账号编号")
        _positive_id(data.coach_id, "教练编号")
        repository = AccountRepository(session)
        target = self._lock_target_account(session, actor, data.account_id)
        if target.role != "coach":
            raise InvalidState("目标账号不是教练账号")

        try:
            coach = repository.lock_coach(data.coach_id)
        except SQLAlchemyError as exc:
            raise StorageError("关联教练档案失败") from exc
        if coach is None:
            raise NotFoundError("教练档案不存在")

        try:
            current_coach_id = repository.get_coach_account_id(data.account_id)
            if current_coach_id == data.coach_id:
                return self._view_for(repository, target)
            if not coach.is_active:
                raise InvalidState("教练档案已停用")
            if current_coach_id is not None:
                raise ConflictError("目标账号已关联其他教练档案")
            if repository.get_coach_link_owner(data.coach_id) is not None:
                raise ConflictError("教练档案已关联其他账号")
            repository.create_coach_link(
                account_id=data.account_id,
                coach_id=data.coach_id,
                linked_by=actor.account_id,
                linked_at=datetime.now(timezone.utc),
            )
            return self._view_for(repository, target)
        except IntegrityError as exc:
            raise ConflictError("教练档案已关联其他账号") from exc
        except SQLAlchemyError as exc:
            raise StorageError("关联教练档案失败") from exc

    def relink_member(self, session: Session, actor: Actor, account_id: int, member_id: int) -> AccountView:
        """管理员为会员账号更换关联档案，原子释放旧关联并建立新关联。

        先升序锁操作者与目标账号，再升序锁旧、新会员档案。
        新档案已被其他账号关联时抛 ConflictError。
        """
        _positive_id(account_id, "账号编号")
        _positive_id(member_id, "会员编号")
        repository = AccountRepository(session)
        target = self._lock_target_account(session, actor, account_id)
        if target.role != "member":
            raise InvalidState("目标账号不是会员账号")

        try:
            current_member_id = repository.get_member_account_id(account_id)
            identifiers = tuple(sorted({
                value for value in (current_member_id, member_id) if value is not None
            }))
            members = {item.id: item for item in repository.lock_members(identifiers)}
            if member_id not in members:
                raise NotFoundError("会员档案不存在")
            if current_member_id == member_id:
                return self._view_for(repository, target)
            owner = repository.get_member_link_owner(member_id)
            if owner is not None and owner != account_id:
                raise ConflictError("会员档案已关联其他账号")
            if current_member_id is not None:
                repository.delete_member_link(account_id)
            repository.create_member_link(
                account_id=account_id,
                member_id=member_id,
                linked_by=actor.account_id,
                linked_at=datetime.now(timezone.utc),
            )
            return self._view_for(repository, target)
        except IntegrityError as exc:
            raise ConflictError("会员档案已关联其他账号") from exc
        except SQLAlchemyError as exc:
            raise StorageError("移交会员账号关联失败") from exc

    def relink_coach(self, session: Session, actor: Actor, account_id: int, coach_id: int) -> AccountView:
        """管理员为教练账号更换关联档案，返回最新 AccountView。

        输入目标账号和新教练编号；先升序锁操作者与目标账号，再升序锁旧、新教练档案。
        同一事务释放原关联并建立新关联；教练停用抛 InvalidState，档案已关联其他账号抛 ConflictError。
        """
        _positive_id(account_id, "账号编号")
        _positive_id(coach_id, "教练编号")
        repository = AccountRepository(session)
        target = self._lock_target_account(session, actor, account_id)
        if target.role != "coach":
            raise InvalidState("目标账号不是教练账号")

        try:
            current_coach_id = repository.get_coach_account_id(account_id)
            identifiers = tuple(sorted({
                value for value in (current_coach_id, coach_id) if value is not None
            }))
            coaches = {item.id: item for item in repository.lock_coaches(identifiers)}
            if coach_id not in coaches:
                raise NotFoundError("教练档案不存在")
            if not coaches[coach_id].is_active:
                raise InvalidState("教练档案已停用")
            if current_coach_id == coach_id:
                return self._view_for(repository, target)
            owner = repository.get_coach_link_owner(coach_id)
            if owner is not None and owner != account_id:
                raise ConflictError("教练档案已关联其他账号")
            if current_coach_id is not None:
                repository.delete_coach_link(account_id)
            repository.create_coach_link(
                account_id=account_id,
                coach_id=coach_id,
                linked_by=actor.account_id,
                linked_at=datetime.now(timezone.utc),
            )
            return self._view_for(repository, target)
        except IntegrityError as exc:
            raise ConflictError("教练档案已关联其他账号") from exc
        except SQLAlchemyError as exc:
            raise StorageError("移交教练账号关联失败") from exc

    def verify_actor(self, session: Session, actor: Actor) -> Actor:
        """以当前 Session 锁定并复核账号、角色与关联，返回可信 Actor。

        先锁当前账号，再通过 lock_profile_links 锁定并读取关联会员或教练的完整记录，
        以锁内记录复核账号与教练的启用状态；归档会员仍可返回可信身份。
        锁持有到调用方 Logic 结束事务。
        账号停用或档案移交一旦提交，旧 Actor 的后续复核抛 AuthenticationError。
        数据库读取或锁定失败抛 StorageError，提示只包含身份复核失败信息；事务由 Logic 回滚。
        """
        if (
            not isinstance(actor, Actor) or type(actor.account_id) is not int
            or not 1 <= actor.account_id <= 2**63 - 1
            or actor.role not in ("admin", "receptionist", "member", "coach")
            or any(value is not None and (type(value) is not int or not 1 <= value <= 2**63 - 1)
                   for value in (actor.member_id, actor.coach_id))
        ):
            raise AuthenticationError("当前登录身份已失效，请重新登录")
        repository = AccountRepository(session)
        try:
            account = repository.lock(actor.account_id)
            if account is None or not account.is_active or account.role != actor.role:
                raise AuthenticationError("当前登录身份已失效，请重新登录")
            member, coach = repository.lock_profile_links(actor.account_id)
        except SQLAlchemyError as exc:
            raise StorageError("复核当前登录身份失败") from exc
        if account.role == "member":
            valid = member is not None and coach is None
        elif account.role == "coach":
            valid = coach is not None and coach.is_active and member is None
        else:
            valid = member is None and coach is None
        current = Actor(
            account_id=account.id, role=account.role,
            member_id=None if member is None else member.id,
            coach_id=None if coach is None else coach.id,
        )
        if not valid or current != actor:
            raise AuthenticationError("当前登录身份已失效，请重新登录")
        return current

    def open_log_snapshot(self, session: Session, actor: Actor) -> LogSnapshot:
        """取得管理员本次日志浏览使用的固定快照。

        返回：LogSnapshot；非管理员抛 PermissionDenied，读取失败抛 ResourceError。
        """
        self._require_admin(session, actor)
        return read_log_snapshot(
            self._log_config.directory,
            backup_count=self._log_config.backup_count,
        )

    def query_logs(
        self, session: Session,
        actor: Actor,
        query: LogQuery,
        *,
        snapshot: LogSnapshot,
    ) -> Page[LogEntry]:
        """查询日志记录；每次筛选和翻页都重新验证身份。

        权限：只有管理员可以查询日志。
        返回：Page[LogEntry]；非法条件抛 InvalidInputError，日志资源不可用抛 ResourceError。
        """
        self._require_admin(session, actor)
        return query_log_snapshot(snapshot, query)

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _require_admin(self, session: Session, actor: Actor) -> Actor:
        current = self.verify_actor(session, actor)
        if current.role != "admin":
            raise PermissionDenied("只有管理员可以执行该操作")
        return current

    def _lock_target_account(
        self, session: Session, actor: Actor, account_id: int,
    ) -> Account:
        """按编号升序锁定操作者与目标账号，并复核操作者身份和管理员角色。"""
        if not _actor_shape_valid(actor):
            raise AuthenticationError(_IDENTITY_FAILED)
        repository = AccountRepository(session)
        try:
            rows = repository.lock_many((actor.account_id, account_id))
        except SQLAlchemyError as exc:
            raise StorageError("锁定账号失败") from exc
        self._verify_locked_admin(session, actor, rows)
        target = next((row for row in rows if row.id == account_id), None)
        if target is None:
            raise NotFoundError("账号不存在")
        return target

    def _verify_locked_admin(
        self, session: Session, actor: Actor, rows: tuple[Account, ...],
    ) -> Account:
        """在已取得的账号锁集合内复核操作者账号、角色和档案关联。"""
        if not _actor_shape_valid(actor):
            raise AuthenticationError(_IDENTITY_FAILED)
        current = next((row for row in rows if row.id == actor.account_id), None)
        if current is None or not current.is_active or current.role != actor.role:
            raise AuthenticationError(_IDENTITY_FAILED)
        repository = AccountRepository(session)
        try:
            member, coach = repository.lock_profile_links(actor.account_id)
        except SQLAlchemyError as exc:
            raise StorageError("复核当前登录身份失败") from exc
        # 先按锁内账号和档案关联复核身份，再判管理员角色。
        # 档案移交或角色档案不变量失效时统一抛 AuthenticationError，
        # 与 verify_actor 的旧身份处理一致；合法会员或教练访问管理操作仍报权限不足。
        current_identity = Actor(
            account_id=current.id,
            role=current.role,
            member_id=None if member is None else member.id,
            coach_id=None if coach is None else coach.id,
        )
        if not _actor_shape_valid(current_identity) or current_identity != actor:
            raise AuthenticationError(_IDENTITY_FAILED)
        if current.role != "admin":
            raise PermissionDenied("只有管理员可以执行该操作")
        return current

    def _view_for(self, repository: AccountRepository, account: Account) -> AccountView:
        """用锁内账号资料和最新关联构造 AccountView。"""
        actor = repository.get_actor(account.id)
        if actor is None:
            raise NotFoundError("账号不存在")
        return AccountView(
            id=account.id,
            username=account.username,
            role=account.role,
            is_active=account.is_active,
            member_id=actor.member_id,
            coach_id=actor.coach_id,
        )

    @staticmethod
    def _normalize_new_username(value: object) -> str:
        if not isinstance(value, str):
            raise InvalidInputError("用户名格式不正确")
        normalized = value.strip().lower()
        if USERNAME_PATTERN.fullmatch(normalized) is None:
            raise InvalidInputError("用户名必须为 3-50 位字母、数字或下划线")
        return normalized
