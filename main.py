"""启动参数与程序入口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from src.config import StartupOptions


def parse_args(argv: list[str] | None = None) -> StartupOptions:
    """解析命令行参数；argv=None 表示使用 sys.argv[1:]。

    支持的参数：
    - --tui：启用终端界面（可选，默认使用 CLI）
    - --config PATH：指定配置文件路径（可选）
    - --help：显示帮助信息并退出

    返回：StartupOptions

    注意：--help 应无需数据库即可显示。当前调用抛 NotImplementedError。"""
    raise NotImplementedError("parse_args 尚未实现")


def main(argv: list[str] | None = None) -> int:
    """程序入口；成功返回 0，失败返回非零状态。

    执行流程：
    1. 解析命令行参数（parse_args）
    2. 加载配置（load_config）
    3. 初始化日志系统
    4. 检查数据库连接
    5. 创建应用实例（App）
    6. 选择并启动界面：
       - 默认：CLI（ui.cli.app）
       - --tui：TUI（ui.tui.app，如果可用）
    7. 优雅关闭：
       - 正常退出：退出码 0
       - Ctrl+C / EOF：正常关闭资源，退出码 0
       - 启动失败：打印错误，退出码 1
       - 运行时错误：记录日志，根据错误类型决定退出码

    资源管理：
    - 数据库连接池在 App 中管理
    - 日志系统在程序关闭时清理
    - 异常处理确保资源释放

    退出码：
    - 0：正常退出（包括 Ctrl+C 和 EOF）
    - 1：配置错误、数据库不可达、启动失败
    - 其他：运行时严重错误

    后续负责选择 CLI 或可选 TUI、管理生命周期；当前仅保留签名。"""
    raise NotImplementedError("main 尚未实现")


if __name__ == "__main__":
    raise SystemExit(main())
