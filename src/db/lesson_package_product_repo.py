"""私教课包产品数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import (
    LessonPackageProductTerms,
    NamedQuery,
)
from src.models.lesson_package_product import LessonPackageProduct

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class LessonPackageProductRepository:
    """私教课包产品数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("LessonPackageProductRepository.__init__ 尚未实现")

    def create(
        self, terms: LessonPackageProductTerms
    ) -> LessonPackageProduct:
        """创建私教课包产品；不自行提交。

        返回：LessonPackageProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageProductRepository.create 尚未实现")

    def get(
        self, product_id: int
    ) -> LessonPackageProduct | None:
        """查询私教课包产品详情；未找到返回 None，由服务转成异常。

        返回：LessonPackageProduct | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageProductRepository.get 尚未实现")

    def lock(
        self, product_id: int
    ) -> LessonPackageProduct | None:
        """锁定并读取最新产品记录；用于服务事务。

        返回：LessonPackageProduct | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageProductRepository.lock 尚未实现")

    def list(
        self, query: NamedQuery
    ) -> tuple[list[LessonPackageProduct], int]:
        """按条件查询并返回产品列表和总数。

        返回：tuple[list[LessonPackageProduct], int]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageProductRepository.list 尚未实现")

    def update_terms(
        self,
        product_id: int,
        terms: LessonPackageProductTerms,
    ) -> LessonPackageProduct:
        """更新产品条款；不自行提交。

        返回：LessonPackageProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageProductRepository.update_terms 尚未实现")

    def set_sale_enabled(
        self, product_id: int, enabled: bool
    ) -> LessonPackageProduct:
        """设置产品销售启用状态；不自行提交。

        返回：LessonPackageProduct；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageProductRepository.set_sale_enabled 尚未实现")
