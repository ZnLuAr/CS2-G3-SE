"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import Page, PageRequest, ReviewInput, ReviewView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ReviewRepository:
    """评价数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("ReviewRepository.__init__ 尚未实现")

    def get(self, review_id: int) -> ReviewView | None:
        """读取评价详情。

        返回：ReviewView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReviewRepository.get 尚未实现")

    def get_by_booking(self, booking_id: int) -> ReviewView | None:
        """预约已加锁后，以锁定当前读读取已有评价，供并发防重检查。

        返回：ReviewView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReviewRepository.get_by_booking 尚未实现")

    def list(self, member_id: int, paging: PageRequest) -> Page[ReviewView]:
        """按 created_at、id 降序稳定分页查询指定会员的评价。

        返回：Page[ReviewView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReviewRepository.list 尚未实现")

    def create(self, data: ReviewInput) -> ReviewView:
        """保存一条评价；重复预约不能覆盖原记录。

        返回：ReviewView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("ReviewRepository.create 尚未实现")
