"""课程、教练、场地与课次的交互处理器。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from uuid import uuid4

from src.errors.business import InvalidInputError, InvalidState
from src.logic.course_logic import CourseLogic
from src.logic.reservation_logic import ReservationLogic
from src.models.contracts import (
    Actor, CoachInput, CourseInput, NamedQuery, RoomInput, SessionInput, SessionQuery,
)
from src.ui.cli import formatters, prompts
from src.ui.cli.handlers.course_booking_common import (
    date_window, optional_date, optional_int, optional_text,
)


_SESSION_STATUS = {"scheduled", "completed", "cancelled"}


class CourseHandler:
    """收集输入、确认操作、调用 CourseLogic 并展示结果。"""

    def __init__(
        self,
        logic: CourseLogic,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
        reservation_logic: ReservationLogic | None = None,
    ) -> None:
        self._logic = logic
        self._get_actor = get_actor
        self._timezone_name = timezone_name
        self._reservation_logic = reservation_logic

    @property
    def current_role(self) -> str:
        return self._get_actor().role

    def create_coach(self) -> None:
        actor = self._get_actor()
        name = prompts.prompt_text("教练姓名（q 取消）：")
        phone = prompts.prompt_optional_text("联系电话（可留空）：")
        if not prompts.prompt_confirm("确认创建教练档案？"):
            return
        view = self._logic.create_coach(actor, CoachInput(name=name, phone=phone))
        print(formatters.format_coach(view, timezone_name=self._timezone_name))

    def update_coach(self) -> None:
        actor = self._get_actor()
        coach_id = prompts.prompt_int("教练编号（q 取消）：", minimum=1)
        name = prompts.prompt_text("新姓名：")
        phone = prompts.prompt_optional_text("新联系电话（可留空）：")
        if not prompts.prompt_confirm("确认修改教练资料？"):
            return
        view = self._logic.update_coach(actor, coach_id, CoachInput(name=name, phone=phone))
        print(formatters.format_coach(view, timezone_name=self._timezone_name))

    def get_coach(self) -> None:
        actor = self._get_actor()
        coach_id = prompts.prompt_int("教练编号（q 取消）：", minimum=1)
        print(formatters.format_coach(
            self._logic.get_coach(actor, coach_id), timezone_name=self._timezone_name,
        ))

    def list_coaches(self) -> None:
        from src.ui.cli.menus import browse_pages
        actor = self._get_actor()
        keyword = optional_text("姓名关键词（留空=全部）：") or ""
        active = None
        if prompts.prompt_confirm("筛选启用状态？"):
            active = prompts.prompt_confirm("只看启用？")
        query = NamedQuery(keyword=keyword, is_active=active)
        browse_pages(
            lambda paging: self._logic.list_coaches(actor, replace(query, paging=paging)),
            lambda page: formatters.format_coaches(page, timezone_name=self._timezone_name),
        )

    def set_coach_active(self) -> None:
        actor = self._get_actor()
        coach_id = prompts.prompt_int("教练编号（q 取消）：", minimum=1)
        current = self._logic.get_coach(actor, coach_id)
        action = "停用" if current.is_active else "启用"
        print(formatters.format_coach(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm(f"确认{action}该教练？"):
            return
        view = self._logic.set_coach_active(actor, coach_id, not current.is_active)
        print(formatters.format_coach(view, timezone_name=self._timezone_name))

    def create_course(self) -> None:
        actor = self._get_actor()
        name = prompts.prompt_text("课程名称（q 取消）：")
        description = prompts.prompt_optional_text("课程说明（可留空）：")
        duration = prompts.prompt_int("默认时长（分钟）：", minimum=1, maximum=150)
        if not prompts.prompt_confirm("确认创建课程模板？"):
            return
        view = self._logic.create_course(actor, CourseInput(
            name=name, description=description, kind="private", duration_minutes=duration,
        ))
        print(formatters.format_course(view, timezone_name=self._timezone_name))

    def update_course(self) -> None:
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号（q 取消）：", minimum=1)
        name = prompts.prompt_text("新课程名称：")
        description = prompts.prompt_optional_text("新课程说明（可留空）：")
        duration = prompts.prompt_int("新默认时长（分钟）：", minimum=1, maximum=150)
        if not prompts.prompt_confirm("确认修改课程模板？"):
            return
        view = self._logic.update_course(actor, course_id, CourseInput(
            name=name, description=description, kind="private", duration_minutes=duration,
        ))
        print(formatters.format_course(view, timezone_name=self._timezone_name))

    def get_course(self) -> None:
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号（q 取消）：", minimum=1)
        print(formatters.format_course(
            self._logic.get_course(actor, course_id), timezone_name=self._timezone_name,
        ))

    def list_courses(self) -> None:
        from src.ui.cli.menus import browse_pages
        actor = self._get_actor()
        keyword = optional_text("课程名称关键词（留空=全部）：") or ""
        active = None
        if prompts.prompt_confirm("筛选启用状态？"):
            active = prompts.prompt_confirm("只看启用？")
        query = NamedQuery(keyword=keyword, is_active=active)
        browse_pages(
            lambda paging: self._logic.list_courses(actor, replace(query, paging=paging)),
            lambda page: formatters.format_courses(page, timezone_name=self._timezone_name),
        )

    def set_course_active(self) -> None:
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号（q 取消）：", minimum=1)
        current = self._logic.get_course(actor, course_id)
        action = "归档" if current.is_active else "恢复"
        print(formatters.format_course(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm(f"确认{action}该课程模板？"):
            return
        view = self._logic.set_course_active(actor, course_id, not current.is_active)
        print(formatters.format_course(view, timezone_name=self._timezone_name))

    def create_room(self) -> None:
        actor = self._get_actor()
        name = prompts.prompt_text("场地名称（q 取消）：")
        location = prompts.prompt_optional_text("位置（可留空）：")
        if not prompts.prompt_confirm("确认创建场地？"):
            return
        view = self._logic.create_room(actor, RoomInput(name=name, location=location))
        print(formatters.format_room(view, timezone_name=self._timezone_name))

    def update_room(self) -> None:
        actor = self._get_actor()
        room_id = prompts.prompt_int("场地编号（q 取消）：", minimum=1)
        name = prompts.prompt_text("新场地名称：")
        location = prompts.prompt_optional_text("新位置（可留空）：")
        if not prompts.prompt_confirm("确认修改场地？"):
            return
        view = self._logic.update_room(actor, room_id, RoomInput(name=name, location=location))
        print(formatters.format_room(view, timezone_name=self._timezone_name))

    def get_room(self) -> None:
        from src.ui.cli.menus import browse_pages
        actor = self._get_actor()
        room_id = prompts.prompt_int("场地编号（q 取消）：", minimum=1)
        print(formatters.format_room(
            self._logic.get_room(actor, room_id), timezone_name=self._timezone_name,
        ))
        day = optional_date("查看该场地的排课日期（YYYY-MM-DD，留空=不限）：")
        query = SessionQuery(
            room_id=room_id, status="scheduled",
            window=date_window(day, self._timezone_name) if day else None,
        )
        browse_pages(
            lambda paging: self._logic.list_sessions(actor, replace(query, paging=paging)),
            lambda page: formatters.format_sessions(page, timezone_name=self._timezone_name),
        )

    def list_rooms(self) -> None:
        from src.ui.cli.menus import browse_pages
        actor = self._get_actor()
        keyword = optional_text("场地名称关键词（留空=全部）：") or ""
        active = None
        if prompts.prompt_confirm("筛选启用状态？"):
            active = prompts.prompt_confirm("只看启用？")
        query = NamedQuery(keyword=keyword, is_active=active)
        browse_pages(
            lambda paging: self._logic.list_rooms(actor, replace(query, paging=paging)),
            lambda page: formatters.format_rooms(page, timezone_name=self._timezone_name),
        )

    def set_room_active(self) -> None:
        actor = self._get_actor()
        room_id = prompts.prompt_int("场地编号（q 取消）：", minimum=1)
        current = self._logic.get_room(actor, room_id)
        action = "停用" if current.is_active else "启用"
        print(formatters.format_room(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm(f"确认{action}该场地？"):
            return
        view = self._logic.set_room_active(actor, room_id, not current.is_active)
        print(formatters.format_room(view, timezone_name=self._timezone_name))

    def create_session(self) -> None:
        actor = self._get_actor()
        course_id = prompts.prompt_int("课程编号（q 取消）：", minimum=1)
        coach_id = prompts.prompt_int("教练编号：", minimum=1)
        room_id = prompts.prompt_int("场地编号：", minimum=1)
        starts_at = prompts.prompt_datetime("开始时间（YYYY-MM-DD HH:MM）：", timezone_name=self._timezone_name)
        ends_at = prompts.prompt_datetime("结束时间（YYYY-MM-DD HH:MM）：", timezone_name=self._timezone_name)
        if not prompts.prompt_confirm("确认发布课次？"):
            return
        view = self._logic.create_session(actor, SessionInput(
            course_id=course_id, coach_id=coach_id, room_id=room_id,
            starts_at=starts_at, ends_at=ends_at,
        ), str(uuid4()))
        print(formatters.format_session(view, timezone_name=self._timezone_name))

    def get_session(self) -> None:
        actor = self._get_actor()
        session_id = prompts.prompt_int("课次编号（q 取消）：", minimum=1)
        print(formatters.format_session(
            self._logic.get_session(actor, session_id), timezone_name=self._timezone_name,
        ))

    def list_sessions(self) -> None:
        from src.ui.cli.menus import browse_pages
        actor = self._get_actor()
        day = optional_date("上课日期（YYYY-MM-DD，留空=不限）：")
        coach_id = optional_int("教练编号（留空=不限）：")
        room_id = optional_int("场地编号（留空=不限）：")
        status = optional_text("状态 scheduled/completed/cancelled（留空=不限）：")
        if status is not None and status not in _SESSION_STATUS:
            raise InvalidInputError("课次状态不合法")
        query = SessionQuery(
            coach_id=coach_id, room_id=room_id, status=status,
            window=date_window(day, self._timezone_name) if day else None,
        )
        browse_pages(
            lambda paging: self._logic.list_sessions(actor, replace(query, paging=paging)),
            lambda page: formatters.format_sessions(page, timezone_name=self._timezone_name),
        )

    def get_session_by_request(self) -> None:
        actor = self._get_actor()
        request_id = prompts.prompt_text("原请求编号（q 取消）：")
        print(formatters.format_session(
            self._logic.get_session_by_request(actor, request_id),
            timezone_name=self._timezone_name,
        ))

    def complete_session(self) -> None:
        actor = self._get_actor()
        session_id = prompts.prompt_int("课次编号（q 取消）：", minimum=1)
        current = self._logic.get_session(actor, session_id)
        print(formatters.format_session(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm("确认完成该课次？"):
            return
        view = self._logic.complete_session(actor, session_id)
        print(formatters.format_session(view, timezone_name=self._timezone_name))

    def cancel_session(self) -> None:
        if self._reservation_logic is None:
            raise InvalidState("课次取消入口不可用")
        actor = self._get_actor()
        session_id = prompts.prompt_int("课次编号（q 取消）：", minimum=1)
        current = self._logic.get_session(actor, session_id)
        print(formatters.format_session(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm("确认取消该课次及其全部预约？"):
            return
        view = self._reservation_logic.cancel_session(actor, session_id, str(uuid4()))
        print(formatters.format_session(view, timezone_name=self._timezone_name))
