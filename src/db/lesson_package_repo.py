"""私教课包数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import (
    LessonPackageCreate,
    LessonPackageQuery,
    LessonPackageStatus,
)
from src.models.lesson_package import LessonPackage

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class LessonPackageRepository:
    """私教课包数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("LessonPackageRepository.__init__ 尚未实现")

    def create(self, data: LessonPackageCreate) -> LessonPackage:
        """创建私教课包；不自行提交。

        返回：LessonPackage；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.create 尚未实现")

    def get(
        self, lesson_package_id: int
    ) -> LessonPackage | None:
        """查询私教课包详情；未找到返回 None，由服务转成异常。

        返回：LessonPackage | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.get 尚未实现")

    def lock(
        self, lesson_package_id: int
    ) -> LessonPackage | None:
        """锁定并读取最新课包记录；用于服务事务。

        返回：LessonPackage | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.lock 尚未实现")

    def list(
        self, query: LessonPackageQuery
    ) -> tuple[list[LessonPackage], int]:
        """按条件查询并返回课包列表和总数。

        返回：tuple[list[LessonPackage], int]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.list 尚未实现")

    def reserve_one(self, lesson_package_id: int) -> LessonPackage:
        """预留一节课；不自行提交。

        返回：LessonPackage；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.reserve_one 尚未实现")

    def release_one(self, lesson_package_id: int) -> LessonPackage:
        """释放一节预留课；不自行提交。

        返回：LessonPackage；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.release_one 尚未实现")

    def consume_reserved_one(
        self, lesson_package_id: int
    ) -> LessonPackage:
        """消耗一节预留课；不自行提交。

        返回：LessonPackage；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.consume_reserved_one 尚未实现")

    def set_status(
        self,
        lesson_package_id: int,
        status: LessonPackageStatus,
    ) -> LessonPackage:
        """设置课包状态；不自行提交。

        返回：LessonPackage；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("LessonPackageRepository.set_status 尚未实现")
