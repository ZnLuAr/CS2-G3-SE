"""课程评价服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import Actor, Page, PageRequest, ReviewInput, ReviewView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ReviewService:
    """课程评价服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_review(self, actor: Actor, data: ReviewInput) -> ReviewView:
        """提交本人已完成课程的评价。

        返回：ReviewView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReviewService.create_review 尚未实现")

    def get_review(self, actor: Actor, review_id: int) -> ReviewView:
        """查看本人评价详情。

        返回：ReviewView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReviewService.get_review 尚未实现")

    def list_reviews(self, actor: Actor, paging: PageRequest) -> Page[ReviewView]:
        """分页查询本人评价。

        返回：Page[ReviewView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("ReviewService.list_reviews 尚未实现")
