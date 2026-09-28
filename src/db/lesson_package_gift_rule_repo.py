"""私教课包赠卡规则数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import (
    LessonPackageGiftRuleInput,
    LessonPackageGiftRuleQuery,
)
from src.models.lesson_package_gift_rule import LessonPackageGiftRule

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class LessonPackageGiftRuleRepository:
    """私教课包赠卡规则数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.__init__ 尚未实现")

    def get(
        self, rule_id: int
    ) -> LessonPackageGiftRule | None:
        """查询赠卡规则详情；未找到返回 None，由服务转成异常。

        返回：LessonPackageGiftRule | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.get 尚未实现")

    def lock(
        self, rule_id: int
    ) -> LessonPackageGiftRule | None:
        """锁定并读取最新规则记录；用于服务事务。

        返回：LessonPackageGiftRule | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.lock 尚未实现")

    def list(
        self, query: LessonPackageGiftRuleQuery
    ) -> tuple[list[LessonPackageGiftRule], int]:
        """按条件查询并返回规则列表和总数。

        返回：tuple[list[LessonPackageGiftRule], int]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.list 尚未实现")

    def lock_versions_for_trigger(
        self, trigger_product_id: int
    ) -> list[LessonPackageGiftRule]:
        """锁定指定触发产品的所有版本规则，按 id 升序返回。

        返回：list[LessonPackageGiftRule]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.lock_versions_for_trigger 尚未实现")

    def lock_active_for_trigger(
        self, trigger_product_id: int
    ) -> LessonPackageGiftRule | None:
        """锁定指定触发产品的启用规则；最多一个。

        返回：LessonPackageGiftRule | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.lock_active_for_trigger 尚未实现")

    def lock_active_for_reward(
        self, reward_gym_card_product_id: int
    ) -> list[LessonPackageGiftRule]:
        """锁定以指定产品作为奖励的所有启用规则，按 id 升序返回。

        返回：list[LessonPackageGiftRule]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.lock_active_for_reward 尚未实现")

    def create_version(
        self,
        data: LessonPackageGiftRuleInput,
        version: int,
        is_active: bool,
    ) -> LessonPackageGiftRule:
        """创建规则版本；不自行提交。

        返回：LessonPackageGiftRule；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.create_version 尚未实现")

    def set_active(
        self, rule_id: int, active: bool
    ) -> LessonPackageGiftRule:
        """设置规则启用状态；不自行提交。

        返回：LessonPackageGiftRule；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageGiftRuleRepository.set_active 尚未实现")
