"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import OperationName
from src.models.operation import OperationRecord

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class OperationRepository:
    """防重复操作记录访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("OperationRepository.__init__ 尚未实现")

    def get_by_request(self, request_id: str) -> OperationRecord | None:
        """查询原请求对应结果，供服务核对操作者和内容摘要。

        返回：OperationRecord | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("OperationRepository.get_by_request 尚未实现")

    def lock_by_request(self, request_id: str) -> OperationRecord | None:
        """当前读并锁定已存在的请求记录，供取得业务锁后再次核对。

        记录不存在时返回 None；不预占请求编号、不提交事务。当前仅占位。"""
        raise NotImplementedError("OperationRepository.lock_by_request 尚未实现")

    def create(
        self,
        *,
        request_id: str,
        actor_id: int,
        operation: OperationName,
        payload_hash: str,
        result_id: int,
    ) -> OperationRecord:
        """保存请求与结果引用；必须和业务记录一起提交。

        返回：OperationRecord；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("OperationRepository.create 尚未实现")
