"""教练、课程模板、场地与课次的 CLI 操作处理器。

处理器只负责“问什么、按什么顺序问、调用哪个服务、打印什么”，
权限、事务和业务规则都在 `CourseService`。用户在确认前取消时直接返回，
不会调用写服务；服务抛出的业务异常交给 CLI 操作边界统一处理。
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from src.models.contracts import (
    Actor,
    CoachInput,
    CoachUpdateInput,
    CourseInput,
    CourseQuery,
    NamedQuery,
    PageRequest,
    RoomInput,
    SessionInput,
    SessionQuery,
)
from src.services.course_service import CourseService
from src.ui.cli import formatters, prompts
from src.ui.cli.handlers.common import (
    date_window,
    optional_bool,
    optional_choice,
    optional_date,
    optional_int,
    optional_text,
)


class CourseHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成。
    """

    def __init__(
        self,
        service: CourseService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区。"""
        self._service = service
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    def create_coach(self) -> None:
        """采集账号、姓名和专长，确认后创建教练档案。"""
        actor = self._get_actor()
        account_id = prompts.prompt_int("教练账号编号", minimum=1)
        name = prompts.prompt_text("教练姓名")
        specialty = prompts.promptoptional_text("专长（可留空）") or ""
        if not prompts.prompt_confirm("确认创建该教练档案？"):
            print("已取消操作")
            return
        view = self._service.create_coach(
            actor, CoachInput(account_id=account_id, name=name, specialty=specialty)
        )
        print(formatters.format_coach(view, timezone_name=self._timezone_name))

    def update_coach(self) -> None:
        """采集教练编号、姓名和专长，确认后修改资料。"""
        actor = self._get_actor()
        coach_id = prompts.prompt_int("教练编号", minimum=1)
        name = prompts.prompt_text("新姓名")
        specialty = prompts.promptoptional_text("新专长（可留空）") or ""
        if not prompts.prompt_confirm("确认修改该教练资料？"):
            print("已取消操作")
            return
        view = self._service.update_coach(
            actor, coach_id, CoachUpdateInput(name=name, specialty=specialty)
        )
        print(formatters.format_coach(view, timezone_name=self._timezone_name))

    def get_coach(self) -> None:
        """按编号查看教练详情。"""
        actor = self._get_actor()
        coach_id = prompts.prompt_int("教练编号", minimum=1)
        print(formatters.format_coach(
            self._service.get_coach(actor, coach_id), timezone_name=self._timezone_name,
        ))

    def list_coaches(self) -> None:
        """按姓名关键词和启用状态分页查看教练。"""
        actor = self._get_actor()
        keyword = optional_text("姓名关键词（留空=全部）") or ""
        active = optional_bool("启用状态（启用/停用，留空=全部）")
        page = self._service.list_coaches(
            actor, NamedQuery(keyword=keyword, is_active=active, paging=PageRequest()),
        )
        print(formatters.format_coaches(page, timezone_name=self._timezone_name))

    def set_coach_active(self) -> None:
        """读取当前状态，确认后切换教练启用状态。"""
        actor = self._get_actor()
        coach_id = prompts.prompt_int("教练编号", minimum=1)
        current = self._service.get_coach(actor, coach_id)
        action = "停用" if current.is_active else "启用"
        print(formatters.format_coach(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm(f"确认{action}该教练？"):
            print("已取消操作")
            return
        view = self._service.set_coach_active(actor, coach_id, not current.is_active)
        print(formatters.format_coach(view, timezone_name=self._timezone_name))

    def create_course(self) -> None:
        """采集课程名称和默认时长，确认后创建私教模板。"""
        actor = self._get_actor()
        name = prompts.prompt_text("课程名称")
        duration = prompts.prompt_int("默认时长（分钟）", minimum=1, maximum=150)
        if not prompts.prompt_confirm("确认创建该课程模板？"):
            print("已取消操作")
            return
        view = self._service.create_course(
            actor, CourseInput(name=name, kind="private", duration_minutes=duration),
        )
        print(formatters.format_course(view, timezone_name=self._timezone_name))

    def update_course(self) -> None:
        """采集课程编号、名称和时长，确认后修改模板。"""
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号", minimum=1)
        name = prompts.prompt_text("新课程名称")
        duration = prompts.prompt_int("新默认时长（分钟）", minimum=1, maximum=150)
        if not prompts.prompt_confirm("确认修改该课程模板？"):
            print("已取消操作")
            return
        view = self._service.update_course(
            actor, course_id,
            CourseInput(name=name, kind="private", duration_minutes=duration),
        )
        print(formatters.format_course(view, timezone_name=self._timezone_name))

    def get_course(self) -> None:
        """按编号查看课程模板详情。"""
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号", minimum=1)
        print(formatters.format_course(
            self._service.get_course(actor, course_id), timezone_name=self._timezone_name,
        ))

    def list_courses(self) -> None:
        """按名称关键词和启用状态分页查看课程模板。"""
        actor = self._get_actor()
        keyword = optional_text("课程名称关键词（留空=全部）") or ""
        active = optional_bool("启用状态（启用/停用，留空=全部）")
        page = self._service.list_courses(
            actor, CourseQuery(keyword=keyword, is_active=active, paging=PageRequest()),
        )
        print(formatters.format_courses(page, timezone_name=self._timezone_name))

    def set_course_active(self) -> None:
        """读取当前状态，确认后归档或恢复课程模板。"""
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号", minimum=1)
        current = self._service.get_course(actor, course_id)
        action = "归档" if current.is_active else "恢复"
        print(formatters.format_course(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm(f"确认{action}该课程模板？"):
            print("已取消操作")
            return
        view = self._service.set_course_active(actor, course_id, not current.is_active)
        print(formatters.format_course(view, timezone_name=self._timezone_name))

    def create_room(self) -> None:
        """采集场地名称和容量，确认后新增场地。"""
        actor = self._get_actor()
        name = prompts.prompt_text("场地名称")
        capacity = prompts.prompt_int("最大容纳人数", minimum=1, maximum=1000)
        if not prompts.prompt_confirm("确认创建该场地？"):
            print("已取消操作")
            return
        view = self._service.create_room(actor, RoomInput(name=name, capacity=capacity))
        print(formatters.format_room(view, timezone_name=self._timezone_name))

    def update_room(self) -> None:
        """采集场地编号、名称和容量，确认后修改。"""
        actor = self._get_actor()
        room_id = prompts.prompt_int("场地编号", minimum=1)
        name = prompts.prompt_text("新场地名称")
        capacity = prompts.prompt_int("新最大容纳人数", minimum=1, maximum=1000)
        if not prompts.prompt_confirm("确认修改该场地？"):
            print("已取消操作")
            return
        view = self._service.update_room(
            actor, room_id, RoomInput(name=name, capacity=capacity),
        )
        print(formatters.format_room(view, timezone_name=self._timezone_name))

    def get_room(self) -> None:
        """按编号查看场地详情，并列出该场地指定日期的已排课次。"""
        actor = self._get_actor()
        room_id = prompts.prompt_int("场地编号", minimum=1)
        print(formatters.format_room(
            self._service.get_room(actor, room_id), timezone_name=self._timezone_name,
        ))
        day = optional_date("查看该场地的排课日期（YYYY-MM-DD，留空=全部）")
        page = self._service.list_sessions(
            actor,
            SessionQuery(
                window=date_window(day, self._timezone_name) if day else None,
                room_id=room_id,
                status="scheduled",
                paging=PageRequest(page_size=20),
            ),
        )
        print(formatters.format_sessions(page, timezone_name=self._timezone_name))

    def list_rooms(self) -> None:
        """按名称关键词和启用状态分页查看场地。"""
        actor = self._get_actor()
        keyword = optional_text("场地名称关键词（留空=全部）") or ""
        active = optional_bool("启用状态（启用/停用，留空=全部）")
        page = self._service.list_rooms(
            actor, NamedQuery(keyword=keyword, is_active=active, paging=PageRequest()),
        )
        print(formatters.format_rooms(page, timezone_name=self._timezone_name))

    def set_room_active(self) -> None:
        """读取当前状态，确认后停用或恢复场地。"""
        actor = self._get_actor()
        room_id = prompts.prompt_int("场地编号", minimum=1)
        current = self._service.get_room(actor, room_id)
        action = "停用" if current.is_active else "启用"
        print(formatters.format_room(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm(f"确认{action}该场地？"):
            print("已取消操作")
            return
        view = self._service.set_room_active(actor, room_id, not current.is_active)
        print(formatters.format_room(view, timezone_name=self._timezone_name))

    def create_session(self) -> None:
        """采集课程、教练、场地和起止时间，确认后发布课次。"""
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号", minimum=1)
        coach_id = prompts.prompt_int("教练编号", minimum=1)
        room_id = prompts.prompt_int("场地编号", minimum=1)
        starts_at = prompts.prompt_datetime("开始时间", timezone_name=self._timezone_name)
        ends_at = prompts.prompt_datetime("结束时间", timezone_name=self._timezone_name)
        if not prompts.prompt_confirm("确认发布该课次？"):
            print("已取消操作")
            return
        view = self._service.create_session(
            actor,
            SessionInput(
                course_id=course_id,
                coach_id=coach_id,
                room_id=room_id,
                starts_at=starts_at,
                ends_at=ends_at,
                capacity=1,
            ),
            str(uuid4()),
        )
        print(formatters.format_session(view, timezone_name=self._timezone_name))

    def get_session(self) -> None:
        """按编号查看课次详情。"""
        actor = self._get_actor()
        session_id = prompts.prompt_int("课次编号", minimum=1)
        print(formatters.format_session(
            self._service.get_session(actor, session_id), timezone_name=self._timezone_name,
        ))

    def list_sessions(self) -> None:
        """按日期、教练、场地和状态筛选课表。"""
        actor = self._get_actor()
        day = optional_date("上课日期（YYYY-MM-DD，留空=不限）")
        coach_id = optional_int("教练编号（留空=不限）")
        room_id = optional_int("场地编号（留空=不限）")
        status = optional_choice(
            "课次状态（scheduled/completed/cancelled，留空=不限）",
            {"scheduled": "scheduled", "completed": "completed", "cancelled": "cancelled"},
        )
        page = self._service.list_sessions(
            actor,
            SessionQuery(
                window=date_window(day, self._timezone_name) if day else None,
                coach_id=coach_id,
                room_id=room_id,
                status=status,  # type: ignore[arg-type]
                paging=PageRequest(),
            ),
        )
        print(formatters.format_sessions(page, timezone_name=self._timezone_name))

    def get_session_by_request(self) -> None:
        """按原请求编号核实排课或取消结果，不重新写数据。"""
        actor = self._get_actor()
        request_id = prompts.prompt_text("原请求编号")
        print(formatters.format_session(
            self._service.get_session_by_request(actor, request_id),
            timezone_name=self._timezone_name,
        ))

    def complete_session(self) -> None:
        """确认后完成已结束且没有待处理预约的课次。"""
        actor = self._get_actor()
        session_id = prompts.prompt_int("课次编号", minimum=1)
        current = self._service.get_session(actor, session_id)
        print(formatters.format_session(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm("确认完成该课次？完成后不能再签到或更正"):
            print("已取消操作")
            return
        view = self._service.complete_session(actor, session_id)
        print(formatters.format_session(view, timezone_name=self._timezone_name))

    def cancel_session(self) -> None:
        """确认后取消课次，并释放全部关联预约的额度占用。"""
        actor = self._get_actor()
        session_id = prompts.prompt_int("课次编号", minimum=1)
        current = self._service.get_session(actor, session_id)
        print(formatters.format_session(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm("确认取消该课次及其全部预约？"):
            print("已取消操作")
            return
        view = self._service.cancel_session(actor, session_id, str(uuid4()))
        print(formatters.format_session(view, timezone_name=self._timezone_name))
