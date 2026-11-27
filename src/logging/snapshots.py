"""固定日志快照的读取与分页查询接口。"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from src.errors.business import InvalidInputError, ResourceError
from src.logging._filelock import exclusive_file_lock
from src.models.contracts import (
    AttendanceChange,
    DateWindow,
    LogEntry,
    LogFrame,
    LogQuery,
    LogSnapshot,
    Page,
    PageRequest,
)

LOCK_FILENAME = "app.log.lock"
_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_OUTCOMES = {"success", "rejected", "failed", "unknown"}


def read_log_snapshot(directory: Path, *, backup_count: int) -> LogSnapshot:
    """复制并解析当前日志及配置数量的备份，返回固定快照。

    输入：日志目录和备份数量（0～3）。
    返回：按时间倒序、同时间按文件记录顺序倒序的不可变快照；无日志时为空快照。
    异常：目录不可访问、锁不可用或文件读取失败时抛 ResourceError。
    数据变更：无。只在跨进程锁内读取并复制文本，释放锁后再解析。
    """
    captured_at = datetime.now(timezone.utc)
    if type(backup_count) is not int or not 0 <= backup_count <= 3:
        raise InvalidInputError("日志备份数量必须是 0～3 的整数")
    directory = Path(directory)
    try:
        directory.stat()
    except FileNotFoundError:
        return LogSnapshot(captured_at=captured_at, entries=(), skipped_lines=0)
    except OSError as exc:
        raise ResourceError("读取日志快照失败") from exc
    if not directory.is_dir():
        raise ResourceError("读取日志快照失败")

    contents: list[str] = []
    try:
        with exclusive_file_lock(directory / LOCK_FILENAME):
            for index in range(backup_count, 0, -1):
                path = directory / f"app.log.{index}"
                try:
                    contents.append(path.read_text(encoding="utf-8", errors="replace"))
                except FileNotFoundError:
                    continue
            current = directory / "app.log"
            try:
                contents.append(current.read_text(encoding="utf-8", errors="replace"))
            except FileNotFoundError:
                pass
    except OSError as exc:
        raise ResourceError("读取日志快照失败") from exc

    parsed: list[tuple[LogEntry, int]] = []
    skipped_lines = 0
    sequence = 0
    for text in contents:
        # 只按换行符拆行；JSON 字符串内的 U+2028/U+2029 等不是事件分隔符。
        for line in text.split("\n"):
            if line.endswith("\r"):
                line = line[:-1]
            sequence += 1
            if not line.strip():
                continue
            entry = _parse_entry(line)
            if entry is None:
                skipped_lines += 1
                continue
            parsed.append((entry, sequence))
    parsed.sort(key=lambda item: (item[0].timestamp, item[1]), reverse=True)
    return LogSnapshot(
        captured_at=captured_at,
        entries=tuple(entry for entry, _ in parsed),
        skipped_lines=skipped_lines,
    )


def query_log_snapshot(snapshot: LogSnapshot, query: LogQuery) -> Page[LogEntry]:
    """在固定快照中筛选、稳定排序并分页。

    输入：read_log_snapshot 返回的快照和筛选、分页条件。
    返回：Page[LogEntry]；条目顺序沿用快照的时间倒序。
    异常：快照或条件类型、范围非法时抛 InvalidInputError。
    数据变更：无。
    """
    if not isinstance(snapshot, LogSnapshot) or not isinstance(query, LogQuery):
        raise InvalidInputError("日志查询条件格式不正确")

    paging = query.paging
    if (
        not isinstance(paging, PageRequest)
        or type(paging.page) is not int
        or paging.page < 1
        or type(paging.page_size) is not int
        or not 1 <= paging.page_size <= 100
    ):
        raise InvalidInputError("分页条件必须是第 1 页起、每页 1～100 条")

    window = query.window
    if window is not None:
        if not isinstance(window, DateWindow) or not _aware(window.start) or not _aware(window.end):
            raise InvalidInputError("日志时间范围必须包含时区")
        if window.start >= window.end:
            raise InvalidInputError("日志时间范围的开始必须早于结束")

    level = query.level
    if level is not None and (not isinstance(level, str) or level not in _LEVELS):
        raise InvalidInputError("日志级别不正确")

    operation = query.operation
    if operation is not None and (not isinstance(operation, str) or not 1 <= len(operation) <= 64):
        raise InvalidInputError("操作名称必须是 1～64 个字符")

    actor_id = query.actor_id
    if actor_id is not None and (type(actor_id) is not int or not 1 <= actor_id <= 2**63 - 1):
        raise InvalidInputError("操作人编号必须是有效的正整数")

    request_id = query.request_id
    if request_id is not None and (not isinstance(request_id, str) or not 1 <= len(request_id) <= 64):
        raise InvalidInputError("请求编号必须是 1～64 个字符")

    def matches(entry: LogEntry) -> bool:
        if window is not None and not window.start <= entry.timestamp < window.end:
            return False
        if level is not None and entry.level != level:
            return False
        if operation is not None and entry.operation != operation:
            return False
        if actor_id is not None and entry.actor_id != actor_id:
            return False
        if request_id is not None and entry.request_id != request_id:
            return False
        return True

    items = [entry for entry in snapshot.entries if matches(entry)]
    total = len(items)
    start = (paging.page - 1) * paging.page_size
    return Page(
        items=items[start:start + paging.page_size],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _parse_entry(line: str) -> LogEntry | None:
    try:
        data = json.loads(line)
        if not isinstance(data, dict):
            return None
        timestamp = datetime.fromisoformat(data["timestamp"])
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        level = data["level"]
        operation = data["operation"]
        outcome = data["outcome"]
        if (
            not isinstance(level, str) or level not in _LEVELS
            or not isinstance(operation, str) or not 1 <= len(operation) <= 64
            or not isinstance(outcome, str) or outcome not in _OUTCOMES
        ):
            return None

        actor_id = _optional_id(data.get("actor_id"))
        request_id = data.get("request_id")
        if request_id is not None and (not isinstance(request_id, str) or not 1 <= len(request_id) <= 64):
            return None
        result_id = _optional_id(data.get("result_id"))
        error_type = data.get("error_type")
        error_message = data.get("error_message")
        if error_type is not None and not isinstance(error_type, str):
            return None
        if error_message is not None and not isinstance(error_message, str):
            return None

        raw_frames = data.get("frames", [])
        if not isinstance(raw_frames, list):
            return None
        frames: list[LogFrame] = []
        for raw in raw_frames:
            frame = _parse_frame(raw)
            if frame is None:
                return None
            frames.append(frame)

        raw_attendance = data.get("attendance_change")
        if raw_attendance is None:
            attendance = None
        else:
            attendance = _parse_attendance(raw_attendance)
            if attendance is None:
                return None

        truncated = data.get("truncated", False)
        if type(truncated) is not bool:
            return None
        return LogEntry(
            timestamp=timestamp.astimezone(timezone.utc),
            level=level,
            operation=operation,
            outcome=outcome,
            actor_id=actor_id,
            request_id=request_id,
            result_id=result_id,
            error_type=error_type,
            error_message=error_message,
            attendance_change=attendance,
            frames=tuple(frames),
            truncated=truncated,
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        # 极端年份转 UTC 可能溢出；损坏行按跳过计数，不使整个快照失败。
        return None


def _optional_id(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise ValueError("编号范围不正确")
    return value


def _parse_frame(value: object) -> LogFrame | None:
    if not isinstance(value, dict):
        return None
    filename = value.get("filename")
    line_number = value.get("line_number")
    function_name = value.get("function_name")
    if (
        not isinstance(filename, str)
        or type(line_number) is not int
        or line_number < 1
        or not isinstance(function_name, str)
    ):
        return None
    return LogFrame(
        filename=filename,
        line_number=line_number,
        function_name=function_name,
    )


def _parse_attendance(value: object) -> AttendanceChange | None:
    if not isinstance(value, dict):
        return None
    before = value.get("before")
    after = value.get("after")
    if before not in {"reserved", "checked_in"} or after not in {"reserved", "checked_in"}:
        return None
    try:
        return AttendanceChange(
            before=before,
            after=after,
            before_checked_in_at=_optional_timestamp(value.get("before_checked_in_at")),
            after_checked_in_at=_optional_timestamp(value.get("after_checked_in_at")),
            corrected_at=_optional_timestamp(value.get("corrected_at")),
        )
    except (ValueError, OverflowError):
        return None


def _optional_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("时刻不是字符串")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
