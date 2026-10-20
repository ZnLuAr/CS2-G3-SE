"""CourseLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        CoachInput,
        CoachView,
        CourseInput,
        CourseView,
        NamedQuery,
        Page,
        RoomInput,
        RoomView,
        SessionInput,
        SessionQuery,
        SessionView,
    )
    from src.services.coach_service import CoachService
    from src.services.course_service import CourseService
    from src.services.room_service import RoomService


class CourseLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        coach_service: CoachService,
        course_service: CourseService,
        room_service: RoomService,
    ) -> None:
        self._session_factory = session_factory
        self._coach_service = coach_service
        self._course_service = course_service
        self._room_service = room_service

    def create_coach(self, actor: Actor, data: CoachInput) -> CoachView:
        raise NotImplementedError

    def update_coach(self, actor: Actor, coach_id: int, data: CoachInput) -> CoachView:
        raise NotImplementedError

    def get_coach(self, actor: Actor, coach_id: int) -> CoachView:
        raise NotImplementedError

    def list_coaches(self, actor: Actor, query: NamedQuery) -> Page[CoachView]:
        raise NotImplementedError

    def set_coach_active(self, actor: Actor, coach_id: int, is_active: bool) -> CoachView:
        raise NotImplementedError

    def create_course(self, actor: Actor, data: CourseInput) -> CourseView:
        raise NotImplementedError

    def update_course(self, actor: Actor, course_id: int, data: CourseInput) -> CourseView:
        raise NotImplementedError

    def get_course(self, actor: Actor, course_id: int) -> CourseView:
        raise NotImplementedError

    def list_courses(self, actor: Actor, query: NamedQuery) -> Page[CourseView]:
        raise NotImplementedError

    def set_course_active(self, actor: Actor, course_id: int, is_active: bool) -> CourseView:
        raise NotImplementedError

    def create_session(self, actor: Actor, data: SessionInput, request_id: str) -> SessionView:
        raise NotImplementedError

    def get_session(self, actor: Actor, session_id: int) -> SessionView:
        raise NotImplementedError

    def list_sessions(self, actor: Actor, query: SessionQuery) -> Page[SessionView]:
        raise NotImplementedError

    def get_session_by_request(self, actor: Actor, request_id: str) -> SessionView:
        raise NotImplementedError

    def complete_session(self, actor: Actor, session_id: int) -> SessionView:
        raise NotImplementedError

    def create_room(self, actor: Actor, data: RoomInput) -> RoomView:
        raise NotImplementedError

    def update_room(self, actor: Actor, room_id: int, data: RoomInput) -> RoomView:
        raise NotImplementedError

    def get_room(self, actor: Actor, room_id: int) -> RoomView:
        raise NotImplementedError

    def list_rooms(self, actor: Actor, query: NamedQuery) -> Page[RoomView]:
        raise NotImplementedError

    def set_room_active(self, actor: Actor, room_id: int, is_active: bool) -> RoomView:
        raise NotImplementedError
