"""启动配置的数据格式、JSON 读取和字段校验。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class StartupOptions:
    """启动参数；tui 为 True 时选择可选 TUI。"""

    tui: bool = False
    config_path: str | None = None  # 可选配置文件路径


@dataclass(frozen=True, kw_only=True)
class DatabaseConfig:
    """数据库配置；密码不参与对象的普通打印，字符集固定使用 utf8mb4。"""

    host: str
    port: int
    database: str
    username: str
    password: str = field(repr=False)
    charset: str = "utf8mb4"
    pool_size: int = 5


@dataclass(frozen=True, kw_only=True)
class LogConfig:
    """日志配置。"""

    directory: Path = Path("logs")
    level: str = "INFO"
    max_bytes: int = 5 * 1024 * 1024  # 5 MiB
    backup_count: int = 3  # 当前文件 + 3 份备份，共 4 份


@dataclass(frozen=True, kw_only=True)
class AppSettings:
    """应用配置；包含数据库、时区和日志配置。"""

    database: DatabaseConfig
    timezone_name: str = "Asia/Shanghai"
    log: LogConfig = field(default_factory=LogConfig)


def _reject_unknown(mapping: dict[str, object], allowed: set[str], prefix: str) -> None:
    """拒绝配置中的拼写错误或未设计字段。"""
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ValueError(f"{prefix} 包含未知字段：{', '.join(unknown)}")


def _required_text(value: object, name: str) -> str:
    """读取去首尾空白后不能为空的文本配置。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} 必须是非空字符串")
    return value.strip()


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    """读取范围内整数；布尔值不作为整数接受。"""
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} 必须是 {minimum}-{maximum} 的整数")
    return value


def _parse_database(data: object, env_password: str | None) -> DatabaseConfig:
    """解析数据库配置；环境变量存在时覆盖文件密码，包括空字符串。"""
    if not isinstance(data, dict):
        raise ValueError("缺少 database 配置")
    _reject_unknown(
        data,
        {"host", "port", "database", "username", "password", "charset", "pool_size"},
        "database",
    )
    password = data.get("password")
    if not isinstance(password, str):
        raise ValueError("database.password 必须是字符串")
    if env_password is not None:
        password = env_password
    charset = data.get("charset", "utf8mb4")
    if charset != "utf8mb4":
        raise ValueError("database.charset 必须是 utf8mb4")
    return DatabaseConfig(
        host=_required_text(data.get("host"), "database.host"),
        port=_integer(data.get("port"), "database.port", 1, 65535),
        database=_required_text(data.get("database"), "database.database"),
        username=_required_text(data.get("username"), "database.username"),
        password=password,
        charset=charset,
        pool_size=_integer(data.get("pool_size", 5), "database.pool_size", 1, 20),
    )


def _parse_log(data: object, config_path: Path) -> LogConfig:
    """解析日志配置，并将相对目录固定到配置文件目录下。"""
    if not isinstance(data, dict):
        raise ValueError("log 配置必须是对象")
    _reject_unknown(data, {"directory", "level", "max_bytes", "backup_count"}, "log")
    directory_value = data.get("directory", "logs")
    if not isinstance(directory_value, str) or not directory_value.strip():
        raise ValueError("log.directory 必须是非空字符串")
    directory = Path(directory_value)
    if not directory.is_absolute():
        directory = (config_path.parent / directory).resolve()
    level = data.get("level", "INFO")
    if not isinstance(level, str) or level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("log.level 不是有效级别")
    max_bytes = _integer(
        data.get("max_bytes", 5 * 1024 * 1024),
        "log.max_bytes",
        1,
        5 * 1024 * 1024,
    )
    backup_count = _integer(data.get("backup_count", 3), "log.backup_count", 0, 3)
    if (backup_count + 1) * max_bytes > 20 * 1024 * 1024:
        raise ValueError("日志总容量不能超过 20 MiB")
    return LogConfig(
        directory=directory,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


def _read_config(path: Path) -> object:
    """读取 UTF-8 JSON；只在安全提示中展示路径和行号。"""
    import json
    from src.errors.business import InvalidInputError

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvalidInputError(f"找不到配置文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"配置文件格式错误：第 {exc.lineno} 行") from exc
    except UnicodeError as exc:
        raise InvalidInputError("配置文件必须使用 UTF-8 编码") from exc
    except OSError as exc:
        raise InvalidInputError(f"无法读取配置文件：{path}") from exc


def _parse_settings(data: object, path: Path, password: str | None) -> AppSettings:
    """应用与测试共用字段校验，环境变量由各自入口选择。"""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    from src.errors.business import InvalidInputError

    try:
        if not isinstance(data, dict):
            raise ValueError("配置文件根节点必须是对象")
        _reject_unknown(data, {"database", "timezone_name", "log"}, "配置文件")
        database = _parse_database(data.get("database"), password)
        timezone_name = _required_text(data.get("timezone_name", "Asia/Shanghai"), "timezone_name")
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone_name 不是有效时区") from exc
        log = _parse_log(data.get("log", {}), path)
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    return AppSettings(database=database, timezone_name=timezone_name, log=log)


def load_config(config_path: str | None = None) -> AppSettings:
    """读取当前目录 config.json 或指定文件；DB_PASSWORD 存在即覆盖文件密码。

    返回固定 AppSettings；缺项或非法配置抛 InvalidInputError。
    相对日志目录以配置文件目录为基准。读取配置不会创建资源。
    """
    import os

    path = Path(config_path).expanduser() if config_path is not None else Path("config.json")
    return _parse_settings(_read_config(path), path, os.environ.get("DB_PASSWORD"))
