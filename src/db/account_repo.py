"""账号数据访问。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import text

from src.errors.storage import StorageError
from src.models.account import Account
from src.models.contracts import AccountView, Actor, NamedQuery, Page, Role
from src.models.course import Coach
from src.models.member import Member

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _account(row) -> Account:
    return Account(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        role=row["role"],
        is_active=bool(row["is_active"]),
        created_at=_utc(row["created_at"]),
        updated_at=_utc(row["updated_at"]),
    )


def _member(row) -> Member:
    return Member(
        id=row["id"],
        name=row["name"],
        phone=row["phone"],
        status=row["status"],
        archived_at=_utc(row["archived_at"]),
        created_at=_utc(row["created_at"]),
        updated_at=_utc(row["updated_at"]),
    )


def _coach(row) -> Coach:
    return Coach(
        id=row["id"],
        name=row["name"],
        phone=row["phone"],
        is_active=bool(row["is_active"]),
        created_at=_utc(row["created_at"]),
        updated_at=_utc(row["updated_at"]),
    )


class AccountRepository:
    """账号数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def _locked_sql(self, sql: str) -> str:
        """SQLite 单元测试不支持 FOR UPDATE；其余数据库使用锁定当前读。"""
        if self._session.get_bind().dialect.name == "sqlite":
            return sql
        return sql + " FOR UPDATE"

    def get(self, account_id: int) -> Account | None:
        """按编号读取账号；包含密码哈希，仅供服务内部使用。"""
        row = self._session.execute(
            text("SELECT * FROM accounts WHERE id = :id"), {"id": account_id},
        ).mappings().first()
        return None if row is None else _account(row)

    def get_view(self, account_id: int) -> AccountView | None:
        """读取可展示的账号资料和关联档案编号，不返回密码哈希。"""
        row = self._session.execute(text(
            "SELECT a.id, a.username, a.role, a.is_active, ml.member_id, cl.coach_id "
            "FROM accounts a "
            "LEFT JOIN member_account_links ml ON ml.account_id = a.id "
            "LEFT JOIN coach_account_links cl ON cl.account_id = a.id "
            "WHERE a.id = :id"
        ), {"id": account_id}).mappings().first()
        if row is None:
            return None
        return AccountView(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            member_id=row["member_id"],
            coach_id=row["coach_id"],
        )

    def lock(self, account_id: int) -> Account | None:
        """在当前事务锁定账号并读取最新 Account，不存在返回 None。

        单账号流程使用本方法；多账号流程使用 lock_many 一次性取得完整锁集合。
        不提交，锁持有到调用方事务结束。
        """
        row = self._session.execute(
            text(self._locked_sql("SELECT * FROM accounts WHERE id = :id")),
            {"id": account_id},
        ).mappings().first()
        return None if row is None else _account(row)

    def lock_many(self, account_ids: tuple[int, ...]) -> tuple[Account, ...]:
        """去重后按账号编号升序锁定指定账号，并读取最新 Account。

        必须通过一条带 ORDER BY id 的锁定当前读取得全部行；不提交。
        """
        identifiers = tuple(sorted(set(account_ids)))
        if not identifiers:
            return ()
        placeholders = ", ".join(f":id{index}" for index in range(len(identifiers)))
        parameters = {f"id{index}": value for index, value in enumerate(identifiers)}
        rows = self._session.execute(
            text(self._locked_sql(
                f"SELECT * FROM accounts WHERE id IN ({placeholders}) ORDER BY id"
            )),
            parameters,
        ).mappings().all()
        return tuple(_account(row) for row in rows)

    def lock_active_admins(
        self, account_ids: tuple[int, ...],
    ) -> tuple[Account, ...]:
        """按账号编号升序锁定指定账号与全部启用管理员的并集。

        指定账号不论角色都锁定；条件中的启用管理员只含 role = 'admin'。
        未指定的会员、教练或前台账号不在返回结果中，但锁定读会锁住执行计划扫过的行，
        不保证它们在事务期间可用。
        使用一条锁定当前读，供账号停用同时锁住操作者、目标账号并复核最后一名管理员。
        """
        identifiers = tuple(sorted(set(account_ids)))
        conditions = ["(is_active = 1 AND role = 'admin')"]
        parameters: dict[str, object] = {}
        if identifiers:
            placeholders = ", ".join(f":id{index}" for index in range(len(identifiers)))
            conditions.append(f"id IN ({placeholders})")
            parameters.update({
                f"id{index}": value for index, value in enumerate(identifiers)
            })
        rows = self._session.execute(
            text(self._locked_sql(
                f"SELECT * FROM accounts WHERE ({' OR '.join(conditions)}) ORDER BY id"
            )),
            parameters,
        ).mappings().all()
        return tuple(_account(row) for row in rows)

    def find_by_username(self, username: str) -> Account | None:
        """按规范化用户名查账号；未找到返回 None。"""
        row = self._session.execute(
            text("SELECT * FROM accounts WHERE username = :username"),
            {"username": username},
        ).mappings().first()
        return None if row is None else _account(row)

    def get_actor(self, account_id: int) -> Actor | None:
        """读取账号角色及关联档案编号，供身份复核。"""
        row = self._session.execute(text(
            "SELECT a.id, a.role, ml.member_id, cl.coach_id "
            "FROM accounts a "
            "LEFT JOIN member_account_links ml ON ml.account_id = a.id "
            "LEFT JOIN coach_account_links cl ON cl.account_id = a.id "
            "WHERE a.id = :id"
        ), {"id": account_id}).mappings().first()
        if row is None:
            return None
        return Actor(
            account_id=row["id"],
            role=row["role"],
            member_id=row["member_id"],
            coach_id=row["coach_id"],
        )

    def lock_profile_links(
        self, account_id: int, *, recheck: bool = False,
    ) -> tuple[Member | None, Coach | None]:
        """账号行已加锁后，读取关联编号并按固定顺序锁定完整档案。

        先普通读取两类关联编号，再按主键依次锁定存在的会员和教练行；
        没有关联时不加间隙锁。账号行锁已串行化同一账号的关联变更，
        双向唯一约束负责防重。返回：(member, coach)；未关联项为 None。

        recheck=True 用于登录：此时事务内已有更早的普通读，REPEATABLE READ
        的读视图可能读到账号锁之前的旧关联。锁定档案行后再对已存在的关联行
        做一次锁定读复核；行已删除按未关联处理，指向新档案时锁定并返回新档案。
        锁定读按唯一键命中已存在的行，只加记录锁，不加间隙锁。
        """
        member_id = self._session.execute(
            text("SELECT member_id FROM member_account_links WHERE account_id = :id"),
            {"id": account_id},
        ).scalar_one_or_none()
        coach_id = self._session.execute(
            text("SELECT coach_id FROM coach_account_links WHERE account_id = :id"),
            {"id": account_id},
        ).scalar_one_or_none()
        member = None if member_id is None else self.lock_member(member_id)
        coach = None if coach_id is None else self.lock_coach(coach_id)
        if recheck:
            member = self._recheck_member_link(account_id, member)
            coach = self._recheck_coach_link(account_id, coach)
        return member, coach

    def _recheck_member_link(
        self, account_id: int, member: Member | None,
    ) -> Member | None:
        """锁定读复核会员关联行；关联缺失返回 None，改指新档案时锁定新档案。"""
        if member is None:
            return None
        member_id = self._session.execute(
            text(self._locked_sql(
                "SELECT member_id FROM member_account_links WHERE account_id = :id"
            )),
            {"id": account_id},
        ).scalar_one_or_none()
        if member_id == member.id:
            return member
        return None if member_id is None else self.lock_member(member_id)

    def _recheck_coach_link(
        self, account_id: int, coach: Coach | None,
    ) -> Coach | None:
        """锁定读复核教练关联行；关联缺失返回 None，改指新档案时锁定新档案。"""
        if coach is None:
            return None
        coach_id = self._session.execute(
            text(self._locked_sql(
                "SELECT coach_id FROM coach_account_links WHERE account_id = :id"
            )),
            {"id": account_id},
        ).scalar_one_or_none()
        if coach_id == coach.id:
            return coach
        return None if coach_id is None else self.lock_coach(coach_id)

    def lock_member(self, member_id: int) -> Member | None:
        """锁定并读取会员档案；不存在返回 None。"""
        row = self._session.execute(
            text(self._locked_sql("SELECT * FROM members WHERE id = :id")),
            {"id": member_id},
        ).mappings().first()
        return None if row is None else _member(row)

    def lock_coach(self, coach_id: int) -> Coach | None:
        """锁定并读取教练档案；不存在返回 None。"""
        row = self._session.execute(
            text(self._locked_sql("SELECT * FROM coaches WHERE id = :id")),
            {"id": coach_id},
        ).mappings().first()
        return None if row is None else _coach(row)

    def lock_members(self, member_ids: tuple[int, ...]) -> tuple[Member, ...]:
        """按会员编号升序锁定多条会员档案。"""
        identifiers = tuple(sorted(set(member_ids)))
        if not identifiers:
            return ()
        placeholders = ", ".join(f":id{index}" for index in range(len(identifiers)))
        parameters = {f"id{index}": value for index, value in enumerate(identifiers)}
        rows = self._session.execute(
            text(self._locked_sql(
                f"SELECT * FROM members WHERE id IN ({placeholders}) ORDER BY id"
            )),
            parameters,
        ).mappings().all()
        return tuple(_member(row) for row in rows)

    def lock_coaches(self, coach_ids: tuple[int, ...]) -> tuple[Coach, ...]:
        """按教练编号升序锁定多条教练档案。"""
        identifiers = tuple(sorted(set(coach_ids)))
        if not identifiers:
            return ()
        placeholders = ", ".join(f":id{index}" for index in range(len(identifiers)))
        parameters = {f"id{index}": value for index, value in enumerate(identifiers)}
        rows = self._session.execute(
            text(self._locked_sql(
                f"SELECT * FROM coaches WHERE id IN ({placeholders}) ORDER BY id"
            )),
            parameters,
        ).mappings().all()
        return tuple(_coach(row) for row in rows)

    def get_member_account_id(self, account_id: int) -> int | None:
        """读取会员账号当前关联的会员编号；未关联返回 None。"""
        return self._session.execute(
            text("SELECT member_id FROM member_account_links WHERE account_id = :id"),
            {"id": account_id},
        ).scalar_one_or_none()

    def get_coach_account_id(self, account_id: int) -> int | None:
        """读取教练账号当前关联的教练编号；未关联返回 None。"""
        return self._session.execute(
            text("SELECT coach_id FROM coach_account_links WHERE account_id = :id"),
            {"id": account_id},
        ).scalar_one_or_none()

    def get_member_link_owner(self, member_id: int) -> int | None:
        """读取会员档案当前关联的账号编号；未关联返回 None。

        使用普通一致性读，不加间隙锁；双向唯一约束负责防重，冲突由服务转换。
        """
        return self._session.execute(
            text("SELECT account_id FROM member_account_links WHERE member_id = :id"),
            {"id": member_id},
        ).scalar_one_or_none()

    def get_coach_link_owner(self, coach_id: int) -> int | None:
        """读取教练档案当前关联的账号编号；未关联返回 None。

        使用普通一致性读，不加间隙锁；双向唯一约束负责防重，冲突由服务转换。
        """
        return self._session.execute(
            text("SELECT account_id FROM coach_account_links WHERE coach_id = :id"),
            {"id": coach_id},
        ).scalar_one_or_none()

    def create(self, *, username: str, password_hash: str, role: Role) -> Account:
        """保存已哈希密码和角色；不自行提交。"""
        result = self._session.execute(text(
            "INSERT INTO accounts (username, password_hash, role, is_active) "
            "VALUES (:username, :password_hash, :role, :is_active)"
        ), {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "is_active": True,
        })
        account_id = result.lastrowid
        if account_id is None:
            row = self._session.execute(
                text("SELECT * FROM accounts WHERE username = :username"),
                {"username": username},
            ).mappings().first()
        else:
            row = self._session.execute(
                text("SELECT * FROM accounts WHERE id = :id"),
                {"id": account_id},
            ).mappings().first()
        if row is None:
            raise StorageError("保存账号失败")
        return _account(row)

    def list(self, query: NamedQuery) -> Page[AccountView]:
        """按 id 升序稳定分页查询可展示账号资料，不返回密码哈希。"""
        conditions: list[str] = []
        parameters: dict[str, object] = {}
        if query.keyword:
            if self._session.get_bind().dialect.name == "sqlite":
                conditions.append("instr(a.username, :keyword) > 0")
            else:
                conditions.append("LOCATE(:keyword, a.username) > 0")
            parameters["keyword"] = query.keyword
        if query.is_active is not None:
            conditions.append("a.is_active = :is_active")
            parameters["is_active"] = query.is_active
        where = "" if not conditions else " WHERE " + " AND ".join(conditions)

        total = int(self._session.execute(
            text(f"SELECT COUNT(*) FROM accounts a{where}"), parameters,
        ).scalar_one())
        offset = (query.paging.page - 1) * query.paging.page_size
        parameters.update({"limit": query.paging.page_size, "offset": offset})
        rows = self._session.execute(text(
            "SELECT a.id, a.username, a.role, a.is_active, ml.member_id, cl.coach_id "
            "FROM accounts a "
            "LEFT JOIN member_account_links ml ON ml.account_id = a.id "
            "LEFT JOIN coach_account_links cl ON cl.account_id = a.id"
            f"{where} ORDER BY a.id LIMIT :limit OFFSET :offset"
        ), parameters).mappings().all()
        items = [
            AccountView(
                id=row["id"],
                username=row["username"],
                role=row["role"],
                is_active=bool(row["is_active"]),
                member_id=row["member_id"],
                coach_id=row["coach_id"],
            )
            for row in rows
        ]
        return Page(
            items=items,
            total=total,
            page=query.paging.page,
            page_size=query.paging.page_size,
        )

    def set_active(self, account_id: int, active: bool) -> AccountView:
        """写启用状态并返回账号详情；不提交。"""
        self._session.execute(
            text("UPDATE accounts SET is_active = :active WHERE id = :id"),
            {"active": active, "id": account_id},
        )
        view = self.get_view(account_id)
        if view is None:
            raise StorageError("读取账号失败")
        return view

    def create_member_link(
        self, *, account_id: int, member_id: int, linked_by: int, linked_at: datetime,
    ) -> None:
        """创建会员账号关联；唯一约束冲突由服务转换为 ConflictError。"""
        self._session.execute(text(
            "INSERT INTO member_account_links (account_id, member_id, linked_at, linked_by) "
            "VALUES (:account_id, :member_id, :linked_at, :linked_by)"
        ), {
            "account_id": account_id,
            "member_id": member_id,
            "linked_at": linked_at,
            "linked_by": linked_by,
        })

    def delete_member_link(self, account_id: int) -> bool:
        """删除账号的会员关联；返回是否确实删除了一行。"""
        result = self._session.execute(
            text("DELETE FROM member_account_links WHERE account_id = :id"),
            {"id": account_id},
        )
        return bool(result.rowcount)

    def create_coach_link(
        self, *, account_id: int, coach_id: int, linked_by: int, linked_at: datetime,
    ) -> None:
        """创建教练账号关联；唯一约束冲突由服务转换为 ConflictError。"""
        self._session.execute(text(
            "INSERT INTO coach_account_links (account_id, coach_id, linked_at, linked_by) "
            "VALUES (:account_id, :coach_id, :linked_at, :linked_by)"
        ), {
            "account_id": account_id,
            "coach_id": coach_id,
            "linked_at": linked_at,
            "linked_by": linked_by,
        })

    def delete_coach_link(self, account_id: int) -> bool:
        """删除账号的教练关联；返回是否确实删除了一行。"""
        result = self._session.execute(
            text("DELETE FROM coach_account_links WHERE account_id = :id"),
            {"id": account_id},
        )
        return bool(result.rowcount)
