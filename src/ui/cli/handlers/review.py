"""按业务划分的 CLI 交互接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.review_service import ReviewService


class ReviewHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: ReviewService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        self._service = service
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    def create_review(self) -> None:
        """组织 ReviewService.create_review 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReviewHandler.create_review 尚未实现")

    def get_review(self) -> None:
        """组织 ReviewService.get_review 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReviewHandler.get_review 尚未实现")

    def list_reviews(self) -> None:
        """组织 ReviewService.list_reviews 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ReviewHandler.list_reviews 尚未实现")
