"""课程与预约 CLI 处理器共用的可选输入和日期窗口工具。

`prompts` 提供必填输入；本模块补“留空表示不限”的筛选输入，并把门店日期
展开成 [当天 00:00, 次日 00:00) 的时区窗口。所有解析失败都会提示后重输，
不把原始文本传给服务层。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.models.contracts import DateWindow
from src.ui.cli import prompts


def zone(timezone_name: str):
    """取得门店时区；配置异常时退回 UTC。"""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return timezone.utc


def optional_text(label: str) -> str | None:
    """读取可留空文字；留空返回 None，而不是空字符串。"""
    value = prompts.prompt_text(label, allow_empty=True).strip()
    return value or None


def optional_int(label: str, *, minimum: int = 1) -> int | None:
    """读取可留空的正整数；留空返回 None，非法输入提示后重输。"""
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


def optional_bool(label: str) -> bool | None:
    """读取启用/停用筛选；留空表示不过滤。"""
    while True:
        raw = prompts.prompt_text(label, allow_empty=True).strip().lower()
        if not raw:
            return None
        if raw in {"启用", "active", "是", "y", "1"}:
            return True
        if raw in {"停用", "inactive", "否", "n", "0"}:
            return False
        print("请输入“启用”“停用”，或直接回车表示不限")


def optional_choice(label: str, choices: dict[str, str]) -> str | None:
    """读取可留空的固定选项；返回选项对应的内部值。"""
    while True:
        raw = prompts.prompt_text(label, allow_empty=True).strip()
        if not raw:
            return None
        key = raw.lower()
        if key in choices:
            return choices[key]
        print("可选值：" + "、".join(sorted(choices)) + "；也可以直接回车表示不限")


def optional_date(label: str) -> date | None:
    """读取可留空的 ISO 日期（YYYY-MM-DD）。"""
    while True:
        raw = prompts.prompt_text(label, allow_empty=True).strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            print("日期格式应为 YYYY-MM-DD，例如 2026-12-01")


def date_window(day: date, timezone_name: str) -> DateWindow:
    """把门店日期展开为 [当天 00:00, 次日 00:00) 的时区窗口。"""
    start = datetime.combine(day, time.min, tzinfo=zone(timezone_name))
    return DateWindow(start=start, end=start + timedelta(days=1))
