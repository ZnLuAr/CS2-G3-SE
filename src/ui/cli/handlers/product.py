"""产品、销售与入场相关的 CLI 交互接口。构造函数已实现，业务操作仍为占位。

v3 将 v2 的 ProductService 拆成健身房卡产品、私教课包产品、销售、权益查询和门禁
五个服务。本 handler 持有这些 v3 服务的引用，方法仍为占位。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import Actor

if TYPE_CHECKING:
    from src.services.access_service import AccessService
    from src.services.entitlement_query_service import EntitlementQueryService
    from src.services.gym_card_product_service import GymCardProductService
    from src.services.lesson_package_product_service import LessonPackageProductService
    from src.services.sales_service import SalesService


class ProductHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        gym_card_products: GymCardProductService,
        lesson_package_products: LessonPackageProductService,
        sales: SalesService,
        entitlements: EntitlementQueryService,
        access: AccessService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收 v3 拆分后的各服务、身份回调及 App 提供的门店时区。"""
        self._gym_card_products = gym_card_products
        self._lesson_package_products = lesson_package_products
        self._sales = sales
        self._entitlements = entitlements
        self._access = access
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    def create_product(self) -> None:
        """组织健身房卡/私教课包产品创建的交互步骤。"""
        raise NotImplementedError("ProductHandler.create_product 尚未实现")

    def update_product(self) -> None:
        """组织产品修改的交互步骤。"""
        raise NotImplementedError("ProductHandler.update_product 尚未实现")

    def get_product(self) -> None:
        """组织产品详情查询的交互步骤。"""
        raise NotImplementedError("ProductHandler.get_product 尚未实现")

    def list_products(self) -> None:
        """组织产品列表的交互步骤。"""
        raise NotImplementedError("ProductHandler.list_products 尚未实现")

    def set_product_active(self) -> None:
        """组织产品启停的交互步骤。"""
        raise NotImplementedError("ProductHandler.set_product_active 尚未实现")

    def get_card(self) -> None:
        """组织会员权益（健身房卡）详情查询的交互步骤。"""
        raise NotImplementedError("ProductHandler.get_card 尚未实现")

    def list_cards(self) -> None:
        """组织会员权益列表的交互步骤。"""
        raise NotImplementedError("ProductHandler.list_cards 尚未实现")

    def sell_product(self) -> None:
        """组织销售的交互步骤。

        只采集会员、产品和收款方式；确认时说明自动接续，不让用户指定生效日。"""
        raise NotImplementedError("ProductHandler.sell_product 尚未实现")

    def get_sale_by_request(self) -> None:
        """组织按请求编号核实销售结果的交互步骤。"""
        raise NotImplementedError("ProductHandler.get_sale_by_request 尚未实现")

    def check_entry(self) -> None:
        """先查今日入场；已有记录显示可重复入场，否则展示今日有效卡供选择。"""
        raise NotImplementedError("ProductHandler.check_entry 尚未实现")

    def register_entry(self) -> None:
        """确认会员与卡后生成请求编号，调用门禁登记入场并展示当日首次入场结果。"""
        raise NotImplementedError("ProductHandler.register_entry 尚未实现")

    def get_entry_by_request(self) -> None:
        """用保留的请求编号核实入场结果，显示记录原日期，不把核实当成新入场。"""
        raise NotImplementedError("ProductHandler.get_entry_by_request 尚未实现")
