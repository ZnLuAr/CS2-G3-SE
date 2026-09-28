"""赠送记录数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import (
    GiftRuleSnapshot,
    RewardGymCardProductSnapshot,
)
from src.models.gift_grant import GiftGrant, GiftGrantAggregate

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class GiftGrantRepository:
    """赠送记录数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("GiftGrantRepository.__init__ 尚未实现")

    def create(
        self,
        trigger_sale_item_id: int,
        member_id: int,
        trigger_product_id: int,
        gift_rule_snapshot: GiftRuleSnapshot,
        reward_product_snapshot: RewardGymCardProductSnapshot,
        sequence: int,
        granted_at: datetime,
    ) -> GiftGrant:
        """创建赠送记录；不自行提交。

        返回：GiftGrant；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GiftGrantRepository.create 尚未实现")

    def list_for_sale_item(
        self, sale_item_id: int
    ) -> list[GiftGrant]:
        """查询指定销售项目触发的所有赠送记录。

        返回：list[GiftGrant]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GiftGrantRepository.list_for_sale_item 尚未实现")

    def get_with_card(
        self, grant_id: int
    ) -> GiftGrantAggregate | None:
        """查询赠送记录及关联的健身房卡。

        返回：GiftGrantAggregate | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GiftGrantRepository.get_with_card 尚未实现")
