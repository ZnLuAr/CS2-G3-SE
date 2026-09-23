"""公共输入、确认与取消接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal


def prompt_password(label: str) -> str:
    """从终端读取不回显的原始密码；中断和文件结束由调用方处理。"""
    import getpass

    return getpass.getpass(label)


def prompt_text(label: str, *, allow_empty: bool = False) -> str:
    """读取文字；allow_empty 决定空文字是否合法。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_text 尚未实现")


def prompt_optional_text(label: str) -> str | None:
    """读取可选文字；确认留空返回 None，主动取消抛 InputCancelled。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_optional_text 尚未实现")


def prompt_int(label: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    """读取整数并检查包含边界；格式或范围不符时提示重输。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_int 尚未实现")


def prompt_decimal(label: str, *, minimum: Decimal | None = None) -> Decimal:
    """从文字读取两位小数，避免 float 中转；不符时提示重输。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_decimal 尚未实现")


def prompt_date(label: str) -> date:
    """读取 ISO 日期，返回 date；不能返回日期字符串。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_date 尚未实现")


def prompt_datetime(label: str, *, timezone_name: str) -> datetime:
    """按门店时区读取时刻，返回带时区的 UTC datetime。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_datetime 尚未实现")


def prompt_confirm(label: str) -> bool:
    """确认返回 True，明确否定返回 False；取消抛 InputCancelled。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_confirm 尚未实现")


def prompt_member_id() -> int:
    """读取有效的正整数会员编号。

    实现后用户取消抛 InputCancelled；当前不读取终端，调用抛 NotImplementedError。"""
    raise NotImplementedError("prompt_member_id 尚未实现")
