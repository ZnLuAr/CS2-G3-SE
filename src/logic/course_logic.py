"""课程、教练、场地与课次的用例入口；负责会话、事务和操作日志。"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from src.db.connection import transaction
from src.errors import StorageError
from src.logging import Operation, Outcome, log_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.services.coach_service import CoachService
    from src.services.course_service import CourseService
    from src.services.room_service import RoomService

T = TypeVar("T")


def _log(operation: str, actor: object, result_id: int | None = None, request_id: str | None = None) -> None:
    try:
        log_event(
            logging.INFO, operation=operation, outcome=Outcome.SUCCESS.value,
            actor_id=getattr(actor, "account_id", None), request_id=request_id, result_id=result_id,
        )
    except Exception:
        print("操作日志记录失败", file=sys.stderr)


class CourseLogic:
    def __init__(
        self, session_factory: Callable[[], Session],
        coach_service: CoachService, course_service: CourseService, room_service: RoomService,
    ) -> None:
        self._session_factory = session_factory
        self._coach_service = coach_service
        self._course_service = course_service
        self._room_service = room_service

    def _read(self, action: Callable[[Session], T]) -> T:
        try:
            with self._session_factory() as session, transaction(session):
                return action(session)
        except SQLAlchemyError as exc:
            raise StorageError("查询课程资料失败") from exc

    def _write(self, action: Callable[[Session], T], *, operation: str,
               actor: object, request_id: str | None = None) -> T:
        try:
            with self._session_factory() as session, transaction(session, request_id=request_id):
                result = action(session)
        except SQLAlchemyError as exc:
            raise StorageError("保存课程资料失败") from exc
        _log(operation, actor, getattr(result, "id", None), request_id)
        return result

    def create_coach(self, actor, data):
        return self._write(lambda s: self._coach_service.create_coach(s, actor, data),
                           operation=Operation.COACH_CREATE.value,
                           actor=actor)

    def update_coach(self, actor, coach_id, data):
        return self._write(lambda s: self._coach_service.update_coach(s, actor, coach_id, data),
                           operation=Operation.COACH_UPDATE.value, actor=actor)

    def get_coach(self, actor, coach_id):
        return self._read(lambda s: self._coach_service.get_coach(s, actor, coach_id))

    def list_coaches(self, actor, query):
        return self._read(lambda s: self._coach_service.list_coaches(s, actor, query))

    def set_coach_active(self, actor, coach_id, is_active):
        return self._write(lambda s: self._coach_service.set_coach_active(s, actor, coach_id, is_active),
                           operation=Operation.COACH_UPDATE.value, actor=actor)

    def create_course(self, actor, data):
        return self._write(lambda s: self._course_service.create_course(s, actor, data),
                           operation=Operation.COURSE_CREATE.value, actor=actor)

    def update_course(self, actor, course_id, data):
        return self._write(lambda s: self._course_service.update_course(s, actor, course_id, data),
                           operation=Operation.COURSE_UPDATE.value, actor=actor)

    def get_course(self, actor, course_id):
        return self._read(lambda s: self._course_service.get_course(s, actor, course_id))

    def list_courses(self, actor, query):
        return self._read(lambda s: self._course_service.list_courses(s, actor, query))

    def set_course_active(self, actor, course_id, is_active):
        return self._write(lambda s: self._course_service.set_course_active(s, actor, course_id, is_active),
                           operation=Operation.COURSE_UPDATE.value, actor=actor)

    def create_session(self, actor, data, request_id):
        return self._write(lambda s: self._course_service.create_session(s, actor, data, request_id),
                           operation=Operation.SESSION_CREATE.value, actor=actor, request_id=request_id)

    def get_session(self, actor, session_id):
        return self._read(lambda s: self._course_service.get_session(s, actor, session_id))

    def list_sessions(self, actor, query):
        return self._read(lambda s: self._course_service.list_sessions(s, actor, query))

    def get_session_by_request(self, actor, request_id):
        return self._read(lambda s: self._course_service.get_session_by_request(s, actor, request_id))

    def complete_session(self, actor, session_id):
        return self._write(lambda s: self._course_service.complete_session(s, actor, session_id),
                           operation=Operation.SESSION_COMPLETE.value, actor=actor)

    def create_room(self, actor, data):
        return self._write(lambda s: self._room_service.create_room(s, actor, data),
                           operation="room.create", actor=actor)

    def update_room(self, actor, room_id, data):
        return self._write(lambda s: self._room_service.update_room(s, actor, room_id, data),
                           operation="room.update", actor=actor)

    def get_room(self, actor, room_id):
        return self._read(lambda s: self._room_service.get_room(s, actor, room_id))

    def list_rooms(self, actor, query):
        return self._read(lambda s: self._room_service.list_rooms(s, actor, query))

    def set_room_active(self, actor, room_id, is_active):
        return self._write(lambda s: self._room_service.set_room_active(s, actor, room_id, is_active),
                           operation="room.update", actor=actor)
