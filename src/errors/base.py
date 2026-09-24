"""异常基类与固定处理结果。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ErrorAction = Literal["continue", "login", "exit", "verify"]


@dataclass(frozen=True, kw_only=True)
class ErrorResult:
    """中文提示及界面应执行的动作，格式见架构“错误处理”。"""

    message: str
    action: ErrorAction
    request_id: str | None = None
    record_id: int | None = None


class GymError(Exception):
    """业务异常基类；message 只允许安全的中文提示。"""

    message: str

    def __init__(self, message: str) -> None:
        """保存可展示的中文错误信息，不携带数据库内部细节。"""
        self.message = message
        super().__init__(message)
