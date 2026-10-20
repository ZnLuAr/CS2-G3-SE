"""课程推荐 CLI 交互处理器占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.logic.recommendation_logic import RecommendationLogic
from src.models.contracts import Actor


class RecommendationHandler:
    """收集推荐操作输入，调用推荐用例并展示固定 View。"""

    def __init__(
        self,
        logic: RecommendationLogic,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        self._logic = logic
        self._get_actor = get_actor
        self._timezone_name = timezone_name
