"""启动与环境配置的数据格式。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class StartupOptions:
    """启动参数；tui 为 True 时选择可选 TUI。"""

    tui: bool = False


@dataclass(frozen=True, kw_only=True)
class AppSettings:
    """部署配置；连接地址可能含密码，不参与对象的普通打印。"""

    database_url: str = field(repr=False)
    timezone_name: str = "Asia/Shanghai"
    log_directory: Path = Path("logs")
    log_level: str = "INFO"


def load_config() -> AppSettings:
    """读取环境配置并校验必需项。

    返回：AppSettings。实现后缺项或格式非法抛 InvalidInputError，不打印数据库凭据。
    当前不读取环境，也不创建目录。"""
    raise NotImplementedError("load_config 尚未实现")
