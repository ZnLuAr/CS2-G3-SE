"""防重复操作记录的数据访问实现。

`operation_records` 与业务记录在同一个事务中写入：业务成功但操作记录失败，
整个事务回滚；操作记录先写、业务失败，也不会留下“成功”的假象。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select

from src.db.support import from_db_utc, utc_now
from src.db.tables import operation_records
from src.models.contracts import OperationName
from src.models.operation import OperationRecord

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _record(row) -> OperationRecord:
    """把一行操作记录转换成存储模型。"""
    return OperationRecord(
        id=int(row["id"]),
        request_id=row["request_id"],
        actor_id=int(row["actor_id"]),
        operation=row["operation"],
        payload_hash=row["payload_hash"],
        result_id=int(row["result_id"]),
        created_at=from_db_utc(row["created_at"]),
    )


class OperationRepository:
    """防重复操作记录访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get_by_request(self, request_id: str) -> OperationRecord | None:
        """按请求编号查询原操作；没有记录返回 None。"""
        row = self._session.execute(
            select(operation_records).where(operation_records.c.request_id == request_id)
        ).mappings().first()
        return _record(row) if row is not None else None

    def create(
        self,
        *,
        request_id: str,
        actor_id: int,
        operation: OperationName,
        payload_hash: str,
        result_id: int,
    ) -> OperationRecord:
        """保存请求与结果引用；必须和业务记录一起提交。"""
        now = utc_now()
        self._session.execute(
            insert(operation_records).values(
                request_id=request_id,
                actor_id=actor_id,
                operation=operation,
                payload_hash=payload_hash,
                result_id=result_id,
                created_at=now,
            )
        )
        record = self.get_by_request(request_id)
        if record is None:
            raise RuntimeError("操作记录保存后无法读取")
        return record
