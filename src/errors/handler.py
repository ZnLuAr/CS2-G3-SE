"""CLI 与 TUI 共用的异常处理接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from src.errors.base import ErrorResult


def handle_error(
    error: Exception,
    *,
    operation: str,
    actor_id: int | None = None,
    request_id: str | None = None,
    fatal: bool = False,
) -> ErrorResult:
    """归类异常、生成中文提示并记录一次脱敏错误日志。

    返回：固定的 ErrorResult，包含动作、可选请求编号和原记录编号；提交未知时从异常读取编号。
    边界：不打印、不控制界面、不提交或回滚数据库。
    当前仅保留签名；调用抛 NotImplementedError。"""
    raise NotImplementedError("handle_error 尚未实现")
