"""AuthLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        AccountInput,
        AccountView,
        Actor,
        CoachAccountLinkInput,
        LogEntry,
        LogQuery,
        LogSnapshot,
        MemberAccountLinkInput,
        NamedQuery,
        Page,
    )
    from src.services.auth_service import AuthService


class AuthLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        auth_service: AuthService,
    ) -> None:
        self._session_factory = session_factory
        self._auth_service = auth_service

    def login(self, username: str, password: str) -> Actor:
        raise NotImplementedError

    def get_current_actor(self, actor: Actor) -> Actor:
        raise NotImplementedError

    def create_account(self, actor: Actor, data: AccountInput) -> AccountView:
        raise NotImplementedError

    def get_account(self, actor: Actor, account_id: int) -> AccountView:
        raise NotImplementedError

    def list_accounts(self, actor: Actor, query: NamedQuery) -> Page[AccountView]:
        raise NotImplementedError

    def set_account_active(self, actor: Actor, account_id: int, active: bool) -> AccountView:
        raise NotImplementedError

    def link_member(self, actor: Actor, data: MemberAccountLinkInput) -> AccountView:
        raise NotImplementedError

    def link_coach(self, actor: Actor, data: CoachAccountLinkInput) -> AccountView:
        raise NotImplementedError

    def relink_member(self, actor: Actor, account_id: int, member_id: int) -> AccountView:
        raise NotImplementedError

    def relink_coach(self, actor: Actor, account_id: int, coach_id: int) -> AccountView:
        raise NotImplementedError

    def open_log_snapshot(self, actor: Actor) -> LogSnapshot:
        raise NotImplementedError

    def query_logs(self, actor: Actor, query: LogQuery, *, snapshot: LogSnapshot) -> Page[LogEntry]:
        raise NotImplementedError
