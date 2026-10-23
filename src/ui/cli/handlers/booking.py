"""预约交互处理器。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from uuid import uuid4

from src.errors.business import PermissionDenied
from src.logic.course_logic import CourseLogic
from src.logic.entitlement_logic import EntitlementLogic
from src.logic.reservation_logic import ReservationLogic
from src.models.contracts import Actor, BookingInput, BookingQuery
from src.ui.cli import formatters, prompts
from src.ui.cli.handlers.course_booking_common import (
    date_window, optional_date, optional_int, optional_text,
)

_STATUS = {"reserved", "checked_in", "completed", "cancelled", "no_show"}


class BookingHandler:
    """收集预约输入、确认并调用 ReservationLogic。"""

    def __init__(
        self, logic: ReservationLogic, get_actor: Callable[[], Actor],
        course_logic: CourseLogic, entitlement_logic: EntitlementLogic,
        *, timezone_name: str,
    ) -> None:
        self._logic = logic
        self._get_actor = get_actor
        self._course_logic = course_logic
        self._entitlement_logic = entitlement_logic
        self._timezone_name = timezone_name

    @property
    def current_role(self) -> str:
        return self._get_actor().role

    def book(self) -> None:
        actor = self._get_actor()
        if actor.role == "coach":
            raise PermissionDenied("教练不能预约课次")
        if actor.role == "member":
            if actor.member_id is None:
                raise PermissionDenied("当前账号未关联会员档案")
            member_id = actor.member_id
        else:
            member_id = prompts.prompt_member_id()
        session_id = prompts.prompt_int("课次编号（q 取消）：", minimum=1)
        package_id = prompts.prompt_int("私教课包编号：", minimum=1)
        if not prompts.prompt_confirm("确认预约并占用 1 节私教课？"):
            return
        view = self._logic.book(
            actor, BookingInput(
                member_id=member_id, session_id=session_id, lesson_package_id=package_id,
            ), str(uuid4()),
        )
        print(formatters.format_booking(view, timezone_name=self._timezone_name))

    def get_booking(self) -> None:
        actor = self._get_actor()
        booking_id = prompts.prompt_int("预约编号（q 取消）：", minimum=1)
        print(formatters.format_booking(
            self._logic.get_booking(actor, booking_id), timezone_name=self._timezone_name,
        ))

    def get_booking_by_request(self) -> None:
        actor = self._get_actor()
        request_id = prompts.prompt_text("原请求编号（q 取消）：")
        print(formatters.format_booking(
            self._logic.get_booking_by_request(actor, request_id),
            timezone_name=self._timezone_name,
        ))

    def cancel(self) -> None:
        actor = self._get_actor()
        booking_id = prompts.prompt_int("预约编号（q 取消）：", minimum=1)
        current = self._logic.get_booking(actor, booking_id)
        print(formatters.format_booking(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm("确认取消该预约并释放 1 节占用？"):
            return
        view = self._logic.cancel(actor, booking_id, str(uuid4()))
        print(formatters.format_booking(view, timezone_name=self._timezone_name))

    def list_bookings(self) -> None:
        from src.ui.cli.menus import browse_pages
        actor = self._get_actor()
        member_id = None
        if actor.role != "member":
            member_id = optional_int("会员编号（留空=不限）：")
        session_id = optional_int("课次编号（留空=不限）：")
        package_id = optional_int("课包编号（留空=不限）：")
        day = optional_date("上课日期（YYYY-MM-DD，留空=不限）：")
        status = optional_text("状态 reserved/checked_in/completed/cancelled/no_show（留空=不限）：")
        if status is not None and status not in _STATUS:
            from src.errors.business import InvalidInputError
            raise InvalidInputError("预约状态不合法")
        query = BookingQuery(
            member_id=member_id, session_id=session_id, lesson_package_id=package_id,
            status=status, window=date_window(day, self._timezone_name) if day else None,
        )
        browse_pages(
            lambda paging: self._logic.list_bookings(actor, replace(query, paging=paging)),
            lambda page: formatters.format_bookings(page, timezone_name=self._timezone_name),
        )
