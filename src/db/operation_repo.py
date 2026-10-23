"""操作记录（防重复请求）的数据访问；事务由调用方 Logic 管理。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError

from src.db.support import from_db_utc, utc_now
from src.db.tables import operation_records
from src.errors.storage import StorageError
from src.models.contracts import OperationName
from src.models.operation import OperationRecord

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _record(row) -> OperationRecord:
    return OperationRecord(
        id=int(row["id"]), request_id=row["request_id"], actor_id=int(row["actor_id"]),
        operation=row["operation"], payload_hash=row["payload_hash"],
        result_id=int(row["result_id"]), created_at=from_db_utc(row["created_at"]),
    )


class OperationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_request(self, request_id: str) -> OperationRecord | None:
        row = self._session.execute(
            select(operation_records).where(operation_records.c.request_id == request_id)
        ).mappings().first()
        return None if row is None else _record(row)

    def lock_by_request(self, request_id: str) -> OperationRecord | None:
        row = self._session.execute(
            select(operation_records).where(
                operation_records.c.request_id == request_id
            ).with_for_update()
        ).mappings().first()
        return None if row is None else _record(row)

    def create(
        self, *, request_id: str, actor_id: int, operation: OperationName,
        payload_hash: str, result_id: int,
    ) -> OperationRecord:
        now = utc_now()
        try:
            self._session.execute(insert(operation_records).values(
                request_id=request_id, actor_id=actor_id, operation=operation,
                payload_hash=payload_hash, result_id=result_id, created_at=now,
            ))
        except SQLAlchemyError as exc:  # 唯一约束与连接错误都交由 Logic 回滚
            raise StorageError("保存请求记录失败") from exc
        record = self.get_by_request(request_id)
        if record is None:
            raise StorageError("保存后未能读取请求记录")
        return record
