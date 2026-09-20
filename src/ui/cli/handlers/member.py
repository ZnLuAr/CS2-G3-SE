"""按业务划分的 CLI 交互接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.member_service import MemberService


class MemberHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: MemberService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        raise NotImplementedError("MemberHandler.__init__ 尚未实现")

    def create(self) -> None:
        """组织 MemberService.create_member 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("MemberHandler.create 尚未实现")

    def show(self) -> None:
        """组织 MemberService.get_member 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("MemberHandler.show 尚未实现")

    def list(self) -> None:
        """组织 MemberService.list_members 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("MemberHandler.list 尚未实现")

    def edit(self) -> None:
        """组织 MemberService.update_member 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("MemberHandler.edit 尚未实现")

    def set_active(self) -> None:
        """组织 MemberService.set_member_active 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("MemberHandler.set_active 尚未实现")
