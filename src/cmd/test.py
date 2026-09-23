"""统一测试入口：默认单元测试，mysql/all 模式显式指定独立测试库。"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys

from src.config import AppSettings, _parse_settings, _read_config
from src.errors.base import GymError
from src.errors.business import InvalidInputError

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, kw_only=True)
class TestSettings:
    """测试库标记与经过相同校验的应用配置。"""
    test_database: bool
    app: AppSettings


def load_test_config(config_path: str) -> TestSettings:
    """只读测试 JSON；非法标记、库名或字段抛 InvalidInputError。"""
    path = Path(config_path).expanduser().resolve()
    data = _read_config(path)
    if not isinstance(data, dict) or set(data) != {"test_database", "app"} or data["test_database"] is not True:
        raise InvalidInputError("测试配置必须包含 test_database: true 和 app")
    app = _parse_settings(data["app"], path, os.environ.get("TEST_DB_PASSWORD"))
    if not app.database.database.endswith("_test"):
        raise InvalidInputError("测试数据库名称必须以 _test 结尾")
    return TestSettings(test_database=True, app=app)


def _lock_name(database: str) -> str:
    return "cs2g3:test:" + hashlib.sha256(database.encode("utf-8")).hexdigest()[:40]


def _stop_pytest(child: subprocess.Popen) -> None:
    """先让 pytest 完成 fixture 清理，超时后回收本次创建的进程树。"""
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        if child.poll() is None:
            try:
                if os.name == "nt":
                    child.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(child.pid, signal.SIGINT)
            except OSError:
                pass
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                # PID 来自本次创建的进程；同时结束 pytest 启动的 CLI 子进程。
                subprocess.run(
                    ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    check=True, timeout=10,
                )
            else:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            child.wait()
    finally:
        signal.signal(signal.SIGINT, previous)


def _run_pytest(mode: str, env: dict[str, str]) -> int:
    """等待测试进程结束；中断时先停止子进程，再交还数据库锁。"""
    command = [sys.executable, "-X", "utf8", "-m", "pytest"]
    if mode != "all":
        command += ["-m", "mysql" if mode == "mysql" else "not mysql"]
    with subprocess.Popen(
        command, cwd=ROOT, env=env,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    ) as child:
        try:
            return 0 if child.wait() == 0 else 1
        except KeyboardInterrupt:
            _stop_pytest(child)
            return 1


def main(argv: list[str] | None = None) -> int:
    """成功 0；测试/环境/中断失败 1；命令参数错误 2。"""
    parser = argparse.ArgumentParser(description="运行项目测试")
    parser.add_argument("mode", nargs="?", choices=("unit", "mysql", "all"), default="unit", help="默认 unit，无需 MySQL")
    parser.add_argument("--config", help="mysql/all 模式使用的独立测试配置")
    try:
        args = parser.parse_args(argv)
        if args.mode == "unit" and args.config is not None:
            parser.error("默认测试不使用数据库配置；请选择 mysql 或 all")
    except SystemExit as exc:
        return int(exc.code or 0)

    engine = None
    exit_code = 1
    try:
        if importlib.util.find_spec("pytest") is None:
            raise InvalidInputError("请先安装测试依赖：python -m pip install -r requirements-dev.txt")
        env = os.environ.copy()
        for key in ("DB_PASSWORD", "GYM_TEST_CONFIG", "GYM_TEST_MODE", "GYM_TEST_LOCK_OWNER"):
            env.pop(key, None)
        if args.mode == "unit":
            env.pop("TEST_DB_PASSWORD", None)
            return _run_pytest(args.mode, env)
        if args.config is None:
            raise InvalidInputError("mysql/all 模式必须通过 --config 指定测试配置")
        config_path = str(Path(args.config).expanduser().resolve())
        settings = load_test_config(config_path)
        from sqlalchemy import text
        from src.db.connection import create_engine

        engine = create_engine(settings.app)
        with engine.connect() as connection:
            lock = _lock_name(settings.app.database.database)
            acquired = False
            try:
                acquired = connection.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": lock}).scalar_one() == 1
                if not acquired:
                    raise InvalidInputError("该测试库已有测试正在运行，请稍后重试")
                env.update(GYM_TEST_CONFIG=config_path, GYM_TEST_MODE=args.mode,
                           GYM_TEST_LOCK_OWNER=str(connection.execute(text("SELECT CONNECTION_ID()")).scalar_one()))
                exit_code = _run_pytest(args.mode, env)
            finally:
                if acquired:
                    try:
                        connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock})
                    except BaseException:
                        connection.invalidate()
                        raise
    except (KeyboardInterrupt, EOFError):
        exit_code = 1
    except GymError as exc:
        print(f"测试失败：{exc}", file=sys.stderr)
        exit_code = 1
    except Exception:
        print("测试环境不可用，请检查依赖、测试配置和 MySQL 服务。", file=sys.stderr)
        exit_code = 1
    finally:
        if engine is not None:
            from src.db.connection import close_engine
            try:
                close_engine(engine)
            except (Exception, KeyboardInterrupt):
                print("关闭测试数据库资源失败", file=sys.stderr)
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
