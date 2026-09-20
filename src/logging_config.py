"""日志配置与脱敏记录接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from src.config import AppSettings


def configure_logging(settings: AppSettings) -> None:
    """配置日志格式、文件与故障报告；当前不写文件。"""
    raise NotImplementedError("configure_logging 尚未实现")


def log_event(
    level: int,
    *,
    operation: str,
    outcome: str,
    actor_id: int | None = None,
    request_id: str | None = None,
    result_id: int | None = None,
    error: Exception | None = None,
) -> bool:
    """记录允许的事件字段和安全堆栈。

    输入：固定操作名、结果类别和非敏感编号；不得传入原始表单或密码。
    返回：实现后成功为 True，日志失败为 False，不能改变已提交的业务结果。
    当前占位：调用抛 NotImplementedError，不写日志。"""
    raise NotImplementedError("log_event 尚未实现")
