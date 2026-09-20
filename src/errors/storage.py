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
        """接收安全提示与已验证编号，由统一错误处理器取出；不含原始表单。

        record_id 对应当前操作的原业务记录，创建时未取得编号可以为 None。
        当前仅声明接口，调用抛 NotImplementedError。"""
        raise NotImplementedError("OutcomeUnknownError.__init__ 尚未实现")
