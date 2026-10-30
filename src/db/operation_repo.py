"""防重复操作记录的数据访问。

仓储只使用调用方传入的会话：不提交、不输出提示、不把数据库异常翻译成业务异常。
未命中查询返回 ``None``，由服务层转换成业务异常。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import OperationName
from src.models.operation import OperationRecord

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_OPERATION_COLUMNS = "id, request_id, actor_id, operation, payload_hash, result_id, created_at"


class OperationRepository:
    """防重复操作记录访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get_by_request(self, request_id: str) -> OperationRecord | None:
        """查询原请求对应结果，供服务核对操作者和内容摘要。

        返回：OperationRecord | None。普通一致性读，不加锁。
        """
        from sqlalchemy import text

        row = self._session.execute(
            text(f"SELECT {_OPERATION_COLUMNS} FROM operation_records WHERE request_id = :request_id"),
            {"request_id": request_id},
        ).mappings().first()
        if row is None:
            return None
        return _to_record(dict(row))

    def lock_by_request(self, request_id: str) -> OperationRecord | None:
        """当前读并锁定已存在的请求记录，供取得业务锁后再次核对。

        记录不存在时返回 None；不预占请求编号、不提交事务。
        """
        from sqlalchemy import text

        row = self._session.execute(
            text(
                f"SELECT {_OPERATION_COLUMNS} FROM operation_records "
                "WHERE request_id = :request_id FOR UPDATE"
            ),
            {"request_id": request_id},
        ).mappings().first()
        if row is None:
            return None
        return _to_record(dict(row))

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

        `request_id` 有唯一约束：并发插入同一编号时，后到的事务在 flush/提交阶段
        抛 `IntegrityError`，由 Logic 回滚整个事务并换新事务回放胜者结果。

        返回：OperationRecord。插入后按请求编号回读，返回数据库实际保存的行。
        """
        from datetime import datetime, timezone

        from sqlalchemy import text

        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self._session.execute(
            text(
                "INSERT INTO operation_records "
                "(request_id, actor_id, operation, payload_hash, result_id, created_at) "
                "VALUES (:request_id, :actor_id, :operation, :payload_hash, :result_id, :created_at)"
            ),
            {
                "request_id": request_id,
                "actor_id": actor_id,
                "operation": operation,
                "payload_hash": payload_hash,
                "result_id": result_id,
                "created_at": created_at,
            },
        )
        created = self.get_by_request(request_id)
        if created is None:
            from src.errors.storage import StorageError

            raise StorageError("保存请求编号记录失败")
        return created


def _to_record(values: dict) -> OperationRecord:
    """把数据库行转换为 OperationRecord；无时区时间按 UTC 补回时区。"""
    from datetime import timezone

    created_at = values["created_at"]
    if created_at is not None:
        values["created_at"] = (
            created_at.replace(tzinfo=timezone.utc)
            if created_at.tzinfo is None
            else created_at.astimezone(timezone.utc)
        )
    return OperationRecord(**values)
