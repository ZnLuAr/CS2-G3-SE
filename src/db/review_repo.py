"""评价数据访问，使用调用方的会话和事务。"""

from __future__ import annotations

from datetime import timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, column, select, table, text
from sqlalchemy.exc import IntegrityError

from src.errors import ConflictError, StorageError
from src.models.contracts import Page, ReviewInput, ReviewQuery, ReviewView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_REVIEWS = table("reviews", column("id"), column("booking_id"))
_COLUMNS = "r.id, r.booking_id, b.member_id, b.session_id, cs.coach_id, r.rating, r.comment, r.created_at"
_FROM = """
    FROM reviews r
    JOIN bookings b ON b.id = r.booking_id
    JOIN course_sessions cs ON cs.id = b.session_id
"""


def _view(row) -> ReviewView:
    created_at = row["created_at"]
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return ReviewView(**{**row, "created_at": created_at.astimezone(timezone.utc)})


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self, review_id: int, *, scope_member_id: int | None, scope_coach_id: int | None,
    ) -> ReviewView | None:
        """读取授权范围内的详情，未命中返回 None。"""
        filters, params = self._scope(scope_member_id, scope_coach_id)
        filters.append("r.id = :review_id")
        params["review_id"] = review_id
        where = " AND ".join(filters)
        row = self._session.execute(
            text(f"SELECT {_COLUMNS} {_FROM} WHERE {where}").columns(created_at=DateTime()),
            params,
        ).mappings().one_or_none()
        return None if row is None else _view(row)

    def has_for_booking(self, booking_id: int) -> bool:
        """预约已加锁后，以锁定当前读检查是否已有评价。"""
        statement = (
            select(_REVIEWS.c.id).where(_REVIEWS.c.booking_id == booking_id).with_for_update()
        )
        return self._session.execute(statement).scalar_one_or_none() is not None

    def list(
        self, query: ReviewQuery, *, scope_member_id: int | None, scope_coach_id: int | None,
    ) -> Page[ReviewView]:
        """对授权范围和查询条件的交集计数并稳定分页。"""
        filters, params = self._scope(scope_member_id, scope_coach_id)
        if query.member_id is not None:
            filters.append("b.member_id = :member_id")
            params["member_id"] = query.member_id
        if query.coach_id is not None:
            filters.append("cs.coach_id = :coach_id")
            params["coach_id"] = query.coach_id
        where = " WHERE " + " AND ".join(filters) if filters else ""
        total = self._session.execute(
            text(f"SELECT COUNT(*) {_FROM}{where}"), params,
        ).scalar_one()
        paging = query.paging
        rows = self._session.execute(
            text(
                f"SELECT {_COLUMNS} {_FROM}{where} "
                "ORDER BY r.created_at DESC, r.id DESC LIMIT :limit OFFSET :offset"
            ).columns(created_at=DateTime()),
            {**params, "limit": paging.page_size, "offset": (paging.page - 1) * paging.page_size},
        ).mappings()
        return Page(
            items=[_view(row) for row in rows], total=total,
            page=paging.page, page_size=paging.page_size,
        )

    def create(self, data: ReviewInput) -> ReviewView:
        """插入一条评价并返回详情。唯一键冲突时保留原评价。"""
        try:
            result = self._session.execute(
                text("""
                    INSERT INTO reviews (booking_id, rating, comment)
                    VALUES (:booking_id, :rating, :comment)
                """),
                {"booking_id": data.booking_id, "rating": data.rating, "comment": data.comment},
            )
        except IntegrityError as exc:
            # 本语句的主键由数据库生成，唯一键冲突来自 booking_id。
            if exc.orig.args and exc.orig.args[0] == 1062:
                raise ConflictError("这条预约已有评价") from exc
            raise
        view = self.get(result.lastrowid, scope_member_id=None, scope_coach_id=None)
        if view is None:
            raise StorageError("无法读取已写入的评价")
        return view

    @staticmethod
    def _scope(
        member_id: int | None, coach_id: int | None,
    ) -> tuple[list[str], dict[str, int]]:
        if member_id is not None:
            return ["b.member_id = :scope_member_id"], {"scope_member_id": member_id}
        if coach_id is not None:
            return ["cs.coach_id = :scope_coach_id"], {"scope_coach_id": coach_id}
        return [], {}
