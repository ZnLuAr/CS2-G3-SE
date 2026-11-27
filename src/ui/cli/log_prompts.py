"""日志查询条件的公共交互入口，供管理员菜单和本机日志命令共用。"""

from __future__ import annotations

from src.models.contracts import DateWindow, LogQuery
from src.ui.cli import prompts

MAX_FILTER_CHARS = 64


def prompt_log_query(timezone_name: str) -> LogQuery:
    """收集时间范围、级别、操作名、操作人和请求编号。

    操作名和请求编号在输入处校验 1～64 个字符，超长时提示后重新输入，
    不在构造查询条件时才失败。
    """
    window = None
    if prompts.prompt_confirm("限定时间范围？"):
        window = DateWindow(
            start=prompts.prompt_datetime(
                "开始时刻（含，YYYY-MM-DD HH:MM）：", timezone_name=timezone_name,
            ),
            end=prompts.prompt_datetime(
                "结束时刻（不含，YYYY-MM-DD HH:MM）：", timezone_name=timezone_name,
            ),
        )
    choice = prompts.prompt_int(
        "日志级别（0 全部 / 1 INFO / 2 WARNING / 3 ERROR）：",
        minimum=0, maximum=3,
    )
    level = (None, "INFO", "WARNING", "ERROR")[choice]
    operation = _optional_filter("操作名称")
    actor_id = prompt_optional_id("操作人账号编号（留空表示全部，q 取消）：")
    request_id = _optional_filter("请求编号")
    return LogQuery(
        window=window,
        level=level,
        operation=operation,
        actor_id=actor_id,
        request_id=request_id,
    )


def prompt_optional_id(label: str) -> int | None:
    """读取可空的正整数编号；格式不正确时提示后重新输入。"""
    while True:
        raw = prompts.prompt_optional_text(label)
        if raw is None:
            return None
        if raw.isascii() and raw.isdecimal():
            try:
                value = int(raw)
            except ValueError:
                pass
            else:
                if 1 <= value <= 2**63 - 1:
                    return value
        print("请输入正整数编号，或留空表示全部。")


def _optional_filter(label: str) -> str | None:
    """读取可空筛选项，长度必须在 1～64 个字符之间。"""
    while True:
        value = prompts.prompt_text(
            f"{label}（留空表示全部，q 取消）：", allow_empty=True,
        ) or None
        if value is None or len(value) <= MAX_FILTER_CHARS:
            return value
        print(f"{label}必须是 1～{MAX_FILTER_CHARS} 个字符，请重新输入。")
