"""默认 CLI 的操作边界与主循环。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable

from src.errors.base import ErrorResult
from src.models.contracts import Actor
from src.ui.cli.menus import CliHandlers


def invoke_action(
    action: Callable[[], None],
    *,
    operation: str,
    actor_id: int | None = None,
    request_id: str | None = None,
) -> ErrorResult:
    """执行一次交互并统一处理失败。

    返回：ErrorResult；含义见设计第 7 节。
    后续调用统一错误处理入口，当前不会执行传入的 action。"""
    raise NotImplementedError("invoke_action 尚未实现")


class GymCLI:
    """管理登录菜单、业务菜单与退出；不包含业务规则。"""

    def __init__(
        self,
        handlers: CliHandlers,
        get_actor: Callable[[], Actor],
        logout: Callable[[], None],
    ) -> None:
        """接收处理器集合及身份回调；未登录时 get_actor 抛 AuthenticationError。"""
        raise NotImplementedError("GymCLI.__init__ 尚未实现")

    def run(self) -> int:
        """运行 CLI 循环并返回进程状态码；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCLI.run 尚未实现")
