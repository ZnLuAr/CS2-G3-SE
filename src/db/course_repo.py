"""教练、课程模板、场地和课次的数据访问实现。

约定：
- 只使用传入的 SQLAlchemy `Session`，不提交事务、不打印提示；
- 查询不到由服务转换成 `NotFoundError`，写入失败交给服务回滚；
- 时间列统一按 UTC 存储，读取后还原为带 `timezone.utc` 的 datetime；
- 课次展示的占用人数只统计 `reserved` 和 `checked_in`，取消与历史完成不占名额。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, insert, or_, select, update

from src.db.support import (
    escape_like,
    from_db_utc,
    to_db_utc,
    utc_now,
    validate_paging,
    window_bounds,
)
from src.db.tables import (
    accounts,
    bookings,
    coaches,
    course_sessions,
    courses,
    rooms,
)
from src.errors.business import (
    ConflictError,
    InvalidInputError,
    InvalidState,
    NotFoundError,
)
from src.models.contracts import (
    CoachInput,
    CoachUpdateInput,
    CoachView,
    CourseInput,
    CourseKind,
    CourseQuery,
    CourseView,
    DateWindow,
    NamedQuery,
    Page,
    RoomInput,
    RoomView,
    SessionInput,
    SessionQuery,
    SessionStatus,
    SessionView,
)
from src.models.course import Coach, Course, CourseSession, Room

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# 取消的预约不占名额；checked_in 与 reserved 一样占用容量，直到课次结束。
_OCCUPYING_STATUSES = ("reserved", "checked_in")

_occupied = (
    select(
        bookings.c.session_id.label("session_id"),
        func.count().label("occupied"),
    )
    .where(bookings.c.status.in_(_OCCUPYING_STATUSES))
    .group_by(bookings.c.session_id)
    .subquery()
)

_session_select = (
    select(
        course_sessions,
        coaches.c.name.label("coach_name"),
        rooms.c.name.label("room_name"),
        func.coalesce(_occupied.c.occupied, 0).label("occupied_count"),
    )
    .join(coaches, coaches.c.id == course_sessions.c.coach_id)
    .join(rooms, rooms.c.id == course_sessions.c.room_id)
    .outerjoin(_occupied, _occupied.c.session_id == course_sessions.c.id)
)


def _coach_view(row) -> CoachView:
    """把一行教练记录转换成 CoachView。"""
    return CoachView(
        id=int(row["id"]),
        account_id=int(row["account_id"]),
        name=row["name"],
        specialty=row["specialty"],
        is_active=bool(row["is_active"]),
    )


def _coach_model(row) -> Coach:
    """把一行教练记录转换成存储模型，供服务在锁内读取。"""
    return Coach(
        id=int(row["id"]),
        account_id=int(row["account_id"]),
        name=row["name"],
        specialty=row["specialty"],
        is_active=bool(row["is_active"]),
        created_at=from_db_utc(row["created_at"]),
        updated_at=from_db_utc(row["updated_at"]),
    )


def _course_view(row) -> CourseView:
    """把一行课程模板记录转换成 CourseView。"""
    return CourseView(
        id=int(row["id"]),
        name=row["name"],
        kind=row["kind"],
        duration_minutes=int(row["duration_minutes"]),
        is_active=bool(row["is_active"]),
    )


def _course_model(row) -> Course:
    """把一行课程模板记录转换成存储模型，供排课时读取快照来源。"""
    return Course(
        id=int(row["id"]),
        name=row["name"],
        kind=row["kind"],
        duration_minutes=int(row["duration_minutes"]),
        is_active=bool(row["is_active"]),
        created_at=from_db_utc(row["created_at"]),
        updated_at=from_db_utc(row["updated_at"]),
    )


def _room_view(row) -> RoomView:
    """把一行场地记录转换成 RoomView。"""
    return RoomView(
        id=int(row["id"]),
        name=row["name"],
        capacity=int(row["capacity"]),
        is_active=bool(row["is_active"]),
    )


def _room_model(row) -> Room:
    """把一行场地记录转换成存储模型，供排课时读取容量。"""
    return Room(
        id=int(row["id"]),
        name=row["name"],
        capacity=int(row["capacity"]),
        is_active=bool(row["is_active"]),
        created_at=from_db_utc(row["created_at"]),
        updated_at=from_db_utc(row["updated_at"]),
    )


def _session_view(row) -> SessionView:
    """把课次与教练、场地、占用人数的联表结果转换成 SessionView。"""
    capacity = int(row["capacity"])
    occupied = int(row["occupied_count"])
    return SessionView(
        id=int(row["id"]),
        course_id=int(row["course_id"]),
        course_name=row["course_name"],
        kind=row["kind"],
        coach_id=int(row["coach_id"]),
        coach_name=row["coach_name"],
        room_id=int(row["room_id"]),
        room_name=row["room_name"],
        starts_at=from_db_utc(row["starts_at"]),
        ends_at=from_db_utc(row["ends_at"]),
        capacity=capacity,
        occupied_count=occupied,
        available_count=max(capacity - occupied, 0),
        status=row["status"],
    )


def _session_model(row) -> CourseSession:
    """把一行课次记录转换成存储模型，供服务在锁内校验状态。"""
    return CourseSession(
        id=int(row["id"]),
        course_id=int(row["course_id"]),
        course_name=row["course_name"],
        kind=row["kind"],
        coach_id=int(row["coach_id"]),
        room_id=int(row["room_id"]),
        starts_at=from_db_utc(row["starts_at"]),
        ends_at=from_db_utc(row["ends_at"]),
        capacity=int(row["capacity"]),
        status=row["status"],
        created_at=from_db_utc(row["created_at"]),
        updated_at=from_db_utc(row["updated_at"]),
    )


def load_session_views(session: Session, session_ids: list[int]) -> dict[int, SessionView]:
    """按编号批量读取课次展示数据，供预约列表一次性组装 SessionView。

    预约列表最多一页 100 条，先批量查课次再在内存中对应，避免逐条查询。
    """
    if not session_ids:
        return {}
    rows = session.execute(
        _session_select.where(course_sessions.c.id.in_(set(session_ids)))
    ).mappings().all()
    return {int(row["id"]): _session_view(row) for row in rows}


def _keyword_condition(column, keyword: str):
    """构造姓名/名称包含匹配条件；用户输入的 % 和 _ 不当作通配符。"""
    keyword = keyword.strip()
    if not keyword:
        return None
    return column.like(f"%{escape_like(keyword)}%", escape="\\")


class CoachRepository:
    """教练数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get(self, coach_id: int) -> CoachView | None:
        """查询教练详情；不存在返回 None。"""
        row = self._session.execute(
            select(coaches).where(coaches.c.id == coach_id)
        ).mappings().first()
        return _coach_view(row) if row is not None else None

    def list(self, query: NamedQuery) -> Page[CoachView]:
        """按姓名关键词和启用状态分页查询教练，按编号升序保证顺序稳定。"""
        page, page_size = validate_paging(query.paging)
        conditions = []
        keyword_condition = _keyword_condition(coaches.c.name, query.keyword)
        if keyword_condition is not None:
            conditions.append(keyword_condition)
        if query.is_active is not None:
            conditions.append(coaches.c.is_active == query.is_active)

        total = int(self._session.scalar(
            select(func.count()).select_from(coaches).where(*conditions)
        ) or 0)
        rows = self._session.execute(
            select(coaches)
            .where(*conditions)
            .order_by(coaches.c.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).mappings().all()
        return Page(
            items=[_coach_view(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create(self, data: CoachInput) -> CoachView:
        """保存教练资料和账号关联。

        在写入前校验目标账号存在、角色为教练且未绑定其他教练档案：
        - 账号不存在 → NotFoundError
        - 角色不是 coach 或账号已停用 → InvalidState
        - 同一账号已绑定教练 → ConflictError
        """
        account = self._session.execute(
            select(accounts.c.role, accounts.c.is_active).where(accounts.c.id == data.account_id)
        ).mappings().first()
        if account is None:
            raise NotFoundError("教练账号不存在")
        if account["role"] != "coach":
            raise InvalidState("目标账号不是教练角色")
        if not account["is_active"]:
            raise InvalidState("教练账号已停用")

        already_linked = self._session.scalar(
            select(func.count()).select_from(coaches).where(coaches.c.account_id == data.account_id)
        )
        if already_linked:
            raise ConflictError("该账号已关联教练档案")

        now = utc_now()
        result = self._session.execute(
            insert(coaches).values(
                account_id=data.account_id,
                name=data.name,
                specialty=data.specialty,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        coach_id = int(result.inserted_primary_key[0])
        view = self.get(coach_id)
        if view is None:  # 理论上刚插入一定存在，保留明确错误便于排查
            raise NotFoundError("教练档案保存失败")
        return view

    def update(self, coach_id: int, data: CoachUpdateInput) -> CoachView:
        """更新姓名和专长；不改账号关联和启用状态。"""
        if self.get(coach_id) is None:
            raise NotFoundError("教练不存在")
        self._session.execute(
            update(coaches)
            .where(coaches.c.id == coach_id)
            .values(name=data.name, specialty=data.specialty, updated_at=utc_now())
        )
        view = self.get(coach_id)
        if view is None:
            raise NotFoundError("教练不存在")
        return view

    def set_active(self, coach_id: int, active: bool) -> CoachView:
        """更改教练启用状态；停用前要求没有未结束课次。

        未结束课次指状态仍为 `scheduled` 的课次，包括已经过了结束时间但尚未
        完成或取消的课次。管理员需要先完成或取消这些课次，历史记录才能保留下来。
        """
        if self.get(coach_id) is None:
            raise NotFoundError("教练不存在")
        if not active:
            unfinished = self._session.scalar(
                select(func.count())
                .select_from(course_sessions)
                .where(
                    course_sessions.c.coach_id == coach_id,
                    course_sessions.c.status == "scheduled",
                )
            )
            if unfinished:
                raise InvalidState("该教练仍有未结束课次，请先完成或取消")
        self._session.execute(
            update(coaches)
            .where(coaches.c.id == coach_id)
            .values(is_active=active, updated_at=utc_now())
        )
        view = self.get(coach_id)
        if view is None:
            raise NotFoundError("教练不存在")
        return view

    def set_account(self, coach_id: int, account_id: int) -> CoachView:
        """更改教练账号关联；不能留下无账号的教练。"""
        if self.get(coach_id) is None:
            raise NotFoundError("教练不存在")
        self._session.execute(
            update(coaches)
            .where(coaches.c.id == coach_id)
            .values(account_id=account_id, updated_at=utc_now())
        )
        view = self.get(coach_id)
        if view is None:
            raise NotFoundError("教练不存在")
        return view

    def lock(self, coach_id: int) -> Coach | None:
        """锁定教练，供排课冲突校验；不存在返回 None。"""
        row = self._session.execute(
            select(coaches).where(coaches.c.id == coach_id).with_for_update()
        ).mappings().first()
        return _coach_model(row) if row is not None else None


class CourseRepository:
    """课程模板数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get(self, course_id: int) -> CourseView | None:
        """查询课程模板详情；不存在返回 None。"""
        row = self._session.execute(
            select(courses).where(courses.c.id == course_id)
        ).mappings().first()
        return _course_view(row) if row is not None else None

    def lock(self, course_id: int) -> Course | None:
        """在当前事务锁定课程模板并读取最新 Course，不存在返回 None。

        协调模板修改和排课快照；不提交。
        """
        row = self._session.execute(
            select(courses).where(courses.c.id == course_id).with_for_update()
        ).mappings().first()
        return _course_model(row) if row is not None else None

    def list(self, query: CourseQuery) -> Page[CourseView]:
        """按名称、类型和启用状态分页查询课程模板。"""
        page, page_size = validate_paging(query.paging)
        conditions = []
        keyword_condition = _keyword_condition(courses.c.name, query.keyword)
        if keyword_condition is not None:
            conditions.append(keyword_condition)
        if query.kind is not None:
            conditions.append(courses.c.kind == query.kind)
        if query.is_active is not None:
            conditions.append(courses.c.is_active == query.is_active)

        total = int(self._session.scalar(
            select(func.count()).select_from(courses).where(*conditions)
        ) or 0)
        rows = self._session.execute(
            select(courses)
            .where(*conditions)
            .order_by(courses.c.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).mappings().all()
        return Page(
            items=[_course_view(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create(self, data: CourseInput) -> CourseView:
        """保存课程模板；类型和时长由服务校验。"""
        now = utc_now()
        result = self._session.execute(
            insert(courses).values(
                name=data.name,
                kind=data.kind,
                duration_minutes=data.duration_minutes,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        course_id = int(result.inserted_primary_key[0])
        view = self.get(course_id)
        if view is None:
            raise NotFoundError("课程模板保存失败")
        return view

    def update(self, course_id: int, data: CourseInput) -> CourseView:
        """更新课程模板；已发布课次保存名称和类型快照，不随模板变化。"""
        if self.get(course_id) is None:
            raise NotFoundError("课程模板不存在")
        self._session.execute(
            update(courses)
            .where(courses.c.id == course_id)
            .values(
                name=data.name,
                kind=data.kind,
                duration_minutes=data.duration_minutes,
                updated_at=utc_now(),
            )
        )
        view = self.get(course_id)
        if view is None:
            raise NotFoundError("课程模板不存在")
        return view

    def set_active(self, course_id: int, active: bool) -> CourseView:
        """归档或恢复课程模板；已有课次和预约保留可查询。"""
        if self.get(course_id) is None:
            raise NotFoundError("课程模板不存在")
        self._session.execute(
            update(courses)
            .where(courses.c.id == course_id)
            .values(is_active=active, updated_at=utc_now())
        )
        view = self.get(course_id)
        if view is None:
            raise NotFoundError("课程模板不存在")
        return view


class RoomRepository:
    """场地数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get(self, room_id: int) -> RoomView | None:
        """查询场地详情；不存在返回 None。"""
        row = self._session.execute(
            select(rooms).where(rooms.c.id == room_id)
        ).mappings().first()
        return _room_view(row) if row is not None else None

    def list(self, query: NamedQuery) -> Page[RoomView]:
        """按名称关键词和启用状态分页查询场地。"""
        page, page_size = validate_paging(query.paging)
        conditions = []
        keyword_condition = _keyword_condition(rooms.c.name, query.keyword)
        if keyword_condition is not None:
            conditions.append(keyword_condition)
        if query.is_active is not None:
            conditions.append(rooms.c.is_active == query.is_active)

        total = int(self._session.scalar(
            select(func.count()).select_from(rooms).where(*conditions)
        ) or 0)
        rows = self._session.execute(
            select(rooms)
            .where(*conditions)
            .order_by(rooms.c.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).mappings().all()
        return Page(
            items=[_room_view(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create(self, data: RoomInput) -> RoomView:
        """新增场地与容量；容量由服务校验为正整数。"""
        now = utc_now()
        result = self._session.execute(
            insert(rooms).values(
                name=data.name,
                capacity=data.capacity,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        room_id = int(result.inserted_primary_key[0])
        view = self.get(room_id)
        if view is None:
            raise NotFoundError("场地保存失败")
        return view

    def update(self, room_id: int, data: RoomInput) -> RoomView:
        """更新场地资料；缩小容量时不能低于已有课次的占用人数的最大值。"""
        if self.get(room_id) is None:
            raise NotFoundError("场地不存在")
        largest_occupied = self._session.scalar(
            select(func.max(func.coalesce(_occupied.c.occupied, 0)))
            .select_from(
                course_sessions.outerjoin(
                    _occupied, _occupied.c.session_id == course_sessions.c.id
                )
            )
            .where(
                course_sessions.c.room_id == room_id,
                course_sessions.c.status == "scheduled",
            )
        )
        if largest_occupied is not None and data.capacity < int(largest_occupied):
            raise InvalidState("新容量小于已有课次的占用人数")
        self._session.execute(
            update(rooms)
            .where(rooms.c.id == room_id)
            .values(name=data.name, capacity=data.capacity, updated_at=utc_now())
        )
        view = self.get(room_id)
        if view is None:
            raise NotFoundError("场地不存在")
        return view

    def set_active(self, room_id: int, active: bool) -> RoomView:
        """停用或恢复场地；停用前要求没有未结束课次。"""
        if self.get(room_id) is None:
            raise NotFoundError("场地不存在")
        if not active:
            unfinished = self._session.scalar(
                select(func.count())
                .select_from(course_sessions)
                .where(
                    course_sessions.c.room_id == room_id,
                    course_sessions.c.status == "scheduled",
                )
            )
            if unfinished:
                raise InvalidState("该场地仍有未结束课次，请先完成或取消")
        self._session.execute(
            update(rooms)
            .where(rooms.c.id == room_id)
            .values(is_active=active, updated_at=utc_now())
        )
        view = self.get(room_id)
        if view is None:
            raise NotFoundError("场地不存在")
        return view

    def lock(self, room_id: int) -> Room | None:
        """锁定场地，供排课冲突校验；不存在返回 None。"""
        row = self._session.execute(
            select(rooms).where(rooms.c.id == room_id).with_for_update()
        ).mappings().first()
        return _room_model(row) if row is not None else None


class SessionRepository:
    """具体课次数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get(self, session_id: int) -> SessionView | None:
        """读取课次及余位展示数据；不存在返回 None。"""
        row = self._session.execute(
            _session_select.where(course_sessions.c.id == session_id)
        ).mappings().first()
        return _session_view(row) if row is not None else None

    def list(self, query: SessionQuery) -> Page[SessionView]:
        """分页读取课表，不附带会员名单；按开始时间和编号稳定排序。"""
        page, page_size = validate_paging(query.paging)
        conditions = []
        if query.window is not None:
            start, end = window_bounds(query.window)
            conditions.append(course_sessions.c.starts_at >= start)
            conditions.append(course_sessions.c.starts_at < end)
        if query.kind is not None:
            conditions.append(course_sessions.c.kind == query.kind)
        if query.coach_id is not None:
            conditions.append(course_sessions.c.coach_id == query.coach_id)
        if query.room_id is not None:
            conditions.append(course_sessions.c.room_id == query.room_id)
        if query.status is not None:
            conditions.append(course_sessions.c.status == query.status)

        total = int(self._session.scalar(
            select(func.count()).select_from(course_sessions).where(*conditions)
        ) or 0)
        rows = self._session.execute(
            _session_select
            .where(*conditions)
            .order_by(course_sessions.c.starts_at, course_sessions.c.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).mappings().all()
        return Page(
            items=[_session_view(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create(
        self, data: SessionInput, *, course_name: str, kind: CourseKind,
    ) -> SessionView:
        """保存已校验的排课资料；课程名称和类型保存为排课时的快照。"""
        now = utc_now()
        result = self._session.execute(
            insert(course_sessions).values(
                course_id=data.course_id,
                course_name=course_name,
                kind=kind,
                coach_id=data.coach_id,
                room_id=data.room_id,
                starts_at=to_db_utc(data.starts_at),
                ends_at=to_db_utc(data.ends_at),
                capacity=data.capacity,
                status="scheduled",
                created_at=now,
                updated_at=now,
            )
        )
        session_id = int(result.inserted_primary_key[0])
        view = self.get(session_id)
        if view is None:
            raise NotFoundError("课次保存失败")
        return view

    def set_status(self, session_id: int, status: SessionStatus) -> SessionView:
        """更新课次状态，不自行处理关联预约。"""
        if self.get(session_id) is None:
            raise NotFoundError("课次不存在")
        self._session.execute(
            update(course_sessions)
            .where(course_sessions.c.id == session_id)
            .values(status=status, updated_at=utc_now())
        )
        view = self.get(session_id)
        if view is None:
            raise NotFoundError("课次不存在")
        return view

    def has_conflict(self, *, coach_id: int, room_id: int, window: DateWindow) -> bool:
        """检查教练或场地时间重叠，排除取消课次。

        区间按 [starts_at, ends_at) 判断：14:00–15:00 与 15:00–16:00 相邻不算冲突；
        14:00–15:00 与 14:30–15:30 重叠，算冲突。
        """
        start, end = window_bounds(window)
        conflict = self._session.scalar(
            select(func.count())
            .select_from(course_sessions)
            .where(
                course_sessions.c.status != "cancelled",
                course_sessions.c.starts_at < end,
                course_sessions.c.ends_at > start,
                or_(
                    course_sessions.c.coach_id == coach_id,
                    course_sessions.c.room_id == room_id,
                ),
            )
        )
        return bool(conflict)

    def has_course_sessions(self, course_id: int) -> bool:
        """检查模板是否已有任何课次引用，包含取消课次；供服务限制类型修改。"""
        count = self._session.scalar(
            select(func.count())
            .select_from(course_sessions)
            .where(course_sessions.c.course_id == course_id)
        )
        return bool(count)

    def lock(self, session_id: int) -> CourseSession | None:
        """锁定并读取课次，供容量与状态校验；不存在返回 None。"""
        row = self._session.execute(
            select(course_sessions)
            .where(course_sessions.c.id == session_id)
            .with_for_update()
        ).mappings().first()
        return _session_model(row) if row is not None else None
