"""体测数据访问层（MySQL 8 / SQLAlchemy 2.x）。只使用传入 Session，不提交事务。"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.models.contracts import MeasurementInput, MeasurementQuery, MeasurementView, Page

_SELECT = """SELECT id, member_id, coach_id, measured_at, height_cm, weight_kg, body_fat_pct
FROM body_measurements"""


def _view(row) -> MeasurementView:
    return MeasurementView(id=int(row["id"]), member_id=int(row["member_id"]),
        coach_id=int(row["coach_id"]), measured_at=row["measured_at"],
        height_cm=Decimal(str(row["height_cm"])), weight_kg=Decimal(str(row["weight_kg"])),
        body_fat_pct=None if row["body_fat_pct"] is None else Decimal(str(row["body_fat_pct"])))

class MeasurementRepository:
    """Repository 不做权限决策、不 commit；scope 和 as_of 必须由 service 提供。"""
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _scope_sql(scope_member_id: int | None, scope_coach_id: int | None) -> tuple[str, dict]:
        if (scope_member_id is None) == (scope_coach_id is None):
            raise ValueError("必须且只能指定一种体测数据范围")
        if scope_member_id is not None:
            return "m.member_id = :scope_member_id", {"scope_member_id": scope_member_id}
        return "m.member_id IN (SELECT b.member_id FROM bookings b JOIN course_sessions cs ON cs.id=b.session_id WHERE cs.coach_id=:scope_coach_id GROUP BY b.member_id) AND m.created_at <= (SELECT MAX(CASE WHEN b.status='cancelled' THEN LEAST(COALESCE(b.closed_at, cs.ends_at), cs.ends_at) ELSE cs.ends_at END) FROM bookings b JOIN course_sessions cs ON cs.id=b.session_id WHERE b.member_id=m.member_id AND cs.coach_id=:scope_coach_id AND b.booked_at <= :as_of)", {"scope_coach_id": scope_coach_id}

    def get(self, measurement_id: int, *, scope_member_id: int | None, scope_coach_id: int | None, as_of: datetime) -> MeasurementView | None:
        scope, params = self._scope_sql(scope_member_id, scope_coach_id)
        params.update(id=measurement_id, as_of=as_of)
        row = self.session.execute(text(f"SELECT m.id,m.member_id,m.coach_id,m.measured_at,m.height_cm,m.weight_kg,m.body_fat_pct FROM body_measurements m WHERE m.id=:id AND {scope}"), params).mappings().first()
        return _view(row) if row else None

    def list(self, query: MeasurementQuery, *, scope_member_id: int | None, scope_coach_id: int | None, as_of: datetime) -> Page[MeasurementView]:
        scope, params = self._scope_sql(scope_member_id, scope_coach_id)
        params.update(member_filter=query.member_id, as_of=as_of)
        filters = [scope, "m.member_id=:member_filter"]
        if query.window:
            if query.window.start >= query.window.end:
                raise ValueError("体测查询开始时间必须早于结束时间")
            filters += ["m.measured_at >= :start_at", "m.measured_at < :end_at"]
            params.update(start_at=query.window.start, end_at=query.window.end)
        where = " AND ".join(filters)
        paging = query.paging
        offset = (paging.page - 1) * paging.page_size
        total = int(self.session.execute(text(f"SELECT COUNT(*) FROM body_measurements m WHERE {where}"), params).scalar_one())
        rows = self.session.execute(text(f"SELECT m.id,m.member_id,m.coach_id,m.measured_at,m.height_cm,m.weight_kg,m.body_fat_pct FROM body_measurements m WHERE {where} ORDER BY m.measured_at DESC,m.id DESC LIMIT :limit OFFSET :offset"), {**params,"limit":paging.page_size,"offset":offset}).mappings().all()
        return Page(items=[_view(r) for r in rows], total=total, page=paging.page, page_size=paging.page_size)

    def create(self, data: MeasurementInput, coach_id: int, *, created_at: datetime) -> MeasurementView:
        result = self.session.execute(text("""INSERT INTO body_measurements (member_id,coach_id,measured_at,height_cm,weight_kg,body_fat_pct,created_at) VALUES (:member_id,:coach_id,:measured_at,:height_cm,:weight_kg,:body_fat_pct,:created_at)"""),
            {"member_id":data.member_id,"coach_id":coach_id,"measured_at":data.measured_at,"height_cm":data.height_cm,"weight_kg":data.weight_kg,"body_fat_pct":data.body_fat_pct,"created_at":created_at})
        row = self.session.execute(text(f"{_SELECT} WHERE id=:id"), {"id":result.lastrowid}).mappings().one()
        return _view(row)
