"""数据库初始化和演示数据维护命令。

用法：
    python -m src.cmd.db init   # 初始化数据库（建表）
    python -m src.cmd.db seed   # 生成演示数据
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.orm import Session


@dataclass(frozen=True, kw_only=True)
class InitResult:
    """数据库初始化结果。"""

    tables_created: int  # 创建的表数量
    schema_version: int  # 记录的版本号


@dataclass(frozen=True, kw_only=True)
class SeedResult:
    """演示数据生成结果。"""

    accounts_created: int  # 创建的账号数（4 个）
    members_created: int  # 创建的会员档案数（1 个）
    coaches_created: int  # 创建的教练档案数（1 个）


@dataclass(frozen=True, kw_only=True)
class DemoPasswordInput:
    """演示数据的四个账号密码（明文）。"""

    member_password: str = field(repr=False)
    coach_password: str = field(repr=False)
    receptionist_password: str = field(repr=False)
    admin_password: str = field(repr=False)


def init_database(connection: Connection) -> InitResult:
    """初始化数据库（建表）。

    检查：
    - 数据库连接可用
    - 目标为空库（无业务表）

    执行：
    - 逐表创建（按依赖顺序）
    - 记录版本号到 schema_versions

    失败处理：
    - MySQL 建表会隐式提交，不能回滚
    - 失败时报告已完成步骤，不删除已有数据

    返回：InitResult

    可能的错误：
    - 数据库不为空 → InvalidState
    - 建表失败 → StorageError

    注意：不使用 DROP TABLE IF EXISTS
    """
    import hashlib
    import re
    from pathlib import Path
    from sqlalchemy import text
    from src.errors.business import InvalidState
    from src.errors.storage import InitializationError, StorageError

    schema_path = Path(__file__).resolve().parents[2] / "sql" / "001_initial_schema.sql"
    try:
        schema_text = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StorageError("找不到数据库初始化脚本") from exc
    schema_text = "\n".join(
        line for line in schema_text.splitlines()
        if not line.lstrip().startswith("--")
    )
    schema_statements = [
        statement.strip()
        for statement in re.split(r";\s*(?:\r?\n|$)", schema_text)
        if statement.strip()
    ]
    if not schema_statements:
        raise StorageError("数据库初始化脚本为空")
    expected_tables = (
        "schema_versions", "accounts", "members", "coaches", "card_products", "memberships",
        "payments", "gym_entries", "courses", "rooms", "course_sessions", "bookings",
        "consumptions", "reviews", "equipment", "maintenance_records", "body_measurements",
        "operation_records",
    )
    table_steps: list[tuple[str, str]] = []
    for statement in schema_statements:
        match = re.match(r"CREATE TABLE\s+(\w+)", statement, re.IGNORECASE)
        if match is None:
            raise StorageError("数据库初始化脚本包含不支持的语句")
        table_steps.append((match.group(1), statement))
    if tuple(name for name, _ in table_steps) != expected_tables:
        raise StorageError("数据库初始化脚本的表名、顺序或数量不符合版本 1 设计")
    lock_name = "cs2g3:init:" + hashlib.sha256(
        str(connection.engine.url.database).encode("utf-8")
    ).hexdigest()[:40]
    tables_created = 0
    completed_tables: list[str] = []
    lock_acquired = False
    current_step: str | None = None

    try:
        lock_row = connection.execute(
            text("SELECT GET_LOCK(:lock_name, 0)"), {"lock_name": lock_name}
        ).scalar_one()
        if lock_row != 1:
            raise InvalidState("已有另一个初始化操作正在进行，请稍后重试")
        lock_acquired = True

        # 检查数据库是否为空，包括表和视图。
        result = connection.execute(
            text(
                """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_type IN ('BASE TABLE', 'VIEW')
            """
            )
        )
        row = result.fetchone()
        if row and row[0] > 0:
            raise InvalidState("数据库不为空，请使用全新数据库")

        # 逐表创建
        for table_name, sql in table_steps:
            current_step = table_name
            connection.execute(text(sql))
            tables_created += 1
            completed_tables.append(table_name)
            current_step = None

        # 记录版本号
        current_step = "schema_versions.version"
        connection.execute(text("INSERT INTO schema_versions (version) VALUES (1)"))
        try:
            connection.commit()
        except BaseException as exc:
            raise InitializationError(
                "版本记录提交结果未知，请核实 schema_versions",
                completed_tables=tuple(completed_tables),
                failed_step="schema_versions.version",
                outcome_unknown=True,
            ) from exc
        current_step = None

        return InitResult(tables_created=tables_created, schema_version=1)

    except InvalidState:
        raise
    except InitializationError:
        raise
    except KeyboardInterrupt as exc:
        if current_step is None and not completed_tables:
            raise
        raise InitializationError(
            "初始化被中断，部分结构可能已经存在",
            completed_tables=tuple(completed_tables),
            failed_step=current_step or "schema_versions.version",
            outcome_unknown=True,
        ) from exc
    except Exception as e:
        raise InitializationError(
            f"建表失败（已确认完成 {len(completed_tables)} 张表）",
            completed_tables=tuple(completed_tables),
            failed_step=current_step or (
                table_steps[len(completed_tables)][0]
                if len(completed_tables) < len(table_steps)
                else "schema_versions.version"
            ),
            outcome_unknown=bool(getattr(e, "connection_invalidated", False)),
        ) from e
    finally:
        if lock_acquired:
            try:
                connection.execute(text("SELECT RELEASE_LOCK(:lock_name)"), {"lock_name": lock_name})
            except BaseException:
                # 专用连接即将关闭；使连接失效，避免物理连接回池后继续持有命名锁。
                try:
                    connection.invalidate()
                except BaseException:
                    pass


def seed_demo_data(
    session: Session,
    passwords: DemoPasswordInput,
    *,
    seed: int | None = None,
) -> SeedResult:
    """生成演示数据。

    生成：
    - 4 个账号：会员、教练、前台、管理员
    - 2 个档案：会员档案、教练档案
    - 共 6 条记录

    密码：
    - 使用提供的明文密码
    - 每个账号生成独立的随机盐
    - 存储哈希后的密码

    会员信息：
    - 电话：1 开头的 11 位随机数字
    - 可通过随机种子复现

    幂等性：
    - 检查是否已有演示数据
    - 已存在 → 拒绝并返回错误
    - 保持数据不变

    返回：SeedResult

    可能的错误：
    - 数据库未初始化 → InvalidState
    - 演示数据已存在 → ConflictError

    注意：不删除已有数据，不覆盖
    """
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    import random
    from src.errors.base import GymError
    from src.errors.business import InvalidState, ConflictError, InvalidInputError
    from src.errors.storage import StorageError
    from src.utils.passwords import hash_password

    try:
        password_values = (
            passwords.member_password, passwords.coach_password,
            passwords.receptionist_password, passwords.admin_password,
        )
        if any(not isinstance(password, str) for password in password_values):
            raise InvalidInputError("演示账号密码必须是字符串")
        # 检查数据库是否已初始化
        result = session.execute(
            text(
                """
            SELECT COUNT(*) as cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = 'accounts'
            """
            )
        )
        row = result.fetchone()
        if not row or row[0] == 0:
            raise InvalidState("数据库未初始化，请先运行：python -m src.cmd.db init")

        # 检查是否已有演示数据
        result = session.execute(
            text(
                """SELECT COUNT(*) FROM accounts
                WHERE username IN (:member, :coach, :receptionist, :admin)"""
            ),
            {
                "member": "demo_member", "coach": "demo_coach",
                "receptionist": "demo_receptionist", "admin": "demo_admin",
            },
        )
        row = result.fetchone()
        if row and row[0] > 0:
            raise ConflictError("演示数据已存在，无需重复生成")

        # 创建 4 个账号
        accounts_data = [
            ("demo_member", passwords.member_password, "member"),
            ("demo_coach", passwords.coach_password, "coach"),
            ("demo_receptionist", passwords.receptionist_password, "receptionist"),
            ("demo_admin", passwords.admin_password, "admin"),
        ]

        account_ids = {}
        for username, password, role in accounts_data:
            password_hash = hash_password(password)
            result = session.execute(
                text(
                    """
                INSERT INTO accounts (username, password_hash, role, is_active)
                VALUES (:username, :password_hash, :role, TRUE)
                """
                ),
                {"username": username, "password_hash": password_hash, "role": role},
            )
            account_ids[role] = result.lastrowid

        # 生成会员档案
        random_source = random.Random(seed)
        member_phone = "1" + "".join(str(random_source.randrange(10)) for _ in range(10))

        session.execute(
            text(
                """
            INSERT INTO members (account_id, name, phone, is_active)
            VALUES (:account_id, :name, :phone, TRUE)
            """
            ),
            {
                "account_id": account_ids["member"],
                "name": "演示会员",
                "phone": member_phone,
            },
        )

        # 生成教练档案
        session.execute(
            text(
                """
            INSERT INTO coaches (account_id, name, specialty, is_active)
            VALUES (:account_id, :name, :specialty, TRUE)
            """
            ),
            {
                "account_id": account_ids["coach"],
                "name": "演示教练",
                "specialty": "力量训练、体能提升",
            },
        )

        return SeedResult(accounts_created=4, members_created=1, coaches_created=1)

    except IntegrityError as exc:
        original = getattr(exc, "orig", None)
        details = getattr(original, "args", ())
        if (details and details[0] == 1062) or "duplicate" in str(original).lower():
            raise ConflictError("演示数据与已有记录冲突") from exc
        raise StorageError("生成演示数据失败") from exc
    except GymError:
        raise
    except Exception as e:
        raise StorageError("生成演示数据失败") from e


def main(argv: list[str] | None = None) -> int:
    """命令行入口。

    解析命令：
    - init：初始化数据库
    - seed：生成演示数据

    失败处理：
    - 打印错误信息到 stderr
    - 退出码 1

    成功：
    - 打印结果到 stdout
    - 退出码 0
    """
    import argparse
    import sys
    from src.config import load_config
    from src.db.connection import (
        close_engine,
        check_connection,
        check_schema,
        create_engine,
        create_session_factory,
        transaction,
    )
    from src.errors.base import GymError
    from src.errors.storage import InitializationError, StorageError
    from src.ui.cli.prompts import prompt_password

    parser = argparse.ArgumentParser(description="数据库初始化和演示数据命令")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="初始化空数据库")
    init_parser.add_argument("--config", dest="config_path", help="配置文件路径")
    seed_parser = subparsers.add_parser("seed", help="生成演示数据")
    seed_parser.add_argument("--config", dest="config_path", help="配置文件路径")
    seed_parser.add_argument("--seed", type=int, help="电话随机种子")
    try:
        options = parser.parse_args(argv)
    except SystemExit as exc:
        # 让公开的 main(argv) 也返回约定的状态码；模块入口再转换为进程退出。
        return int(exc.code or 0)

    engine = None
    exit_code = 1
    try:
        settings = load_config(options.config_path)
        engine = create_engine(settings)

        if options.command == "init":
            check_connection(engine)
            print("正在初始化数据库...")
            with engine.connect() as conn:
                result = init_database(conn)
            print(f"✓ 成功创建 {result.tables_created} 张表")
            print(f"✓ 数据库版本：{result.schema_version}")
            exit_code = 0

        elif options.command == "seed":
            check_schema(engine, required_version=1)
            print("正在生成演示数据...")
            passwords: dict[str, str] = {}
            for role, label in [
                ("member", "会员"),
                ("coach", "教练"),
                ("receptionist", "前台"),
                ("admin", "管理员"),
            ]:
                while True:
                    pwd1 = prompt_password(f"请输入 {label} 账号密码：")
                    pwd2 = prompt_password(f"请再次输入 {label} 账号密码：")
                    if pwd1 == pwd2:
                        passwords[f"{role}_password"] = pwd1
                        break
                    print("两次输入不一致，请重新输入", file=sys.stderr)

            demo_passwords = DemoPasswordInput(**passwords)
            session_factory = create_session_factory(engine)
            with session_factory() as session:
                with transaction(session):
                    result = seed_demo_data(
                        session, demo_passwords, seed=options.seed
                    )

            print(f"✓ 成功创建 {result.accounts_created} 个账号")
            print(f"✓ 成功创建 {result.members_created} 个会员档案")
            print(f"✓ 成功创建 {result.coaches_created} 个教练档案")
            print("演示账号：")
            print("  - demo_member       (会员)")
            print("  - demo_coach        (教练)")
            print("  - demo_receptionist (前台)")
            print("  - demo_admin        (管理员)")
            exit_code = 0
    except (KeyboardInterrupt, EOFError):
        print("\n操作已取消", file=sys.stderr)
        exit_code = 0
    except GymError as exc:
        if isinstance(exc, InitializationError):
            completed = "、".join(exc.completed_tables) or "无"
            print(
                f"初始化失败：{exc.message}；已确认完成：{completed}；"
                f"失败步骤：{exc.failed_step}；结果未知：{'是' if exc.outcome_unknown else '否'}",
                file=sys.stderr,
            )
        else:
            label = "数据库错误" if isinstance(exc, StorageError) else "操作失败"
            print(f"{label}：{exc}", file=sys.stderr)
    except Exception:
        print("未知错误，请查看日志", file=sys.stderr)
    finally:
        if engine is not None:
            try:
                close_engine(engine)
            except (Exception, KeyboardInterrupt):
                print("关闭数据库资源失败", file=sys.stderr)
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
