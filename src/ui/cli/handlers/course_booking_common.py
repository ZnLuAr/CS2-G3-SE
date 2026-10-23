"""课程/预约处理器共用的可选筛选输入。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.models.contracts import DateWindow
from src.ui.cli import prompts


def zone(timezone_name: str):
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        from datetime import timezone
        return timezone.utc


def optional_int(label: str, *, minimum: int = 1) -> int | None:
    while True:
        raw = prompts.prompt_text(label, allow_empty=True).strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            print("请输入整数，或直接回车表示不限")
            continue
        if value < minimum:
            print(f"请输入不小于 {minimum} 的整数")
            continue
        return value


def optional_date(label: str) -> date | None:
    while True:
        raw = prompts.prompt_text(label, allow_empty=True).strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            print("日期格式应为 YYYY-MM-DD，例如 2026-12-01")


def optional_text(label: str) -> str | None:
    return prompts.prompt_text(label, allow_empty=True).strip() or None


def date_window(day: date, timezone_name: str) -> DateWindow:
    start = datetime.combine(day, time.min, tzinfo=zone(timezone_name))
    return DateWindow(start=start, end=start + timedelta(days=1))
