"""数据库资源和事务边界接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from src.config import AppSettings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session


def create_engine(settings: AppSettings) -> Engine:
    """按配置创建 MySQL 引擎；实现后检查 UTC 时区与严格 SQL 模式。

    当前不连接数据库；调用抛 NotImplementedError。"""
    raise NotImplementedError("create_engine 尚未实现")


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    """返回会话工厂；后续每次业务调用使用一个独立会话。

    当前不连接数据库；调用抛 NotImplementedError。"""
    raise NotImplementedError("create_session_factory 尚未实现")


def check_connection(engine: Engine) -> None:
    """只检查连通性，不建表；实现后失败抛 StorageError。

    当前不连接数据库；调用抛 NotImplementedError。"""
    raise NotImplementedError("check_connection 尚未实现")


def check_schema(engine: Engine, required_version: int) -> None:
    """核对结构版本；版本不符时拒绝普通启动，不自动改表。

    当前不连接数据库；调用抛 NotImplementedError。"""
    raise NotImplementedError("check_schema 尚未实现")


def transaction(session: Session) -> AbstractContextManager[Session]:
    """返回事务上下文；后续负责提交、失败回滚及提交结果未知的区分。

    当前不连接数据库；调用抛 NotImplementedError。"""
    raise NotImplementedError("transaction 尚未实现")


def close_engine(engine: Engine) -> None:
    """关闭引擎管理的连接资源。

    当前不连接数据库；调用抛 NotImplementedError。"""
    raise NotImplementedError("close_engine 尚未实现")
