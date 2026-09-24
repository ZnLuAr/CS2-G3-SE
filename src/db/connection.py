"""数据库连接池、结构检查和事务边界。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from src.config import AppSettings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session


CURRENT_SCHEMA_VERSION = 2


def create_engine(settings: AppSettings) -> Engine:
    """按配置创建 MySQL 引擎，新连接使用 UTC、严格 SQL 模式和 REPEATABLE READ。"""
    from sqlalchemy import create_engine as sa_create_engine, event
    from sqlalchemy.engine import URL
    from src.errors.storage import StorageError

    db = settings.database

    connection_url = URL.create(
        drivername="mysql+pymysql",
        username=db.username,
        password=db.password,
        host=db.host,
        port=db.port,
        database=db.database,
        query={"charset": db.charset},
    )

    try:
        engine = sa_create_engine(
            connection_url,
            pool_size=db.pool_size,
            max_overflow=0,
            pool_timeout=5,
            pool_pre_ping=True,  # 检查连接是否存活
            isolation_level="REPEATABLE READ",
            connect_args={"connect_timeout": 5, "read_timeout": 30, "write_timeout": 30},
            echo=False,  # 不打印 SQL（避免泄露敏感数据）
        )

        @event.listens_for(engine, "connect")
        def _configure_connection(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SET time_zone = '+00:00'")
                cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE'")
            finally:
                cursor.close()

        return engine
    except Exception as exc:
        raise StorageError("无法创建数据库引擎") from exc


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    """返回会话工厂；后续每次业务调用使用一个独立会话。"""
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory


def check_connection(engine: Engine) -> None:
    """只检查连通性，不建表；失败抛 StorageError。"""
    from sqlalchemy import text
    from src.errors.storage import StorageError

    try:
        with engine.connect() as conn:
            # 执行简单查询检查连接
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise StorageError("数据库连接失败") from exc


def check_schema(engine: Engine, required_version: int) -> None:
    """核对结构版本；版本不符时拒绝普通启动，不自动改表。"""
    from sqlalchemy import text
    from src.errors.business import InvalidState
    from src.errors.storage import StorageError

    try:
        with engine.connect() as conn:
            required_tables = {
                "schema_versions", "accounts", "members", "coaches", "card_products",
                "memberships", "payments", "gym_entries", "courses", "rooms",
                "course_sessions", "bookings", "consumptions", "reviews", "equipment",
                "maintenance_records", "body_measurements", "operation_records",
            }
            result = conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_type = 'BASE TABLE'
                """
                )
            )
            actual = {row[0] for row in result.fetchall()}
            if "schema_versions" not in actual:
                raise InvalidState(
                    "数据库未初始化，请先运行：python -m src.cmd.db init"
                )
            missing = sorted(required_tables - actual)
            if missing:
                raise InvalidState(f"数据库结构不完整，缺少：{', '.join(missing)}")

            # 查询当前版本
            result = conn.execute(
                text("SELECT version FROM schema_versions ORDER BY version DESC LIMIT 1")
            )
            row = result.fetchone()
            if not row:
                raise InvalidState("数据库版本记录缺失")

            current_version = row[0]
            if current_version != required_version:
                if current_version < required_version:
                    raise InvalidState(
                        f"数据库版本过低：当前 {current_version}，需要 {required_version}；"
                        "请先运行 python -m src.cmd.db migrate"
                    )
                raise InvalidState(
                    f"数据库版本不匹配：当前 {current_version}，需要 {required_version}"
                )

    except InvalidState:
        raise
    except Exception as exc:
        raise StorageError("版本检查失败") from exc


def transaction(
    session: Session,
    *,
    request_id: str | None = None,
    record_id: int | None = None,
) -> AbstractContextManager[Session]:
    """返回事务上下文；提交未知时保留调用方提供的核实编号。"""
    from contextlib import contextmanager

    @contextmanager
    def _transaction():
        try:
            yield session
            # flush 中的约束失败表示事务确定没有提交，应保留原异常供服务映射。
            session.flush()
        except BaseException:
            try:
                session.rollback()
            except BaseException:
                pass
            raise
        try:
            session.commit()
        except BaseException as exc:
            from src.errors.storage import OutcomeUnknownError

            try:
                session.rollback()
            except BaseException:
                pass
            raise OutcomeUnknownError(
                "事务提交结果未知",
                request_id=request_id,
                record_id=record_id,
            ) from exc

    return _transaction()


def close_engine(engine: Engine) -> None:
    """释放连接池；失败抛安全 StorageError，由调用方保留主流程故障。"""
    from src.errors.storage import StorageError

    try:
        engine.dispose()
    except (EOFError, KeyboardInterrupt):
        raise
    except Exception as exc:
        raise StorageError("关闭数据库资源失败") from exc
