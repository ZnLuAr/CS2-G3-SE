"""AccessLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        EntryInput,
        EntryView,
    )
    from src.services.access_service import AccessService


class AccessLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        access_service: AccessService,
    ) -> None:
        self._session_factory = session_factory
        self._access_service = access_service

    def get_today_entry(self, actor: Actor, member_id: int) -> EntryView:
        raise NotImplementedError

    def register_entry(self, actor: Actor, data: EntryInput, request_id: str) -> EntryView:
        raise NotImplementedError

    def get_entry_by_request(self, actor: Actor, request_id: str) -> EntryView:
        raise NotImplementedError
