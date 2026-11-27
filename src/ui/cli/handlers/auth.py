"""账号、权限与日志的 CLI 交互。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from src.logic.auth_logic import AuthLogic
from src.models.contracts import (
    AccountInput,
    Actor,
    CoachAccountLinkInput,
    MemberAccountLinkInput,
    NamedQuery,
    Role,
)
from src.ui.cli import formatters, prompts
from src.ui.cli.log_prompts import prompt_log_query

_ROLES: tuple[Role, ...] = ("member", "coach", "receptionist", "admin")


class AuthHandler:
    """收集输入、确认操作、调用业务用例并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    """

    def __init__(
        self,
        logic: AuthLogic,
        get_actor: Callable[[], Actor],
        set_actor: Callable[[Actor], None],
        logout: Callable[[], None],
        *, timezone_name: str,
    ) -> None:
        self._logic = logic
        self._get_actor = get_actor
        self._set_actor = set_actor
        self._logout = logout
        self._timezone_name = timezone_name

    def login(self) -> None:
        """读取用户名和密码，登录成功后保存可信身份。"""
        username = prompts.prompt_text("用户名（q 取消）：")
        password = prompts.prompt_password("密码：")
        actor = self._logic.login(username, password)
        self._set_actor(actor)
        print("登录成功：" + formatters.format_actor(
            actor, timezone_name=self._timezone_name,
        ))

    def logout(self) -> None:
        """清除当前登录身份与私有界面状态。"""
        actor = self._get_actor()
        self._logout()
        print(f"已退出账号 {actor.account_id}。")

    def create_account(self) -> None:
        """管理员创建启用账号；密码输入不回显。"""
        actor = self._get_actor()
        username = prompts.prompt_text("用户名（3-50 位字母、数字或下划线，q 取消）：")
        password = prompts.prompt_password("密码（6-32 位字母、数字、下划线或短横线）：")
        role = self._choose_role()
        if not prompts.prompt_confirm("确认创建账号？"):
            return
        view = self._logic.create_account(
            actor, AccountInput(username=username, password=password, role=role),
        )
        print(formatters.format_account(view, timezone_name=self._timezone_name))

    def get_account(self) -> None:
        """按账号编号查看详情。"""
        actor = self._get_actor()
        account_id = prompts.prompt_int("账号编号（q 取消）：", minimum=1)
        view = self._logic.get_account(actor, account_id)
        print(formatters.format_account(view, timezone_name=self._timezone_name))

    def list_accounts(self) -> None:
        """按用户名关键字和启用状态分页浏览。"""
        actor = self._get_actor()
        keyword = prompts.prompt_text(
            "用户名关键字（留空表示全部，q 取消）：", allow_empty=True,
        )
        state = prompts.prompt_int(
            "启用状态（0 全部 / 1 启用 / 2 停用）：", minimum=0, maximum=2,
        )
        query = NamedQuery(
            keyword=keyword,
            is_active=None if state == 0 else state == 1,
        )
        from src.ui.cli.menus import browse_pages

        browse_pages(
            lambda paging: self._logic.list_accounts(
                actor, replace(query, paging=paging),
            ),
            lambda page: formatters.format_accounts(
                page, timezone_name=self._timezone_name,
            ),
        )

    def deactivate_account(self) -> None:
        """按账号编号停用账号。"""
        self._set_account_active(False)

    def activate_account(self) -> None:
        """按账号编号恢复账号。"""
        self._set_account_active(True)

    def _set_account_active(self, active: bool) -> None:
        """收集目标账号并确认后提交停用或恢复。"""
        actor = self._get_actor()
        account_id = prompts.prompt_int("账号编号（q 取消）：", minimum=1)
        action = "恢复" if active else "停用"
        if not prompts.prompt_confirm(f"确认{action}该账号？"):
            return
        view = self._logic.set_account_active(actor, account_id, active)
        print(formatters.format_account(view, timezone_name=self._timezone_name))

    def link_profile(self) -> None:
        """为会员或教练账号首次关联档案。"""
        actor = self._get_actor()
        account_id = prompts.prompt_int("账号编号（q 取消）：", minimum=1)
        kind = prompts.prompt_int("档案类型（1 会员 / 2 教练）：", minimum=1, maximum=2)
        if kind == 1:
            member_id = prompts.prompt_int("会员编号（q 取消）：", minimum=1)
            if not prompts.prompt_confirm("确认关联该会员档案？"):
                return
            view = self._logic.link_member(
                actor, MemberAccountLinkInput(account_id=account_id, member_id=member_id),
            )
        else:
            coach_id = prompts.prompt_int("教练编号（q 取消）：", minimum=1)
            if not prompts.prompt_confirm("确认关联该教练档案？"):
                return
            view = self._logic.link_coach(
                actor, CoachAccountLinkInput(account_id=account_id, coach_id=coach_id),
            )
        print(formatters.format_account(view, timezone_name=self._timezone_name))

    def relink_profile(self) -> None:
        """为会员或教练账号移交档案关联，原子释放旧关联。"""
        actor = self._get_actor()
        account_id = prompts.prompt_int("账号编号（q 取消）：", minimum=1)
        kind = prompts.prompt_int("档案类型（1 会员 / 2 教练）：", minimum=1, maximum=2)
        if kind == 1:
            member_id = prompts.prompt_int("新会员编号（q 取消）：", minimum=1)
            if not prompts.prompt_confirm("确认移交会员档案关联？"):
                return
            view = self._logic.relink_member(actor, account_id, member_id)
        else:
            coach_id = prompts.prompt_int("新教练编号（q 取消）：", minimum=1)
            if not prompts.prompt_confirm("确认移交教练档案关联？"):
                return
            view = self._logic.relink_coach(actor, account_id, coach_id)
        print(formatters.format_account(view, timezone_name=self._timezone_name))

    def query_logs(self) -> None:
        """管理员按条件分页查看脱敏日志；刷新时重新取得快照。"""
        actor = self._get_actor()
        from src.ui.cli.menus import browse_pages

        while True:
            snapshot = self._logic.open_log_snapshot(actor)
            if snapshot.skipped_lines:
                print(f"跳过损坏日志行：{snapshot.skipped_lines} 条")
            query = prompt_log_query(self._timezone_name)
            browse_pages(
                lambda paging: self._logic.query_logs(
                    actor, replace(query, paging=paging), snapshot=snapshot,
                ),
                lambda page: formatters.format_logs(
                    page, timezone_name=self._timezone_name,
                ),
            )
            if not prompts.prompt_confirm("重新读取日志快照并刷新？"):
                return

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _choose_role() -> Role:
        index = prompts.prompt_int(
            "角色（1 会员 / 2 教练 / 3 前台 / 4 管理员）：", minimum=1, maximum=4,
        )
        return _ROLES[index - 1]
