"""场地服务；事务由 CourseLogic 管理。"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from src.db.course_repo import RoomRepository, SessionRepository
from src.errors.business import InvalidInputError, InvalidState, NotFoundError
from src.models.contracts import Actor, NamedQuery, Page, RoomInput, RoomView
from src.services.auth_service import AuthService
from src.services.course_booking_rules import positive_id, require_admin, text_field

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _input(data: RoomInput) -> RoomInput:
    if not isinstance(data, RoomInput):
        raise InvalidInputError("场地输入格式不正确")
    return RoomInput(
        name=text_field(data.name, "场地名称", minimum=1, maximum=100),
        location=text_field(data.location, "位置", minimum=1, maximum=200, optional=True),
    )


class RoomService:
    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def create_room(self, session: Session, actor: Actor, data: RoomInput) -> RoomView:
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        return RoomRepository(session).create(_input(data))

    def update_room(self, session: Session, actor: Actor, room_id: int, data: RoomInput) -> RoomView:
        positive_id(room_id, "场地编号")
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        repo = RoomRepository(session)
        if repo.lock(room_id) is None:
            raise NotFoundError("场地不存在")
        return repo.update(room_id, _input(data))

    def get_room(self, session: Session, actor: Actor, room_id: int) -> RoomView:
        positive_id(room_id, "场地编号")
        current = self._auth.verify_actor(session, actor)
        view = RoomRepository(session).get(room_id)
        if view is None or (current.role != "admin" and not view.is_active):
            raise NotFoundError("场地不存在或不可见")
        return view

    def list_rooms(self, session: Session, actor: Actor, query: NamedQuery) -> Page[RoomView]:
        if not isinstance(query, NamedQuery):
            raise InvalidInputError("场地查询格式不正确")
        current = self._auth.verify_actor(session, actor)
        if current.role != "admin":
            query = replace(query, is_active=True)
        return RoomRepository(session).list(query)

    def set_room_active(self, session: Session, actor: Actor, room_id: int, is_active: bool) -> RoomView:
        positive_id(room_id, "场地编号")
        if not isinstance(is_active, bool):
            raise InvalidInputError("启用状态必须是布尔值")
        current = self._auth.verify_actor(session, actor)
        require_admin(current)
        repo = RoomRepository(session)
        room = repo.lock(room_id)
        if room is None:
            raise NotFoundError("场地不存在")
        if room.is_active == is_active:
            view = repo.get(room_id)
            if view is None:
                raise NotFoundError("场地不存在")
            return view
        if not is_active and SessionRepository(session).has_scheduled_for_room(room_id):
            raise InvalidState("该场地仍有未结束课次")
        return repo.set_active(room_id, is_active)
