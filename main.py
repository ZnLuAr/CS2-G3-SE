"""启动参数与程序入口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from src.config import StartupOptions


def parse_args(argv: list[str] | None = None) -> StartupOptions:
    """解析参数；argv=None 表示使用进程参数。

    返回 StartupOptions；后续 --help 应无需数据库即可显示。当前调用抛 NotImplementedError。"""
    raise NotImplementedError("parse_args 尚未实现")


def main(argv: list[str] | None = None) -> int:
    """程序入口；成功返回 0，失败返回非零状态。

    后续负责选择 CLI 或可选 TUI、管理生命周期；当前仅保留签名。"""
    raise NotImplementedError("main 尚未实现")


if __name__ == "__main__":
    raise SystemExit(main())
