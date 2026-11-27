"""会员数据访问；体测所用的会员锁定、建档写入与详情读取已实现。

仓储只使用调用方传入的会话：不提交、不输出提示、不转业务异常。
未命中查询返回 None，由服务层转换成 NotFoundError。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import MemberInput, MemberQuery, MemberStatus
from src.models.member import Member

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


_MEMBER_COLUMNS = "id, name, phone, status, archived_at, created_at, updated_at"


class MemberRepository:
    """会员表读写；参数绑定、分页、锁定与持久化。

    返回领域模型 Member（非 View）；查询未命中返回 None，由服务转换异常。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def create(self, data: MemberInput) -> Member:
        """新增会员档案并返回领域模型；不自行提交。

        写入 status=active、archived_at=NULL；created_at 与 updated_at 由仓储按 UTC 生成，
        避免依赖数据库会话时区。插入后按主键回读，返回数据库实际保存的值。
        """
        from datetime import datetime, timezone

        from sqlalchemy import text

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = self._session.execute(
            text(
                "INSERT INTO members (name, phone, status, archived_at, created_at, updated_at) "
                "VALUES (:name, :phone, :status, NULL, :created_at, :updated_at)"
            ),
            {
                "name": data.name,
                "phone": data.phone,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
        )
        member_id = result.lastrowid
        created = self.get(member_id)
        if created is None:
            from src.errors.storage import StorageError

            raise StorageError("保存会员档案失败")
        return created

    def get(self, member_id: int) -> Member | None:
        """查询会员；未找到返回 None，由服务转成异常。

        数据库以无时区 DATETIME(6) 存 UTC，读取时补回 UTC 时区。
        """
        from datetime import timezone

        from sqlalchemy import text

        row = self._session.execute(
            text(f"SELECT {_MEMBER_COLUMNS} FROM members WHERE id = :member_id"),
            {"member_id": member_id},
        ).mappings().first()
        if row is None:
            return None
        return _to_member(dict(row), timezone)

    def lock(self, member_id: int) -> Member | None:
        """锁定并读取最新会员记录；用于服务事务。"""
        from datetime import timezone

        from sqlalchemy import DateTime, Integer, String, column, select, table

        members = table(
            "members", column("id", Integer), column("name", String), column("phone", String),
            column("status", String), column("archived_at", DateTime),
            column("created_at", DateTime), column("updated_at", DateTime),
        )
        row = self._session.execute(
            select(members).where(members.c.id == member_id).with_for_update(),
        ).mappings().first()
        if row is None:
            return None
        return _to_member(dict(row), timezone)

    def list(self, query: MemberQuery) -> tuple[list[Member], int]:
        """按 id 升序稳定分页，返回（当页记录, 总数）；权限范围由服务在 query 中约束。

        关键字按姓名包含匹配，输入里的 LIKE 通配符按字面量处理。
        COUNT 与当页查询使用同一组筛选条件，避免总数与分页口径不一致。
        """
        from datetime import timezone

        from sqlalchemy import text

        where, params = _member_filters(query)
        total = self._session.execute(
            text(f"SELECT COUNT(*) FROM members WHERE {where}"),
            params,
        ).scalar_one()
        offset = (query.paging.page - 1) * query.paging.page_size
        rows = self._session.execute(
            text(
                f"SELECT {_MEMBER_COLUMNS} FROM members WHERE {where} "
                "ORDER BY id ASC LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": query.paging.page_size, "offset": offset},
        ).mappings().all()
        return [_to_member(dict(row), timezone) for row in rows], int(total)

    def update_profile(self, member_id: int, name: str, phone: str | None) -> Member:
        """更新会员姓名与电话；phone=None 表示清空。

        调用方须已在同一事务内持有该会员的行锁；本方法不回锁、不提交，
        写入后按主键回读，返回数据库实际保存的最新值。
        """
        from datetime import datetime, timezone

        from sqlalchemy import text

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self._session.execute(
            text(
                "UPDATE members SET name = :name, phone = :phone, updated_at = :updated_at "
                "WHERE id = :member_id"
            ),
            {"name": name, "phone": phone, "updated_at": now, "member_id": member_id},
        )
        updated = self.get(member_id)
        if updated is None:
            from src.errors.storage import StorageError

            raise StorageError("更新会员档案失败")
        return updated

    def set_status(self, member_id: int, status: MemberStatus, archived_at: datetime | None) -> Member:
        """写会员状态与归档时刻；业务条件由服务检查。"""
        raise NotImplementedError("MemberRepository.set_status 尚未实现")


def _escape_like(value: str) -> str:
    """把 LIKE 通配符转成字面量，避免用户输入 % 或 _ 扩大匹配范围。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _member_filters(query: MemberQuery) -> tuple[str, dict]:
    """按 MemberQuery 生成 WHERE 片段与绑定参数；无条件时返回恒真假条件。"""
    clauses: list[str] = []
    params: dict = {}

    if query.member_id is not None:
        clauses.append("id = :member_id")
        params["member_id"] = query.member_id

    keyword = (query.keyword or "").strip()
    if keyword:
        clauses.append("name LIKE :keyword ESCAPE '\\\\'")
        params["keyword"] = f"%{_escape_like(keyword)}%"

    if query.status is not None:
        clauses.append("status = :status")
        params["status"] = query.status

    return (" AND ".join(clauses) if clauses else "1 = 1"), params


def _to_member(values: dict, timezone) -> Member:
    """把数据库行转换为 Member；无时区时间按 UTC 补回时区。"""
    for key in ("archived_at", "created_at", "updated_at"):
        value = values[key]
        if value is not None:
            values[key] = (
                value.replace(tzinfo=timezone.utc)
                if value.tzinfo is None
                else value.astimezone(timezone.utc)
            )
    return Member(**values)
