"""CLI 导航与操作调用；错误分类由统一错误处理接口提供。"""
from __future__ import annotations

from collections.abc import Callable

from src.errors.base import ErrorResult
from src.errors.business import AuthenticationError, InputCancelled
from src.errors.handler import handle_error
from src.models.contracts import Actor
from src.ui.cli import menus
from src.ui.cli.menus import CliHandlers, MenuItem


def invoke_action(
    action: Callable[[], None],
    *,
    operation: str,
    actor_id: int | None = None,
    request_id: str | None = None,
) -> ErrorResult:
    """执行一次操作；取消返回菜单，EOF/Ctrl+C 传播到入口。"""
    try:
        action()
    except (EOFError, KeyboardInterrupt):
        raise
    except InputCancelled:
        pass
    except NotImplementedError:
        raise
    except Exception as exc:
        return handle_error(exc, operation=operation, actor_id=actor_id, request_id=request_id)
    return ErrorResult(message="", action="continue")


class GymCLI:
    """管理身份菜单及子菜单，服务继续检查实际操作权限。"""

    def __init__(
        self,
        handlers: CliHandlers,
        get_actor: Callable[[], Actor],
        logout: Callable[[], None],
    ) -> None:
        self._handlers = handlers
        self._get_actor = get_actor
        self._logout = logout

    def _sections(self, actor: Actor) -> dict[str, tuple[str, list[MenuItem]]]:
        """模块导航按角色显示；具体操作在各菜单函数登记。"""
        h = self._handlers
        sections = {
            "1": ("会员", menus.member_menu(h.member)),
            "2": ("产品与门禁", menus.product_menu(h.product)),
            "3": ("课程", menus.course_menu(h.course)),
            "4": ("预约", menus.booking_menu(h.booking)),
            "5": ("签到", menus.attendance_menu(h.attendance)),
            "6": ("评价", menus.review_menu(h.review)),
            "7": ("器械", menus.equipment_menu(h.equipment)),
        }
        if actor.role in {"member", "coach"}:
            sections["8"] = ("体测", menus.measurement_menu(h.measurement))
        if actor.role in {"admin", "receptionist"}:
            sections["9"] = ("报表", menus.report_menu(h.report))
        if actor.role == "admin":
            sections["10"] = ("账号", menus.auth_menu(h.auth))
        return sections

    def _execute(self, item: MenuItem, actor_id: int | None) -> str:
        result = invoke_action(item.action, operation=item.operation, actor_id=actor_id)
        if result.message:
            print(result.message)
        if result.action == "verify":
            if result.request_id is not None:
                print(f"核实请求编号：{result.request_id}")
            if result.record_id is not None:
                print(f"核实记录编号：{result.record_id}")
        if result.action == "login":
            self._logout()
        return result.action

    def run(self) -> int:
        """运行至退出；EOF/Ctrl+C 由入口清理后返回 0。"""
        submenu: tuple[str, list[MenuItem]] | None = None
        while True:
            try:
                actor = self._get_actor()
            except AuthenticationError:
                submenu = None
                print("\n健身房管理系统\n1 登录\n0 退出")
                choice = input("请选择：").strip()
                if choice == "0":
                    return 0
                if choice == "1":
                    action = self._execute(MenuItem(key="1", label="登录", operation="login", action=self._handlers.auth.login), None)
                    if action == "exit":
                        return 1
                else:
                    print("选择无效，请重试。")
                continue

            if submenu is not None:
                title, items = submenu
                print(f"\n{title}")
                for item in items:
                    print(f"{item.key} {item.label}")
                if not items:
                    print("本模块的操作尚待接入。")
                print("0 返回")
                choice = input("请选择：").strip()
                if choice == "0":
                    submenu = None
                    continue
                item = next((item for item in items if item.key == choice), None)
                if item is None:
                    print("选择无效，请重试。")
                    continue
                action = self._execute(item, actor.account_id)
                if action == "exit":
                    return 1
                if action == "login":
                    submenu = None
                continue

            sections = self._sections(actor)
            print("\n主菜单")
            for key, (title, _) in sections.items():
                print(f"{key} {title}")
            print("l 退出登录\n0 退出程序")
            choice = input("请选择：").strip().lower()
            if choice == "0":
                return 0
            if choice == "l":
                self._logout()
            elif choice in sections:
                submenu = sections[choice]
            else:
                print("选择无效，请重试。")
