"""MemberLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        MemberInput,
        MemberQuery,
        MemberStatus,
        MemberView,
        Page,
    )
    from src.services.member_service import MemberService


class MemberLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        member_service: MemberService,
    ) -> None:
        self._session_factory = session_factory
        self._member_service = member_service

    def create_member(self, actor: Actor, data: MemberInput, request_id: str) -> MemberView:
        raise NotImplementedError

    def get_member_by_request(self, actor: Actor, request_id: str) -> MemberView:
        raise NotImplementedError

    def get_member(self, actor: Actor, member_id: int) -> MemberView:
        raise NotImplementedError

    def list_members(self, actor: Actor, query: MemberQuery) -> Page[MemberView]:
        raise NotImplementedError

    def update_member(self, actor: Actor, member_id: int, data: MemberInput) -> MemberView:
        raise NotImplementedError

    def set_member_status(self, actor: Actor, member_id: int, status: MemberStatus) -> MemberView:
        raise NotImplementedError
