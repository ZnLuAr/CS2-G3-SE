"""日志配置和资源关闭接口。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import AppSettings


def configure_logging(settings: AppSettings) -> None:
    """配置日志格式、文件与故障报告。

    配置：
    - 日志目录：settings.log.directory（如 logs/）
    - 日志级别：settings.log.level（如 INFO）
    - 日志文件：logs/app.log
    - 日志格式：UTF-8 单行 JSON
    - 轮转策略：使用 settings.log.max_bytes 和 settings.log.backup_count
    - 跨进程锁：防止多进程写入冲突

    失败处理：
    - 目录不存在 → 尝试创建
    - 创建失败 → 抛出异常（启动阶段）
    - 权限不足 → 抛出异常

    当前不写文件。"""
    raise NotImplementedError("configure_logging 尚未实现")


def close_logging() -> None:
    """关闭日志系统，释放文件句柄。

    在程序退出时调用。
    """
    raise NotImplementedError("close_logging 尚未实现")
