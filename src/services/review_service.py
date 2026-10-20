"""课程评价服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import Actor, Page, ReviewInput, ReviewQuery, ReviewView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ReviewService:
    """课程评价服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md的返回、异常、权限和事务约定。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_review(self, session: Session, actor: Actor, data: ReviewInput) -> ReviewView:
        """提交本人已完成课程的评价。

        在事务中锁定预约后复核归属、完成状态和既有评价；重复或并发重复提交抛 ConflictError。
        返回：ReviewView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("ReviewService.create_review 尚未实现")

    def get_review(self, session: Session, actor: Actor, review_id: int) -> ReviewView:
        """按评价编号返回授权范围内的 ReviewView。

        会员看本人、教练看本人课次、管理员看全部；前台抛 PermissionDenied。
        记录不存在或对象范围外抛 NotFoundError。

        返回：ReviewView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("ReviewService.get_review 尚未实现")

    def list_reviews(self, session: Session, actor: Actor, query: ReviewQuery) -> Page[ReviewView]:
        """按会员、教练与分页条件返回授权范围内的 Page[ReviewView]。

        会员看本人、教练看本人课次、管理员看全部；前台抛 PermissionDenied。
        SQL 计数和当前页先应用同一范围，再按 created_at DESC, id DESC 排序。

        返回：Page[ReviewView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("ReviewService.list_reviews 尚未实现")
