"""本机日志查询命令接口。日志读取和交互仍为占位。"""

from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    """解析 --config 并进入日志查询；当前仅声明接口。"""
    raise NotImplementedError("src.cmd.logs.main 尚未实现")


if __name__ == "__main__":
    raise SystemExit(main())
