"""本机日志查询命令。"""

from __future__ import annotations

import argparse
from dataclasses import replace

from src.config import load_config
from src.errors.base import GymError
from src.errors.business import InputCancelled
from src.logging.snapshots import query_log_snapshot, read_log_snapshot
from src.ui.cli import formatters, prompts
from src.ui.cli.log_prompts import prompt_log_query


def main(argv: list[str] | None = None) -> int:
    """按 --config 读取本机日志并进入查询交互。

    返回：正常退出 0；读取或查询失败 1；参数错误 2。
    异常：不向外抛出；EOF、Ctrl+C 和取消输入按正常退出处理。
    """
    parser = argparse.ArgumentParser(description="查询本机应用日志")
    parser.add_argument("--config", dest="config_path", required=True, help="JSON 配置文件路径")
    try:
        options = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    try:
        settings = load_config(options.config_path)
        snapshot = read_log_snapshot(
            settings.log.directory, backup_count=settings.log.backup_count,
        )
    except GymError as exc:
        print(exc.message)
        return 1
    except (OSError, ValueError):
        print("读取日志配置或日志文件失败。")
        return 1

    from src.ui.cli.menus import browse_pages

    try:
        while True:
            if snapshot.skipped_lines:
                print(f"跳过损坏日志行：{snapshot.skipped_lines} 条")
            query = prompt_log_query(settings.timezone_name)
            browse_pages(
                lambda paging: query_log_snapshot(
                    snapshot, replace(query, paging=paging),
                ),
                lambda page: formatters.format_logs(
                    page, timezone_name=settings.timezone_name,
                ),
            )
            if not prompts.prompt_confirm("重新读取日志快照并刷新？"):
                return 0
            snapshot = read_log_snapshot(
                settings.log.directory, backup_count=settings.log.backup_count,
            )
    except InputCancelled:
        return 0
    except GymError as exc:
        print(exc.message)
        return 1
    except (EOFError, KeyboardInterrupt):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
