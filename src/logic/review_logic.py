"""评价用例入口，管理会话和事务。"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from src.db.connection import transaction
from src.errors import OutcomeUnknownError, StorageError
from src.logging import Operation, Outcome, log_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import Actor, Page, ReviewInput, ReviewQuery, ReviewView
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
        """提交评价，提交结果未知时附上记录编号供详情核实。"""
        retry_deadlock = True
        while True:
            result = None
            try:
                with self._session_factory() as session, transaction(session):
                    result = self._review_service.create_review(session, actor, data)
            except OutcomeUnknownError as exc:
                if result is not None:
                    exc.record_id = result.id
                raise
            except SQLAlchemyError as exc:
                # MySQL 1213 表示事务已回滚，可用新会话重试一次。
                if not (
                    retry_deadlock and isinstance(exc, OperationalError)
                    and exc.orig.args and exc.orig.args[0] == 1213
                ):
                    raise StorageError("保存评价失败") from exc
                retry_deadlock = False
            else:
                break

        try:
            log_event(
                logging.INFO, operation=Operation.REVIEW_CREATE.value, outcome=Outcome.SUCCESS.value,
                actor_id=actor.account_id, result_id=result.id,
            )
        except Exception:
            try:
                print("操作日志记录失败", file=sys.stderr)
            except (OSError, ValueError):
                pass
        return result

    def get_review(self, actor: Actor, review_id: int) -> ReviewView:
        """使用短事务读取授权详情并释放身份锁。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._review_service.get_review(session, actor, review_id)
        except SQLAlchemyError as exc:
            raise StorageError("查询评价失败") from exc

    def list_reviews(self, actor: Actor, query: ReviewQuery) -> Page[ReviewView]:
        """在同一事务快照内读取授权总数与当前页。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._review_service.list_reviews(session, actor, query)
        except SQLAlchemyError as exc:
            raise StorageError("查询评价列表失败") from exc
