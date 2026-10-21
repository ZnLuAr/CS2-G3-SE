"""固定日志快照的读取与分页查询接口。"""

from __future__ import annotations

from pathlib import Path

from src.models.contracts import LogEntry, LogQuery, LogSnapshot, Page


def read_log_snapshot(directory: Path, *, backup_count: int) -> LogSnapshot:
    """复制并解析当前日志及配置数量的备份，返回固定快照。

    无日志时 entries 为空；损坏行计入 skipped_lines。当前仅占位。"""
    raise NotImplementedError("read_log_snapshot 尚未实现")


def query_log_snapshot(snapshot: LogSnapshot, query: LogQuery) -> Page[LogEntry]:
    """在固定快照中筛选、稳定排序并分页；当前仅占位。"""
    raise NotImplementedError("query_log_snapshot 尚未实现")
