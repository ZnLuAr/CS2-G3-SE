"""站内通知 CLI 交互处理器占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.logic.notification_logic import NotificationLogic
from src.models.contracts import Actor


class NotificationHandler:
    """收集通知操作输入，调用通知用例并展示固定 View。"""

    def __init__(
        self,
        logic: NotificationLogic,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        self._logic = logic
        self._get_actor = get_actor
        self._timezone_name = timezone_name
