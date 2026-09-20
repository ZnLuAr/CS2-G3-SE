"""可选 TUI 的入口签名。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable

from src.app import ServiceBundle
from src.models.contracts import Actor


class GymTUI:
    """通过共用业务服务实现可选界面，后续按时间安排页面。"""

    def __init__(
        self,
        services: ServiceBundle,
        get_actor: Callable[[], Actor],
        set_actor: Callable[[Actor], None],
        logout: Callable[[], None],
        *, timezone_name: str,
    ) -> None:
        """接收共用服务和身份回调；当前不导入任何 TUI 库。"""
        raise NotImplementedError("GymTUI.__init__ 尚未实现")

    def run(self) -> int:
        """运行 TUI 并返回退出码；页面和后台任务均待实现。"""
        raise NotImplementedError("GymTUI.run 尚未实现")

    def close(self) -> None:
        """关闭 TUI 自身的资源；数据库生命周期由 App 管理。"""
        raise NotImplementedError("GymTUI.close 尚未实现")
