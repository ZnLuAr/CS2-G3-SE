"""公共终端输入；普通表单用 q/Q 取消，EOF/Ctrl+C 交给程序入口。"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import getpass
import re
import warnings
from zoneinfo import ZoneInfo

from src.errors.business import InputCancelled, ResourceError


def prompt_password(label: str) -> str:
    """无回显读取原始密码；无法隐藏输入时抛 ResourceError。"""
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(label)
        except getpass.GetPassWarning as exc:
            raise ResourceError("终端无法隐藏密码输入，请在交互式终端运行") from exc


def prompt_text(label: str, *, allow_empty: bool = False) -> str:
    """去首尾空白；空值不合法时重输，q/Q 抛 InputCancelled。"""
    while True:
        value = input(label).strip()
        if value.lower() == "q":
            raise InputCancelled()
        if value or allow_empty:
            return value
        print("此项不能为空；输入 q 取消。")


def prompt_optional_text(label: str) -> str | None:
    """确认留空返回 None。"""
    return prompt_text(label, allow_empty=True) or None


def prompt_int(label: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    """读取十进制整数，包含上下界。"""
    while True:
        raw = prompt_text(label)
        if re.fullmatch(r"[+-]?[0-9]+", raw):
            try:
                value = int(raw)
            except ValueError:
                pass
            else:
                if (minimum is None or value >= minimum) and (maximum is None or value <= maximum):
                    return value
        limits = f"（最小 {minimum}）" if minimum is not None else ""
        limits += f"（最大 {maximum}）" if maximum is not None else ""
        print(f"请输入有效整数{limits}。")


def prompt_decimal(label: str, *, minimum: Decimal | None = None) -> Decimal:
    """直接从字符串读取有限十进制数，最多两位小数。"""
    while True:
        raw = prompt_text(label)
        if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]{1,2})?", raw):
            value = Decimal(raw)
            if value.is_finite() and (minimum is None or value >= minimum):
                return value
        limit = f"，且不小于 {minimum}" if minimum is not None else ""
        print(f"请输入最多两位小数的十进制数{limit}。")


def prompt_date(label: str) -> date:
    """读取严格 YYYY-MM-DD 格式的有效日期。"""
    while True:
        raw = prompt_text(label)
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw):
            try:
                return date.fromisoformat(raw)
            except ValueError:
                pass
        print("请输入有效日期，格式为 YYYY-MM-DD。")


def prompt_datetime(label: str, *, timezone_name: str) -> datetime:
    """读取门店时刻并转 UTC；夏令时跳过或重复的本地时刻重输。"""
    zone = ZoneInfo(timezone_name)
    while True:
        raw = prompt_text(label)
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}", raw):
            try:
                local = datetime.strptime(raw, "%Y-%m-%d %H:%M")
                candidates = set()
                for fold in (0, 1):
                    utc = local.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
                    if utc.astimezone(zone).replace(tzinfo=None) == local:
                        candidates.add(utc)
                if len(candidates) == 1:
                    return candidates.pop()
            except (ValueError, OverflowError):
                pass
        print("请输入唯一有效的本地时刻，格式为 YYYY-MM-DD HH:MM。")


def prompt_confirm(label: str) -> bool:
    """y 确认、n 否定；q/Q 取消。"""
    while True:
        value = prompt_text(f"{label} [y/n，q 取消] ").lower()
        if value in {"y", "n"}:
            return value == "y"
        print("请输入 y 或 n。")


def prompt_member_id() -> int:
    """读取正整数会员编号。"""
    return prompt_int("会员编号（q 取消）：", minimum=1)
