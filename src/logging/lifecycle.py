"""日志配置和资源关闭接口。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from src.errors.business import ResourceError
from src.logging._filelock import exclusive_file_lock

if TYPE_CHECKING:
    from src.config import AppSettings

LOGGER_NAME = "gym.app"
LOG_FILENAME = "app.log"
LOCK_FILENAME = "app.log.lock"
LINE_TERMINATOR = "\n"

_logger: logging.Logger | None = None


class _LockedRotatingFileHandler(logging.Handler):
    """在跨进程锁内追加并轮转日志文件。

    不为日志文件长期保留打开句柄：每次写入在锁内打开、写入、关闭。
    这样其他进程轮转后不会继续写旧 inode，Windows 上也不会因另一个进程
    长期持有 app.log 而阻塞重命名。写入或轮转失败向调用方抛出，由
    log_event 转换为返回 False。
    """

    def __init__(
        self,
        filename: Path,
        *,
        lock_path: Path,
        max_bytes: int,
        backup_count: int,
    ) -> None:
        super().__init__()
        self.baseFilename = str(filename)
        self._filename = Path(filename)
        self._lock_path = lock_path
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self.terminator = LINE_TERMINATOR
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        line = self.format(record) + self.terminator
        with exclusive_file_lock(self._lock_path):
            self._rotate_if_needed(len(line.encode("utf-8")))
            with self._filename.open("a", encoding="utf-8", newline="") as stream:
                stream.write(line)
                stream.flush()

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        """当前文件加上本条日志将超过上限时轮转或截断。"""
        try:
            current_size = self._filename.stat().st_size
        except FileNotFoundError:
            return
        if current_size == 0 or current_size + incoming_bytes <= self._max_bytes:
            return
        if self._backup_count <= 0:
            # 只保留当前文件时直接截断，避免关闭备份后仍无限增长。
            with self._filename.open("w", encoding="utf-8", newline=""):
                pass
            return
        oldest = Path(f"{self.baseFilename}.{self._backup_count}")
        if oldest.exists():
            oldest.unlink()
        for index in range(self._backup_count - 1, 0, -1):
            source = Path(f"{self.baseFilename}.{index}")
            if source.exists():
                os.replace(source, f"{self.baseFilename}.{index + 1}")
        os.replace(self._filename, f"{self.baseFilename}.1")


def configure_logging(settings: AppSettings) -> None:
    """创建日志目录和轮转处理器。

    输入：已校验的应用配置，使用其中的日志目录、级别、单文件上限和备份数量。
    返回：无。日志写入全局日志器，调用方不需要保存处理器。
    异常：目录、文件或处理器无法创建时抛 ResourceError，使启动流程停止。
    数据变更：创建日志目录和日志文件，不修改业务数据。
    """
    global _logger
    directory = Path(settings.log.directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        log_file = directory / LOG_FILENAME
        log_file.touch(exist_ok=True)
        handler = _LockedRotatingFileHandler(
            log_file,
            lock_path=directory / LOCK_FILENAME,
            max_bytes=settings.log.max_bytes,
            backup_count=settings.log.backup_count,
        )
    except (OSError, ValueError) as exc:
        raise ResourceError("初始化日志系统失败") from exc

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(settings.log.level)
    logger.propagate = False
    for existing in list(logger.handlers):
        logger.removeHandler(existing)
        try:
            existing.close()
        except Exception:
            pass
    logger.addHandler(handler)
    _logger = logger


def get_logger() -> logging.Logger | None:
    """返回已配置的项目日志器；尚未配置时返回 None。"""
    return _logger


def close_logging() -> None:
    """刷新并关闭日志文件句柄，允许重复调用。

    异常：不向外抛出。关闭失败时向标准错误输出固定安全提示。
    """
    global _logger
    logger = _logger
    _logger = None
    if logger is None:
        return
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            try:
                print("关闭日志文件失败，程序继续退出。", file=sys.stderr)
            except (OSError, ValueError):
                pass
