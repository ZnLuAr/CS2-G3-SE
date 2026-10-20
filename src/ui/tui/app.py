"""可选终端界面的入口合同，方法为占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.logic import LogicBundle
from src.models.contracts import Actor


class GymTUI:
    """可选终端界面，共用 Logic 用例入口；页面与操作为占位。"""

    def __init__(
        self,
        logic_bundle: LogicBundle,
        get_actor: Callable[[], Actor],
        set_actor: Callable[[Actor], None],
        logout: Callable[[], None],
        *, timezone_name: str,
    ) -> None:
        """接收共用用例入口、身份回调与时区配置。"""
        raise NotImplementedError("GymTUI.__init__ 尚未实现")

    def run(self) -> int:
        """运行 TUI 并返回退出码；页面和后台任务均待实现。"""
        raise NotImplementedError("GymTUI.run 尚未实现")

    def close(self) -> None:
        """关闭 TUI 自身的资源；数据库生命周期由 App 管理。"""
        raise NotImplementedError("GymTUI.close 尚未实现")
