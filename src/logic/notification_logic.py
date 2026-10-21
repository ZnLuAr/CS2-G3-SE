"""NotificationLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        NotificationQuery,
        NotificationReadResultView,
        NotificationView,
        Page,
    )
    from src.services.notification_service import NotificationService


class NotificationLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        notification_service: NotificationService,
    ) -> None:
        self._session_factory = session_factory
        self._notification_service = notification_service

    def list_notifications(self, actor: Actor, query: NotificationQuery) -> Page[NotificationView]:
        raise NotImplementedError

    def mark_read(self, actor: Actor, notification_id: int) -> NotificationView:
        raise NotImplementedError

    def mark_all_read(self, actor: Actor) -> NotificationReadResultView:
        raise NotImplementedError
