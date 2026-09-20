"""异常基类与固定处理结果。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ErrorAction = Literal["continue", "login", "exit", "verify"]


@dataclass(frozen=True, kw_only=True)
class ErrorResult:
    """中文提示及界面应执行的动作，格式见设计第 7 节。"""

    message: str
    action: ErrorAction
    request_id: str | None = None
    record_id: int | None = None


class GymError(Exception):
    """业务异常基类；message 只允许安全的中文提示。"""

    message: str

    def __init__(self, message: str) -> None:
        """接收可展示的中文错误信息；当前构造方法也仅占位。"""
        raise NotImplementedError("GymError.__init__ 尚未实现")
