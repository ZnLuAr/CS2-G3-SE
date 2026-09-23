"""启动参数与程序入口。默认启动 CLI，TUI 作为可选模式提示。"""

from __future__ import annotations

from src.config import StartupOptions


def parse_args(argv: list[str] | None = None) -> StartupOptions:
    """解析命令行参数；argv=None 表示使用 sys.argv[1:]。

    支持的参数：
    - --tui：启用终端界面（可选，默认使用 CLI）
    - --config PATH：指定配置文件路径（可选）
    - --help：显示帮助信息并退出

    返回：StartupOptions

    注意：--help 无需配置文件或数据库即可显示。"""
    import argparse

    parser = argparse.ArgumentParser(description="健身房管理系统")
    parser.add_argument("--tui", action="store_true", help="使用可选的终端界面")
    parser.add_argument("--config", dest="config_path", help="JSON 配置文件路径")
    options = parser.parse_args(argv)
    return StartupOptions(tui=options.tui, config_path=options.config_path)




def main(argv: list[str] | None = None) -> int:
    """程序入口；成功返回 0，失败返回非零状态。

    执行流程：
    1. 解析命令行参数（parse_args）
    2. 加载配置（load_config）
    3. 创建应用实例（App）并检查数据库连接和结构
    4. 选择并启动界面：
       - 默认：CLI（ui.cli.app）
       - --tui：TUI（ui.tui.app，如果可用）
    5. 优雅关闭：
       - 正常退出：退出码 0
       - Ctrl+C / EOF：正常关闭资源，退出码 0
       - 启动失败：打印错误，退出码 1
       - 运行时错误：输出安全提示并返回 1

    资源管理：
    - 数据库连接池在 App 中管理
    - 应用创建的数据库资源在程序关闭时清理
    - 异常处理确保资源释放

    退出码：
    - 0：正常退出（包括 Ctrl+C 和 EOF）
    - 1：配置、启动、运行或资源关闭失败
    - 2：参数错误

    本函数负责选择模式、管理生命周期并转换进程退出码。"""
    import sys
    from src.app import App
    from src.errors.base import GymError

    try:
        options = parse_args(argv)
    except SystemExit as exc:
        # parse_args 的公开契约保留 argparse 的 SystemExit；这里转成返回码，
        # 方便测试和模块入口统一使用 raise SystemExit(main())。
        return int(exc.code or 0)

    app = None
    exit_code = 1
    try:
        if options.tui:
            print("TUI 尚未就绪，请使用默认 CLI 启动。", file=sys.stderr)
            return 1
        from src.config import load_config

        settings = load_config(options.config_path)
        app = App(settings)
        app.start()
        exit_code = app.run(tui=options.tui)
    except (EOFError, KeyboardInterrupt):
        exit_code = 0
    except GymError as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
    except NotImplementedError:
        print("当前操作依赖的功能尚未实现，请等待对应模块接入。", file=sys.stderr)
    except Exception:
        # 不把连接串、密码或底层堆栈输出到终端。
        print("程序运行失败，请联系维护人员检查。", file=sys.stderr)
    finally:
        if app is not None:
            try:
                app.close()
            except (Exception, KeyboardInterrupt):
                print("关闭应用资源失败，请检查后再启动。", file=sys.stderr)
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
