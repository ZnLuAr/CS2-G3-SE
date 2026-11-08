"""采集课程评价表单并展示授权查询结果。"""

from __future__ import annotations

from collections.abc import Callable

from src.logic.review_logic import ReviewLogic
from src.models.contracts import Actor, ReviewInput, ReviewQuery, Role
from src.ui.cli import formatters, prompts


class ReviewHandler:
    def __init__(
        self,
        logic: ReviewLogic,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        self._logic = logic
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    @property
    def current_role(self) -> Role:
        """取得当前菜单角色，业务权限由服务复核。"""
        return self._get_actor().role

    def create_review(self) -> None:
        """收集评分与留言，确认后提交。"""
        actor = self._get_actor()
        booking_id = prompts.prompt_int("预约编号（q 取消）：", minimum=1)
        rating = prompts.prompt_int("评分（1 至 5，q 取消）：", minimum=1, maximum=5)
        comment = prompts.prompt_text("评价留言（可留空，q 取消）：", allow_empty=True)
        if not prompts.prompt_confirm("确认提交评价？"):
            return
        view = self._logic.create_review(
            actor, ReviewInput(booking_id=booking_id, rating=rating, comment=comment),
        )
        print(formatters.format_review(view, timezone_name=self._timezone_name))

    def get_review(self) -> None:
        """按评价编号展示详情。"""
        actor = self._get_actor()
        review_id = prompts.prompt_int("评价编号（q 取消）：", minimum=1)
        view = self._logic.get_review(actor, review_id)
        print(formatters.format_review(view, timezone_name=self._timezone_name))

    def list_reviews(self) -> None:
        """分页展示当前角色可见的评价。"""
        from src.ui.cli.menus import browse_pages

        actor = self._get_actor()
        browse_pages(
            lambda paging: self._logic.list_reviews(actor, ReviewQuery(paging=paging)),
            lambda page: formatters.format_reviews(page, timezone_name=self._timezone_name),
        )
