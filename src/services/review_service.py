"""评价输入校验、身份复核与数据授权。"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from src.db.booking_repo import BookingRepository
from src.db.review_repo import ReviewRepository
from src.errors import ConflictError, InvalidInputError, InvalidState, NotFoundError, PermissionDenied
from src.models.contracts import Actor, Page, PageRequest, ReviewInput, ReviewQuery, ReviewView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_MAX_ID = 2**63 - 1


def _validate_id(value: int) -> None:
    if type(value) is not int or not 1 <= value <= _MAX_ID:
        raise InvalidInputError("编号必须是数据库范围内的正整数")


class ReviewService:
    """复核当前身份并校验评价权限。事务由调用方用例管理。"""

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def create_review(self, session: Session, actor: Actor, data: ReviewInput) -> ReviewView:
        """锁定本人预约，确认已完成且尚未评价后保存并返回详情。

        权限、输入、归属、状态和重复提交分别通过项目异常报告。
        本方法只新增一条评价，由调用方提交或回滚。
        """
        actor = self._auth.verify_actor(session, actor)
        if actor.role != "member" or actor.member_id is None:
            raise PermissionDenied("只有会员可以提交本人课程的评价")
        if not isinstance(data, ReviewInput):
            raise InvalidInputError("评价输入格式不正确")
        _validate_id(data.booking_id)
        if type(data.rating) is not int or not 1 <= data.rating <= 5:
            raise InvalidInputError("评分必须是 1 至 5 的整数")
        if not isinstance(data.comment, str):
            raise InvalidInputError("评价留言必须是文本")
        comment = data.comment.strip()
        if len(comment) > 1000:
            raise InvalidInputError("评价留言最多 1000 字")

        booking = BookingRepository(session).lock(data.booking_id)
        if booking is None or booking.member_id != actor.member_id:
            raise NotFoundError("预约不存在或不可见")
        if booking.status != "completed":
            raise InvalidState("只有已完成的预约可以评价")
        repository = ReviewRepository(session)
        if repository.has_for_booking(booking.id):
            raise ConflictError("这条预约已有评价")
        return repository.create(replace(data, comment=comment))

    def get_review(self, session: Session, actor: Actor, review_id: int) -> ReviewView:
        """返回授权范围内的详情，不修改数据。

        不可见或不存在抛 NotFoundError；未授权角色抛 PermissionDenied。
        """
        actor = self._auth.verify_actor(session, actor)
        member_id, coach_id = self._scope(actor)
        _validate_id(review_id)
        view = ReviewRepository(session).get(
            review_id, scope_member_id=member_id, scope_coach_id=coach_id,
        )
        if view is None:
            raise NotFoundError("评价不存在或不可见")
        return view

    def list_reviews(self, session: Session, actor: Actor, query: ReviewQuery) -> Page[ReviewView]:
        """返回授权范围内的评价分页，查询条件可进一步缩小范围。

        不修改数据。未授权角色抛 PermissionDenied，非法查询抛 InvalidInputError。
        """
        actor = self._auth.verify_actor(session, actor)
        member_id, coach_id = self._scope(actor)
        if not isinstance(query, ReviewQuery) or not isinstance(query.paging, PageRequest):
            raise InvalidInputError("评价查询格式不正确")
        for value in (query.member_id, query.coach_id):
            if value is not None:
                _validate_id(value)
        paging = query.paging
        if (
            type(paging.page) is not int or not 1 <= paging.page <= _MAX_ID
            or type(paging.page_size) is not int or not 1 <= paging.page_size <= 100
            or (paging.page - 1) * paging.page_size > _MAX_ID
        ):
            raise InvalidInputError("页码须为有效正整数，每页条数须为 1 至 100")

        return ReviewRepository(session).list(
            query, scope_member_id=member_id, scope_coach_id=coach_id,
        )

    @staticmethod
    def _scope(actor: Actor) -> tuple[int | None, int | None]:
        if actor.role == "member" and actor.member_id is not None:
            return actor.member_id, None
        if actor.role == "coach" and actor.coach_id is not None:
            return None, actor.coach_id
        if actor.role == "admin":
            return None, None
        raise PermissionDenied("当前角色无权查看评价")
