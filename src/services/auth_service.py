"""账号与权限服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.config import LogConfig

from src.models.contracts import (
    AccountInput,
    AccountLinkInput,
    AccountView,
    Actor,
    LogEntry,
    LogQuery,
    LogSnapshot,
    NamedQuery,
    Page,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AuthService:
    """账号与权限服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture.md“开发前必读”的返回、异常、权限和事务约定。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(
        self, session_factory: Callable[[], Session], *, log_config: LogConfig,
    ) -> None:
        """接收会话工厂和配置解析后的日志配置。"""
        self._session_factory = session_factory
        self._log_config = log_config

    def login(self, username: str, password: str) -> Actor:
        """校验凭据并取得当前操作者。

        用户名去首尾空白并转小写，只允许 3–50 位 ASCII 字母、数字和下划线。
        密码原样处理，允许 A–Z、a–z、0–9、短横线和下划线，共 6–32 位；不做强度检测。
        member/coach 角色必须关联唯一且启用的对应档案；员工角色不得关联会员或教练档案。
        账号停用、档案不匹配、未关联或关联档案停用时抛 AuthenticationError。
        返回：Actor。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AuthService.login 尚未实现")

    def create_account(self, actor: Actor, data: AccountInput) -> AccountView:
        """创建账号。

        用户名和密码格式见 docs/architecture.md“数据边界规则”；实现时密码须哈希保存。
        返回：AccountView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AuthService.create_account 尚未实现")

    def get_account(self, actor: Actor, account_id: int) -> AccountView:
        """查询账号详情。

        返回：AccountView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AuthService.get_account 尚未实现")

    def list_accounts(self, actor: Actor, query: NamedQuery) -> Page[AccountView]:
        """分页查询账号。

        返回：Page[AccountView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AuthService.list_accounts 尚未实现")

    def set_account_active(self, actor: Actor, account_id: int, active: bool) -> AccountView:
        """停用或恢复账号。

        将操作者和目标账号统一按编号升序锁定；停用管理员时，同一次锁定当前读还要
        包含全部启用管理员。锁内复核操作者、目标状态和启用管理员数量。
        返回：AccountView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AuthService.set_account_active 尚未实现")

    def link_profile(self, actor: Actor, account_id: int, data: AccountLinkInput) -> AccountView:
        """将 data 指定的档案移交给 account_id 指定的目标账号。

        返回：目标账号的 AccountView；同一档案重复关联不变，目标占用其他档案则拒绝。
        先只读取得旧账号，再将操作者、旧账号和目标账号去重后按编号升序统一锁定，
        最后锁档案；关联变化时最多重开 3 次。
        同事务把档案外键从旧账号直接改为目标账号；失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AuthService.link_profile 尚未实现")

    def verify_actor(self, session: Session, actor: Actor) -> Actor:
        """锁定并重验账号、角色档案不变量及档案启用状态。

        先锁当前账号，再通过 lock_profile_links 锁定并读取关联会员或教练的完整记录，
        以锁内记录复核关联和 is_active；锁持有到调用方事务结束，不自行提交。
        账号停用或档案移交一旦提交，旧 Actor 的后续复核抛 AuthenticationError。"""
        raise NotImplementedError("AuthService.verify_actor 尚未实现")

    def open_log_snapshot(self, actor: Actor) -> LogSnapshot:
        """取得管理员本次日志浏览使用的固定快照。

        返回：LogSnapshot；非管理员抛 PermissionDenied，读取失败抛 ResourceError。
        当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AuthService.open_log_snapshot 尚未实现")

    def query_logs(
        self,
        actor: Actor,
        query: LogQuery,
        *,
        snapshot: LogSnapshot,
    ) -> Page[LogEntry]:
        """查询日志记录。

        权限：只有管理员可以查询日志

        参数：
        - actor: 当前操作人
        - query: LogQuery
          - window: 时间范围
          - level: 日志级别
          - operation: 操作名称
          - actor_id: 操作人编号
          - request_id: 请求编号
          - paging: 分页参数（默认每页 20 条，最多 100 条）
        - snapshot: open_log_snapshot 返回的同一次浏览快照

        返回：Page[LogEntry]

        注意：
        - 筛选和翻页沿用同一快照，刷新时重新取得快照
        - 跨进程文件锁保护
        - 只有管理员可以查询日志

        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("AuthService.query_logs 尚未实现")
