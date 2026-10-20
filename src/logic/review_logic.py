"""ReviewLogic use-case entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        Page,
        ReviewInput,
        ReviewQuery,
        ReviewView,
    )
    from src.services.review_service import ReviewService


class ReviewLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        review_service: ReviewService,
    ) -> None:
        self._session_factory = session_factory
        self._review_service = review_service

    def create_review(self, actor: Actor, data: ReviewInput) -> ReviewView:
        raise NotImplementedError

    def get_review(self, actor: Actor, review_id: int) -> ReviewView:
        raise NotImplementedError

    def list_reviews(self, actor: Actor, query: ReviewQuery) -> Page[ReviewView]:
        raise NotImplementedError
