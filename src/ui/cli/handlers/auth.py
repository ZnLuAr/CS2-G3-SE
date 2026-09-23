"""按业务划分的 CLI 交互接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.auth_service import AuthService


class AuthHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: AuthService,
        get_actor: Callable[[], Actor],
        set_actor: Callable[[Actor], None],
        logout: Callable[[], None],
        *, timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        self._service = service
        self._get_actor = get_actor
        self._set_actor = set_actor
        self._logout = logout
        self._timezone_name = timezone_name

    def login(self) -> None:
        """组织 AuthService.login 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AuthHandler.login 尚未实现")

    def logout(self) -> None:
        """清除当前登录身份与私有界面状态。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AuthHandler.logout 尚未实现")

    def create_account(self) -> None:
        """组织 AuthService.create_account 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AuthHandler.create_account 尚未实现")

    def get_account(self) -> None:
        """组织 AuthService.get_account 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AuthHandler.get_account 尚未实现")

    def list_accounts(self) -> None:
        """组织 AuthService.list_accounts 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AuthHandler.list_accounts 尚未实现")

    def set_account_active(self) -> None:
        """组织 AuthService.set_account_active 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AuthHandler.set_account_active 尚未实现")

    def link_profile(self) -> None:
        """组织 AuthService.link_profile 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("AuthHandler.link_profile 尚未实现")
