"""日志生命周期、脱敏事件和固定快照的公共入口。"""

from src.logging.events import Operation, Outcome, log_event
from src.logging.lifecycle import close_logging, configure_logging
from src.logging.snapshots import query_log_snapshot, read_log_snapshot

__all__ = [
    "Operation",
    "Outcome",
    "configure_logging",
    "log_event",
    "close_logging",
    "read_log_snapshot",
    "query_log_snapshot",
]
