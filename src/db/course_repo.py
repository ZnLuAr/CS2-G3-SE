"""教练、课程模板、场地和课次的数据访问；事务由调用方 Logic 管理。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, insert, or_, select, update

from src.db.support import from_db_utc, to_db_utc, utc_now, validate_paging, window_bounds
from src.db.tables import (
    coach_account_links, coaches, course_sessions, courses, rooms,
)
from src.errors.business import NotFoundError
from src.errors.storage import StorageError
from src.models.contracts import (
    CoachInput, CoachView, CourseInput, CourseKind, CourseView, DateWindow, NamedQuery,
    Page, RoomInput, RoomView, SessionInput, SessionQuery, SessionStatus, SessionView,
)
from src.models.course import Coach, Course, CourseSession, Room

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_OCCUPYING = ("reserved", "checked_in")


def _like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _occupied_subquery():
    from src.db.tables import bookings
    return (
        select(bookings.c.session_id.label("session_id"), func.count().label("occupied"))
        .where(bookings.c.status.in_(_OCCUPYING))
        .group_by(bookings.c.session_id)
        .subquery()
    )


_OCCUPIED = _occupied_subquery()
_SESSION_SELECT = (
    select(
        course_sessions, courses.c.name.label("course_title"),
        courses.c.description.label("course_description"),
        courses.c.duration_minutes.label("course_duration"),
        courses.c.is_active.label("course_active"),
        courses.c.created_at.label("course_created_at"),
        courses.c.updated_at.label("course_updated_at"),
        coaches.c.name.label("coach_name"), coaches.c.phone.label("coach_phone"),
        coaches.c.is_active.label("coach_active"),
        coaches.c.created_at.label("coach_created_at"),
        coaches.c.updated_at.label("coach_updated_at"),
        rooms.c.name.label("room_name"), rooms.c.location.label("room_location"),
        rooms.c.is_active.label("room_active"),
        rooms.c.created_at.label("room_created_at"),
        rooms.c.updated_at.label("room_updated_at"),
        func.coalesce(_OCCUPIED.c.occupied, 0).label("occupied_count"),
    )
    .join(courses, courses.c.id == course_sessions.c.course_id)
    .join(coaches, coaches.c.id == course_sessions.c.coach_id)
    .join(rooms, rooms.c.id == course_sessions.c.room_id)
    .outerjoin(_OCCUPIED, _OCCUPIED.c.session_id == course_sessions.c.id)
)


def _coach_view(row) -> CoachView:
    return CoachView(
        id=int(row["id"]), name=row["name"], phone=row["phone"],
        is_active=bool(row["is_active"]),
        created_at=from_db_utc(row["created_at"]), updated_at=from_db_utc(row["updated_at"]),
    )


def _coach_model(row) -> Coach:
    view = _coach_view(row)
    return Coach(
        id=view.id, name=view.name, phone=view.phone, is_active=view.is_active,
        created_at=view.created_at, updated_at=view.updated_at,
    )


def _course_view(row) -> CourseView:
    return CourseView(
        id=int(row["id"]), name=row["name"], description=row["description"],
        kind=row["kind"], duration_minutes=int(row["duration_minutes"]),
        is_active=bool(row["is_active"]),
        created_at=from_db_utc(row["created_at"]), updated_at=from_db_utc(row["updated_at"]),
    )


def _course_model(row) -> Course:
    view = _course_view(row)
    return Course(
        id=view.id, name=view.name, description=view.description, kind=view.kind,
        duration_minutes=view.duration_minutes, is_active=view.is_active,
        created_at=view.created_at, updated_at=view.updated_at,
    )


def _room_view(row) -> RoomView:
    return RoomView(
        id=int(row["id"]), name=row["name"], location=row["location"],
        is_active=bool(row["is_active"]),
        created_at=from_db_utc(row["created_at"]), updated_at=from_db_utc(row["updated_at"]),
    )


def _room_model(row) -> Room:
    view = _room_view(row)
    return Room(
        id=view.id, name=view.name, location=view.location, is_active=view.is_active,
        created_at=view.created_at, updated_at=view.updated_at,
    )


def _session_view(row) -> SessionView:
    starts_at = from_db_utc(row["starts_at"])
    ends_at = from_db_utc(row["ends_at"])
    capacity = int(row["capacity"])
    occupied = int(row["occupied_count"])
    return SessionView(
        id=int(row["id"]),
        course=CourseView(
            id=int(row["course_id"]), name=row["course_title"], description=row["course_description"],
            kind=row["kind"], duration_minutes=int(row["course_duration"]),
            is_active=bool(row["course_active"]),
            created_at=from_db_utc(row["course_created_at"]),
            updated_at=from_db_utc(row["course_updated_at"]),
        ),
        coach=CoachView(
            id=int(row["coach_id"]), name=row["coach_name"], phone=row["coach_phone"],
            is_active=bool(row["coach_active"]),
            created_at=from_db_utc(row["coach_created_at"]),
            updated_at=from_db_utc(row["coach_updated_at"]),
        ),
        room=RoomView(
            id=int(row["room_id"]), name=row["room_name"], location=row["room_location"],
            is_active=bool(row["room_active"]),
            created_at=from_db_utc(row["room_created_at"]),
            updated_at=from_db_utc(row["room_updated_at"]),
        ),
        course_name=row["course_name"], kind=row["kind"],
        duration_minutes=int(round((ends_at - starts_at).total_seconds() / 60)),
        starts_at=starts_at, ends_at=ends_at, capacity=capacity,
        occupied_count=occupied, available_count=max(capacity - occupied, 0) if row["status"] == "scheduled" else 0,
        status=row["status"], created_at=from_db_utc(row["created_at"]),
        updated_at=from_db_utc(row["updated_at"]),
    )


def _session_model(row) -> CourseSession:
    view = _session_view(row)
    return CourseSession(
        id=view.id, course_id=view.course.id, course_name=view.course_name,
        kind=view.kind, coach_id=view.coach.id, room_id=view.room.id,
        starts_at=view.starts_at, ends_at=view.ends_at, capacity=view.capacity,
        status=view.status, created_at=view.created_at, updated_at=view.updated_at,
    )


def load_session_views(session: Session, session_ids: list[int]) -> dict[int, SessionView]:
    """批量读取课次展示数据，供预约列表组装 SessionView。"""
    if not session_ids:
        return {}
    rows = session.execute(_SESSION_SELECT.where(course_sessions.c.id.in_(set(session_ids)))).mappings().all()
    return {int(row["id"]): _session_view(row) for row in rows}


class CoachRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, coach_id: int) -> CoachView | None:
        row = self._session.execute(select(coaches).where(coaches.c.id == coach_id)).mappings().first()
        return None if row is None else _coach_view(row)

    def list(self, query: NamedQuery) -> Page[CoachView]:
        page, size = validate_paging(query.paging)
        conditions = []
        if query.keyword.strip():
            conditions.append(coaches.c.name.like(f"%{_like(query.keyword.strip())}%", escape="\\"))
        if query.is_active is not None:
            conditions.append(coaches.c.is_active == query.is_active)
        total = int(self._session.scalar(select(func.count()).select_from(coaches).where(*conditions)) or 0)
        rows = self._session.execute(
            select(coaches).where(*conditions).order_by(coaches.c.id).limit(size).offset((page - 1) * size)
        ).mappings().all()
        return Page(items=[_coach_view(row) for row in rows], total=total, page=page, page_size=size)

    def create(self, data: CoachInput) -> CoachView:
        now = utc_now()
        result = self._session.execute(insert(coaches).values(
            name=data.name, phone=data.phone, is_active=True, created_at=now, updated_at=now,
        ))
        view = self.get(int(result.inserted_primary_key[0]))
        if view is None:
            raise StorageError("保存教练档案失败")
        return view

    def update(self, coach_id: int, data: CoachInput) -> CoachView:
        if self.get(coach_id) is None:
            raise NotFoundError("教练不存在")
        self._session.execute(update(coaches).where(coaches.c.id == coach_id).values(
            name=data.name, phone=data.phone, updated_at=utc_now(),
        ))
        view = self.get(coach_id)
        if view is None:
            raise NotFoundError("教练不存在")
        return view

    def set_active(self, coach_id: int, active: bool) -> CoachView:
        if self.get(coach_id) is None:
            raise NotFoundError("教练不存在")
        self._session.execute(update(coaches).where(coaches.c.id == coach_id).values(
            is_active=active, updated_at=utc_now(),
        ))
        view = self.get(coach_id)
        if view is None:
            raise NotFoundError("教练不存在")
        return view

    def set_account(self, coach_id: int, account_id: int) -> CoachView:
        if self.get(coach_id) is None:
            raise NotFoundError("教练不存在")
        existing = self._session.execute(
            select(coach_account_links.c.account_id).where(
                or_(coach_account_links.c.account_id == account_id,
                    coach_account_links.c.coach_id == coach_id)
            )
        ).first()
        if existing is not None:
            self._session.execute(delete(coach_account_links).where(
                or_(coach_account_links.c.account_id == account_id,
                    coach_account_links.c.coach_id == coach_id)
            ))
        self._session.execute(insert(coach_account_links).values(
            account_id=account_id, coach_id=coach_id, linked_at=utc_now(), linked_by=account_id,
        ))
        view = self.get(coach_id)
        if view is None:
            raise NotFoundError("教练不存在")
        return view

    def lock(self, coach_id: int) -> Coach | None:
        row = self._session.execute(
            select(coaches).where(coaches.c.id == coach_id).with_for_update()
        ).mappings().first()
        return None if row is None else _coach_model(row)


class CourseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, course_id: int) -> CourseView | None:
        row = self._session.execute(select(courses).where(courses.c.id == course_id)).mappings().first()
        return None if row is None else _course_view(row)

    def lock(self, course_id: int) -> Course | None:
        row = self._session.execute(
            select(courses).where(courses.c.id == course_id).with_for_update()
        ).mappings().first()
        return None if row is None else _course_model(row)

    def list(self, query: NamedQuery) -> Page[CourseView]:
        page, size = validate_paging(query.paging)
        conditions = []
        if query.keyword.strip():
            conditions.append(courses.c.name.like(f"%{_like(query.keyword.strip())}%", escape="\\"))
        if query.is_active is not None:
            conditions.append(courses.c.is_active == query.is_active)
        total = int(self._session.scalar(select(func.count()).select_from(courses).where(*conditions)) or 0)
        rows = self._session.execute(
            select(courses).where(*conditions).order_by(courses.c.id).limit(size).offset((page - 1) * size)
        ).mappings().all()
        return Page(items=[_course_view(row) for row in rows], total=total, page=page, page_size=size)

    def create(self, data: CourseInput) -> CourseView:
        now = utc_now()
        result = self._session.execute(insert(courses).values(
            name=data.name, description=data.description, kind=data.kind,
            duration_minutes=data.duration_minutes, is_active=True,
            created_at=now, updated_at=now,
        ))
        view = self.get(int(result.inserted_primary_key[0]))
        if view is None:
            raise StorageError("保存课程模板失败")
        return view

    def update(self, course_id: int, data: CourseInput) -> CourseView:
        if self.get(course_id) is None:
            raise NotFoundError("课程模板不存在")
        self._session.execute(update(courses).where(courses.c.id == course_id).values(
            name=data.name, description=data.description, kind=data.kind,
            duration_minutes=data.duration_minutes, updated_at=utc_now(),
        ))
        view = self.get(course_id)
        if view is None:
            raise NotFoundError("课程模板不存在")
        return view

    def set_active(self, course_id: int, active: bool) -> CourseView:
        if self.get(course_id) is None:
            raise NotFoundError("课程模板不存在")
        self._session.execute(update(courses).where(courses.c.id == course_id).values(
            is_active=active, updated_at=utc_now(),
        ))
        view = self.get(course_id)
        if view is None:
            raise NotFoundError("课程模板不存在")
        return view


class RoomRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, room_id: int) -> RoomView | None:
        row = self._session.execute(select(rooms).where(rooms.c.id == room_id)).mappings().first()
        return None if row is None else _room_view(row)

    def list(self, query: NamedQuery) -> Page[RoomView]:
        page, size = validate_paging(query.paging)
        conditions = []
        if query.keyword.strip():
            conditions.append(rooms.c.name.like(f"%{_like(query.keyword.strip())}%", escape="\\"))
        if query.is_active is not None:
            conditions.append(rooms.c.is_active == query.is_active)
        total = int(self._session.scalar(select(func.count()).select_from(rooms).where(*conditions)) or 0)
        rows = self._session.execute(
            select(rooms).where(*conditions).order_by(rooms.c.id).limit(size).offset((page - 1) * size)
        ).mappings().all()
        return Page(items=[_room_view(row) for row in rows], total=total, page=page, page_size=size)

    def create(self, data: RoomInput) -> RoomView:
        now = utc_now()
        result = self._session.execute(insert(rooms).values(
            name=data.name, location=data.location, is_active=True,
            created_at=now, updated_at=now,
        ))
        view = self.get(int(result.inserted_primary_key[0]))
        if view is None:
            raise StorageError("保存场地失败")
        return view

    def update(self, room_id: int, data: RoomInput) -> RoomView:
        if self.get(room_id) is None:
            raise NotFoundError("场地不存在")
        self._session.execute(update(rooms).where(rooms.c.id == room_id).values(
            name=data.name, location=data.location, updated_at=utc_now(),
        ))
        view = self.get(room_id)
        if view is None:
            raise NotFoundError("场地不存在")
        return view

    def set_active(self, room_id: int, active: bool) -> RoomView:
        if self.get(room_id) is None:
            raise NotFoundError("场地不存在")
        self._session.execute(update(rooms).where(rooms.c.id == room_id).values(
            is_active=active, updated_at=utc_now(),
        ))
        view = self.get(room_id)
        if view is None:
            raise NotFoundError("场地不存在")
        return view

    def lock(self, room_id: int) -> Room | None:
        row = self._session.execute(
            select(rooms).where(rooms.c.id == room_id).with_for_update()
        ).mappings().first()
        return None if row is None else _room_model(row)


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, session_id: int) -> SessionView | None:
        row = self._session.execute(_SESSION_SELECT.where(course_sessions.c.id == session_id)).mappings().first()
        return None if row is None else _session_view(row)

    def list(
        self, query: SessionQuery, *, scope_coach_id: int | None,
        bookable_after: "datetime | None",
    ) -> Page[SessionView]:
        page, size = validate_paging(query.paging)
        conditions = []
        if query.window is not None:
            start, end = window_bounds(query.window)
            conditions.extend((course_sessions.c.starts_at >= start, course_sessions.c.starts_at < end))
        if query.kind is not None:
            conditions.append(course_sessions.c.kind == query.kind)
        if query.coach_id is not None:
            conditions.append(course_sessions.c.coach_id == query.coach_id)
        if query.room_id is not None:
            conditions.append(course_sessions.c.room_id == query.room_id)
        if query.status is not None:
            conditions.append(course_sessions.c.status == query.status)
        if scope_coach_id is not None:
            conditions.append(course_sessions.c.coach_id == scope_coach_id)
        if bookable_after is not None:
            conditions.extend((
                course_sessions.c.status == "scheduled",
                course_sessions.c.starts_at > to_db_utc(bookable_after),
            ))
        total = int(self._session.scalar(
            select(func.count()).select_from(course_sessions).where(*conditions)
        ) or 0)
        rows = self._session.execute(
            _SESSION_SELECT.where(*conditions)
            .order_by(course_sessions.c.starts_at, course_sessions.c.id)
            .limit(size).offset((page - 1) * size)
        ).mappings().all()
        return Page(items=[_session_view(row) for row in rows], total=total, page=page, page_size=size)

    def create(self, data: SessionInput, *, course_name: str, kind: CourseKind) -> SessionView:
        now = utc_now()
        result = self._session.execute(insert(course_sessions).values(
            course_id=data.course_id, coach_id=data.coach_id, room_id=data.room_id,
            course_name=course_name, kind=kind,
            starts_at=to_db_utc(data.starts_at), ends_at=to_db_utc(data.ends_at),
            capacity=1, status="scheduled", created_at=now, updated_at=now,
        ))
        view = self.get(int(result.inserted_primary_key[0]))
        if view is None:
            raise StorageError("保存课次失败")
        return view

    def set_status(self, session_id: int, status: SessionStatus) -> SessionView:
        if self.get(session_id) is None:
            raise NotFoundError("课次不存在")
        self._session.execute(update(course_sessions).where(
            course_sessions.c.id == session_id
        ).values(status=status, updated_at=utc_now()))
        view = self.get(session_id)
        if view is None:
            raise NotFoundError("课次不存在")
        return view

    def has_conflict(self, *, coach_id: int, room_id: int, window: DateWindow) -> bool:
        start, end = window_bounds(window)
        row = self._session.execute(
            select(course_sessions.c.id).where(
                course_sessions.c.status != "cancelled",
                course_sessions.c.starts_at < end,
                course_sessions.c.ends_at > start,
                or_(course_sessions.c.coach_id == coach_id,
                    course_sessions.c.room_id == room_id),
            ).with_for_update().limit(1)
        ).first()
        return row is not None

    def has_scheduled_for_coach(self, coach_id: int) -> bool:
        row = self._session.execute(
            select(course_sessions.c.id).where(
                course_sessions.c.coach_id == coach_id,
                course_sessions.c.status == "scheduled",
            ).with_for_update().limit(1)
        ).first()
        return row is not None

    def has_scheduled_for_room(self, room_id: int) -> bool:
        row = self._session.execute(
            select(course_sessions.c.id).where(
                course_sessions.c.room_id == room_id,
                course_sessions.c.status == "scheduled",
            ).with_for_update().limit(1)
        ).first()
        return row is not None

    def lock(self, session_id: int) -> CourseSession | None:
        row = self._session.execute(
            _SESSION_SELECT.where(course_sessions.c.id == session_id).with_for_update()
        ).mappings().first()
        return None if row is None else _session_model(row)
