"""启动与环境配置的数据格式。当前仅声明字段与签名，方法尚未实现。"""

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
    """数据库配置；密码不参与对象的普通打印。"""

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


def load_config(config_path: str | None = None) -> AppSettings:
    """读取配置文件并校验必需项。

    优先级：
    1. 从 config_path 指定的 JSON 文件读取（如果提供）
    2. 从 config.json 读取（当前目录）
    3. 敏感字段（如 password）支持从环境变量覆盖：DB_PASSWORD

    JSON 格式参考 config.example.json。

    返回：AppSettings。
    实现后缺项或格式非法抛 InvalidInputError，不打印数据库凭据。
    当前不读取配置，也不创建目录。
    """
    raise NotImplementedError("load_config 尚未实现")
