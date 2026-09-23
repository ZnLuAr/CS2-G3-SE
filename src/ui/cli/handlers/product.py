"""按业务划分的 CLI 交互接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.product_service import ProductService


class ProductHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: ProductService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        self._service = service
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    def create_product(self) -> None:
        """组织 ProductService.create_product 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.create_product 尚未实现")

    def update_product(self) -> None:
        """组织 ProductService.update_product 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.update_product 尚未实现")

    def get_product(self) -> None:
        """组织 ProductService.get_product 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.get_product 尚未实现")

    def list_products(self) -> None:
        """组织 ProductService.list_products 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.list_products 尚未实现")

    def set_product_active(self) -> None:
        """组织 ProductService.set_product_active 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.set_product_active 尚未实现")

    def get_card(self) -> None:
        """组织 ProductService.get_card 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.get_card 尚未实现")

    def list_cards(self) -> None:
        """组织 ProductService.list_cards 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.list_cards 尚未实现")

    def sell_product(self) -> None:
        """组织 ProductService.sell_product 的交互步骤。

        只采集会员、产品和收款方式；确认时说明自动接续，不让用户指定生效日。
        成功展示服务计算的起止日期、购买课节数和收款结果。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.sell_product 尚未实现")

    def get_sale_by_request(self) -> None:
        """组织 ProductService.get_sale_by_request 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("ProductHandler.get_sale_by_request 尚未实现")

    def check_entry(self) -> None:
        """先查今日入场；已有记录显示可重复入场，否则展示今日有效卡供选择。

        调用 get_today_entry 或 list_cards，不扣次；次卡最后一次已在上午扣掉仍可同日再入场。
        列表保持 Page[CardView] 格式，权限由服务检查；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("ProductHandler.check_entry 尚未实现")

    def register_entry(self) -> None:
        """确认会员与卡后生成请求编号，调用 register_entry 并展示当日首次入场结果。

        已有今日记录时沿用其卡；日期不由用户输入，同日重复不扣次。
        提交未知保留原编号供核实，取消输入不写数据；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("ProductHandler.register_entry 尚未实现")

    def get_entry_by_request(self) -> None:
        """用保留的请求编号核实入场结果，显示记录原日期，不把核实当成新入场。"""
        raise NotImplementedError("ProductHandler.get_entry_by_request 尚未实现")
