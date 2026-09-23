"""数据库错误的类型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from src.errors.base import GymError


class StorageError(GymError):
    """数据库操作失败，由服务负责清理本次事务和资源。"""


class OutcomeUnknownError(StorageError):
    """提交确认丢失，须按原请求或记录编号核实结果。"""

    request_id: str | None
    record_id: int | None

    def __init__(
        self, message: str, *, request_id: str | None = None,
        record_id: int | None = None,
    ) -> None:
        """保存安全提示与核实编号，不含原始表单。"""
        super().__init__(message)
        self.request_id = request_id
        self.record_id = record_id


class InitializationError(StorageError):
    """数据库初始化失败，保存已经确认完成的表和失败步骤。"""

    completed_tables: tuple[str, ...]
    failed_step: str
    outcome_unknown: bool

    def __init__(
        self,
        message: str,
        *,
        completed_tables: tuple[str, ...],
        failed_step: str,
        outcome_unknown: bool = False,
    ) -> None:
        super().__init__(message)
        self.completed_tables = completed_tables
        self.failed_step = failed_step
        self.outcome_unknown = outcome_unknown
