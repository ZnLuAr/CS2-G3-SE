"""体测数据访问：授权范围在查询中应用。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Numeric, bindparam, text

from src.models.contracts import MeasurementInput, MeasurementQuery, MeasurementView, Page

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_COLUMNS = """
    m.id, m.member_id, m.coach_id, m.measured_at, m.created_at,
    m.height_cm, m.weight_kg, m.body_fat_pct
"""


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _stored(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _select(sql: str):
    return _statement(sql).columns(
        measured_at=DateTime(), created_at=DateTime(),
        height_cm=Numeric(6, 2), weight_kg=Numeric(6, 2), body_fat_pct=Numeric(5, 2),
    )


def _statement(sql: str):
    statement = text(sql)
    temporal = [name for name in ("as_of", "start_at", "end_at") if f":{name}" in sql]
    return statement.bindparams(*(bindparam(name, type_=DateTime()) for name in temporal))


def _view(row) -> MeasurementView:
    return MeasurementView(
        id=int(row["id"]), member_id=int(row["member_id"]), coach_id=int(row["coach_id"]),
        measured_at=_utc(row["measured_at"]), created_at=_utc(row["created_at"]),
        height_cm=row["height_cm"], weight_kg=row["weight_kg"], body_fat_pct=row["body_fat_pct"],
    )


class MeasurementRepository:
    """使用传入会话读写体测；查询未命中返回 None，事务由 Logic 管理。"""

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    @staticmethod
    def _scope(scope_member_id: int | None, scope_coach_id: int | None) -> tuple[str, dict]:
        if (scope_member_id is None) == (scope_coach_id is None):
            raise ValueError("必须指定且只能指定一种体测授权范围")
        if scope_member_id is not None:
            return "m.member_id = :scope_member_id", {"scope_member_id": scope_member_id}
        # 有一条预约的截止覆盖记录，等价于记录早于所有预约截止的最大值。
        return """
            m.created_at <= :as_of AND EXISTS (
                SELECT 1 FROM bookings b
                JOIN course_sessions cs ON cs.id = b.session_id
                WHERE b.member_id = m.member_id AND cs.coach_id = :scope_coach_id
                  AND b.booked_at <= :as_of AND m.created_at <= cs.ends_at
                  AND (b.closed_at IS NULL OR m.created_at <= b.closed_at)
            )
        """, {"scope_coach_id": scope_coach_id}

    def get(
        self, measurement_id: int, *, scope_member_id: int | None,
        scope_coach_id: int | None, as_of: datetime,
    ) -> MeasurementView | None:
        """读取范围内的体测详情；不存在或不可见返回 None。

        范围与 as_of 由服务根据可信身份生成，两种 scope 必须恰有一项非空。
        会员范围按归属；教练范围按历史预约计算截止并限制 created_at，见架构“体测权限规则”。

        返回：MeasurementView | None。"""
        scope, params = self._scope(scope_member_id, scope_coach_id)
        params.update(measurement_id=measurement_id, as_of=_stored(as_of))
        row = self._session.execute(
            _select(f"SELECT {_COLUMNS} FROM body_measurements m "
                    f"WHERE m.id = :measurement_id AND {scope}"), params,
        ).mappings().first()
        return None if row is None else _view(row)

    def list(
        self, query: MeasurementQuery, *, scope_member_id: int | None,
        scope_coach_id: int | None, as_of: datetime,
    ) -> Page[MeasurementView]:
        """按测量时间和编号降序分页查询，只计算授权范围内的 total 和 items。

        身份范围与可见截止同 get；query.member_id 只能缩小范围，不能覆盖服务给定的 scope。

        返回：Page[MeasurementView]。"""
        scope, params = self._scope(scope_member_id, scope_coach_id)
        filters = [scope, "m.member_id = :member_id"]
        params.update(member_id=query.member_id, as_of=_stored(as_of))
        if query.window is not None:
            filters.extend(["m.measured_at >= :start_at", "m.measured_at < :end_at"])
            params.update(start_at=_stored(query.window.start), end_at=_stored(query.window.end))
        where = " AND ".join(filters)
        total = self._session.execute(
            _statement(f"SELECT COUNT(*) FROM body_measurements m WHERE {where}"), params,
        ).scalar_one()
        paging = query.paging
        rows = self._session.execute(
            _select(f"SELECT {_COLUMNS} FROM body_measurements m WHERE {where} "
                    "ORDER BY m.measured_at DESC, m.id DESC LIMIT :limit OFFSET :offset"),
            {**params, "limit": paging.page_size, "offset": (paging.page - 1) * paging.page_size},
        ).mappings().all()
        return Page(
            items=[_view(row) for row in rows], total=int(total),
            page=paging.page, page_size=paging.page_size,
        )

    def create(
        self, data: MeasurementInput, coach_id: int, *, created_at: datetime,
    ) -> MeasurementView:
        """保存体测；教练编号来自可信操作者，created_at 由服务获得会员锁后生成。

        created_at 是实际录入时间，不接受界面传值；不可用 measured_at 代替。

        返回：MeasurementView。"""
        statement = text("""
            INSERT INTO body_measurements (
                member_id, coach_id, measured_at, height_cm, weight_kg, body_fat_pct, created_at
            ) VALUES (
                :member_id, :coach_id, :measured_at, :height_cm, :weight_kg, :body_fat_pct, :created_at
            )
        """).bindparams(
            bindparam("measured_at", type_=DateTime()), bindparam("created_at", type_=DateTime()),
            bindparam("height_cm", type_=Numeric(6, 2)), bindparam("weight_kg", type_=Numeric(6, 2)),
            bindparam("body_fat_pct", type_=Numeric(5, 2)),
        )
        result = self._session.execute(statement, {
            "member_id": data.member_id, "coach_id": coach_id,
            "measured_at": _stored(data.measured_at), "created_at": _stored(created_at),
            "height_cm": data.height_cm, "weight_kg": data.weight_kg,
            "body_fat_pct": data.body_fat_pct,
        })
        return MeasurementView(
            id=int(result.lastrowid), member_id=data.member_id, coach_id=coach_id,
            measured_at=_utc(data.measured_at), created_at=_utc(created_at),
            height_cm=data.height_cm, weight_kg=data.weight_kg, body_fat_pct=data.body_fat_pct,
        )
