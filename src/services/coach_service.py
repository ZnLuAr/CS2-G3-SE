"""教练档案服务；事务由 CourseLogic 管理。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.db.course_repo import CoachRepository, SessionRepository
from src.errors.business import InvalidState, NotFoundError
from src.models.contracts import Actor, CoachInput, CoachView, NamedQuery, Page
from src.services.auth_service import AuthService
from src.services.course_booking_rules import positive_id, require_admin, text_field

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _input(data: CoachInput) -> CoachInput:
    if not isinstance(data, CoachInput):
        from src.errors.business import InvalidInputError
        raise InvalidInputError("教练输入格式不正确")
    return CoachInput(
        name=text_field(data.name, "教练姓名", minimum=1, maximum=100),
        phone=text_field(data.phone, "联系电话", minimum=1, maximum=32, optional=True),
    )


class CoachService:
    """教练档案服务；actor 来自可信登录会话。"""

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def create_coach(self, session: Session, actor: Actor, data: CoachInput) -> CoachView:
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        return CoachRepository(session).create(_input(data))

    def update_coach(self, session: Session, actor: Actor, coach_id: int, data: CoachInput) -> CoachView:
        positive_id(coach_id, "教练编号")
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        repo = CoachRepository(session)
        if repo.lock(coach_id) is None:
            raise NotFoundError("教练不存在")
        return repo.update(coach_id, _input(data))

    def get_coach(self, session: Session, actor: Actor, coach_id: int) -> CoachView:
        positive_id(coach_id, "教练编号")
        current = self._auth.verify_actor(session, actor)
        view = CoachRepository(session).get(coach_id)
        if view is None or (current.role != "admin" and not view.is_active):
            raise NotFoundError("教练不存在或不可见")
        return view

    def list_coaches(self, session: Session, actor: Actor, query: NamedQuery) -> Page[CoachView]:
        if not isinstance(query, NamedQuery):
            from src.errors.business import InvalidInputError
            raise InvalidInputError("教练查询格式不正确")
        current = self._auth.verify_actor(session, actor)
        if current.role != "admin":
            from dataclasses import replace
            query = replace(query, is_active=True)
        return CoachRepository(session).list(query)

    def set_coach_active(self, session: Session, actor: Actor, coach_id: int, is_active: bool) -> CoachView:
        positive_id(coach_id, "教练编号")
        if not isinstance(is_active, bool):
            from src.errors.business import InvalidInputError
            raise InvalidInputError("启用状态必须是布尔值")
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        repo = CoachRepository(session)
        coach = repo.lock(coach_id)
        if coach is None:
            raise NotFoundError("教练不存在")
        if coach.is_active == is_active:
            view = repo.get(coach_id)
            if view is None:
                raise NotFoundError("教练不存在")
            return view
        if not is_active and SessionRepository(session).has_scheduled_for_coach(coach_id):
            raise InvalidState("该教练仍有未结束课次")
        return repo.set_active(coach_id, is_active)
