"""数据库维护命令。当前仅声明字段与签名，方法尚未实现。

用法：
    python -m src.cmd.db init   # 初始化数据库（建表）
    python -m src.cmd.db seed   # 生成演示数据
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

    member_password: str
    coach_password: str
    receptionist_password: str
    admin_password: str


def init_database(session: Session) -> InitResult:
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
    raise NotImplementedError("init_database 尚未实现")


def seed_demo_data(session: Session, passwords: DemoPasswordInput) -> SeedResult:
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
    raise NotImplementedError("seed_demo_data 尚未实现")


def main() -> None:
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
    raise NotImplementedError("db 命令尚未实现")


if __name__ == "__main__":
    main()
