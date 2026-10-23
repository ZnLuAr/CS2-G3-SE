"""预约数据访问；事务由调用方 Logic 管理。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, insert, select, update

from src.db.course_repo import load_session_views
from src.db.support import from_db_utc, to_db_utc, utc_now, validate_paging, window_bounds
from src.db.tables import bookings, course_sessions, members
from src.errors.storage import StorageError
from src.models.booking import Booking
from src.models.contracts import (
    BookingInput, BookingQuery, BookingStatus, BookingView, DateWindow, Page,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_ACTIVE = ("reserved", "checked_in")


def _model(row) -> Booking:
    return Booking(
        id=int(row["id"]), member_id=int(row["member_id"]),
        session_id=int(row["session_id"]), lesson_package_id=int(row["lesson_package_id"]),
        status=row["status"], booked_at=from_db_utc(row["booked_at"]),
        checked_in_at=from_db_utc(row["checked_in_at"]),
        closed_at=from_db_utc(row["closed_at"]),
        created_at=from_db_utc(row["created_at"]), updated_at=from_db_utc(row["updated_at"]),
    )


def _view(row, session_view) -> BookingView:
    return BookingView(
        id=int(row["id"]), member_id=int(row["member_id"]), member_name=row["member_name"],
        lesson_package_id=int(row["lesson_package_id"]), session=session_view,
        status=row["status"], booked_at=from_db_utc(row["booked_at"]),
        checked_in_at=from_db_utc(row["checked_in_at"]),
        closed_at=from_db_utc(row["closed_at"]),
    )


class BookingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, booking_id: int) -> BookingView | None:
        row = self._session.execute(
            select(bookings, members.c.name.label("member_name"))
            .join(members, members.c.id == bookings.c.member_id)
            .where(bookings.c.id == booking_id)
        ).mappings().first()
        if row is None:
            return None
        session_view = load_session_views(self._session, [int(row["session_id"])]).get(int(row["session_id"]))
        if session_view is None:
            raise StorageError("预约关联的课次不存在")
        return _view(row, session_view)

    def list(self, query: BookingQuery, *, scope_member_id: int | None, scope_coach_id: int | None) -> Page[BookingView]:
        page, size = validate_paging(query.paging)
        if scope_member_id is not None and scope_coach_id is not None:
            raise ValueError("会员与教练范围不能同时指定")
        conditions = []
        if query.member_id is not None:
            conditions.append(bookings.c.member_id == query.member_id)
        if query.session_id is not None:
            conditions.append(bookings.c.session_id == query.session_id)
        if query.lesson_package_id is not None:
            conditions.append(bookings.c.lesson_package_id == query.lesson_package_id)
        if query.status is not None:
            conditions.append(bookings.c.status == query.status)
        if query.window is not None:
            start, end = window_bounds(query.window)
            conditions.extend((course_sessions.c.starts_at >= start, course_sessions.c.starts_at < end))
        if scope_member_id is not None:
            conditions.append(bookings.c.member_id == scope_member_id)
        if scope_coach_id is not None:
            conditions.append(course_sessions.c.coach_id == scope_coach_id)
        total = int(self._session.scalar(
            select(func.count()).select_from(bookings)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(*conditions)
        ) or 0)
        rows = self._session.execute(
            select(bookings, members.c.name.label("member_name"))
            .join(members, members.c.id == bookings.c.member_id)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(*conditions)
            .order_by(course_sessions.c.starts_at.desc(), bookings.c.id.desc())
            .limit(size).offset((page - 1) * size)
        ).mappings().all()
        session_views = load_session_views(self._session, [int(row["session_id"]) for row in rows])
        items = []
        for row in rows:
            session_view = session_views.get(int(row["session_id"]))
            if session_view is None:
                raise StorageError("预约关联的课次不存在")
            items.append(_view(row, session_view))
        return Page(items=items, total=total, page=page, page_size=size)

    def find_for_member_session(self, member_id: int, session_id: int) -> Booking | None:
        row = self._session.execute(
            select(bookings).where(
                bookings.c.member_id == member_id,
                bookings.c.session_id == session_id,
            ).order_by(bookings.c.id.desc()).with_for_update()
        ).mappings().first()
        return None if row is None else _model(row)

    def has_open_for_member(self, member_id: int) -> bool:
        row = self._session.execute(
            select(bookings.c.id).where(
                bookings.c.member_id == member_id,
                bookings.c.status.in_(_ACTIVE),
            ).with_for_update().limit(1)
        ).first()
        return row is not None

    def list_open_for_session(self, session_id: int) -> tuple[Booking, ...]:
        rows = self._session.execute(
            select(bookings).where(
                bookings.c.session_id == session_id,
                bookings.c.status.in_(_ACTIVE),
            ).order_by(bookings.c.member_id, bookings.c.lesson_package_id, bookings.c.id)
        ).mappings().all()
        return tuple(_model(row) for row in rows)

    def has_open_for_session(self, session_id: int) -> bool:
        row = self._session.execute(
            select(bookings.c.id).where(
                bookings.c.session_id == session_id,
                bookings.c.status.in_(_ACTIVE),
            ).with_for_update().limit(1)
        ).first()
        return row is not None

    def create(self, data: BookingInput, booked_at: datetime) -> BookingView:
        now = utc_now()
        result = self._session.execute(insert(bookings).values(
            member_id=data.member_id, session_id=data.session_id,
            lesson_package_id=data.lesson_package_id, status="reserved",
            booked_at=to_db_utc(booked_at), checked_in_at=None, closed_at=None,
            created_at=now, updated_at=now,
        ))
        view = self.get(int(result.inserted_primary_key[0]))
        if view is None:
            raise StorageError("保存预约失败")
        return view

    def set_state(
        self, booking_id: int, *, status: BookingStatus,
        checked_in_at: datetime | None, closed_at: datetime | None,
    ) -> BookingView:
        self._session.execute(update(bookings).where(bookings.c.id == booking_id).values(
            status=status,
            checked_in_at=None if checked_in_at is None else to_db_utc(checked_in_at),
            closed_at=None if closed_at is None else to_db_utc(closed_at),
            updated_at=utc_now(),
        ))
        view = self.get(booking_id)
        if view is None:
            raise StorageError("读取预约失败")
        return view

    def count_occupied(self, session_id: int) -> int:
        rows = self._session.execute(
            select(bookings.c.id).where(
                bookings.c.session_id == session_id,
                bookings.c.status.in_(_ACTIVE),
            ).with_for_update()
        ).all()
        return len(rows)

    def has_member_conflict(self, member_id: int, window: DateWindow) -> bool:
        start, end = window_bounds(window)
        row = self._session.execute(
            select(bookings.c.id)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(
                bookings.c.member_id == member_id,
                bookings.c.status.in_(_ACTIVE),
                course_sessions.c.status != "cancelled",
                course_sessions.c.starts_at < end,
                course_sessions.c.ends_at > start,
            ).with_for_update().limit(1)
        ).first()
        return row is not None

    def has_current_coaching_booking(self, member_id: int, coach_id: int, *, at: datetime) -> bool:
        at_db = to_db_utc(at)
        row = self._session.execute(
            select(bookings.c.id)
            .join(course_sessions, course_sessions.c.id == bookings.c.session_id)
            .where(
                bookings.c.member_id == member_id,
                course_sessions.c.coach_id == coach_id,
                bookings.c.status.in_(_ACTIVE),
                course_sessions.c.status == "scheduled",
                bookings.c.booked_at <= at_db,
                course_sessions.c.ends_at > at_db,
                bookings.c.closed_at.is_(None),
            ).with_for_update().limit(1)
        ).first()
        return row is not None

    def lock(self, booking_id: int) -> Booking | None:
        row = self._session.execute(
            select(bookings).where(bookings.c.id == booking_id).with_for_update()
        ).mappings().first()
        return None if row is None else _model(row)
