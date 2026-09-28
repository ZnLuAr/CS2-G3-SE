"""健身房卡产品数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import (
    DurationGymCardProductTerms,
    NamedQuery,
    VisitGymCardProductTerms,
)
from src.models.gym_card_product import (
    DurationGymCardProduct,
    GymCardProduct,
    VisitGymCardProduct,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class GymCardProductRepository:
    """健身房卡产品数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("GymCardProductRepository.__init__ 尚未实现")

    def create_duration(
        self, terms: DurationGymCardProductTerms
    ) -> DurationGymCardProduct:
        """创建期限型健身房卡产品；不自行提交。

        返回：DurationGymCardProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.create_duration 尚未实现")

    def create_visit(
        self, terms: VisitGymCardProductTerms
    ) -> VisitGymCardProduct:
        """创建次卡型健身房卡产品；不自行提交。

        返回：VisitGymCardProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.create_visit 尚未实现")

    def get(self, product_id: int) -> GymCardProduct | None:
        """查询健身房卡产品详情；未找到返回 None，由服务转成异常。

        返回：GymCardProduct | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.get 尚未实现")

    def lock(self, product_id: int) -> GymCardProduct | None:
        """锁定并读取最新产品记录；用于服务事务。

        返回：GymCardProduct | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.lock 尚未实现")

    def lock_duration(
        self, product_id: int
    ) -> DurationGymCardProduct | None:
        """锁定并读取期限型产品；用于服务事务。

        返回：DurationGymCardProduct | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.lock_duration 尚未实现")

    def lock_visit(
        self, product_id: int
    ) -> VisitGymCardProduct | None:
        """锁定并读取次卡型产品；用于服务事务。

        返回：VisitGymCardProduct | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.lock_visit 尚未实现")

    def list(
        self, query: NamedQuery
    ) -> tuple[list[GymCardProduct], int]:
        """按条件查询并返回产品列表和总数。

        返回：tuple[list[GymCardProduct], int]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.list 尚未实现")

    def update_duration_terms(
        self,
        product_id: int,
        terms: DurationGymCardProductTerms,
    ) -> DurationGymCardProduct:
        """更新期限型产品条款；不自行提交。

        返回：DurationGymCardProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.update_duration_terms 尚未实现")

    def update_visit_terms(
        self,
        product_id: int,
        terms: VisitGymCardProductTerms,
    ) -> VisitGymCardProduct:
        """更新次卡型产品条款；不自行提交。

        返回：VisitGymCardProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.update_visit_terms 尚未实现")

    def set_sale_enabled(
        self, product_id: int, enabled: bool
    ) -> GymCardProduct:
        """设置产品销售启用状态；不自行提交。

        返回：GymCardProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.set_sale_enabled 尚未实现")

    def set_duration_gift_enabled(
        self, product_id: int, enabled: bool
    ) -> DurationGymCardProduct:
        """设置期限型产品赠送启用状态；不自行提交。

        返回：DurationGymCardProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardProductRepository.set_duration_gift_enabled 尚未实现")
