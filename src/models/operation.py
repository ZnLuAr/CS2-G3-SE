"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.contracts import OperationName


@dataclass(frozen=True, kw_only=True)
class OperationRecord:
    """对应 operation_records 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    request_id: str
    actor_id: int
    operation: OperationName
    payload_hash: str
    result_id: int
    created_at: datetime
