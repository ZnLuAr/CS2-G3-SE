"""预约相关的 CLI 操作处理器。

处理器只收集输入、确认并打印结果；卡资格、满员、撞期、权限和事务
由 `BookingService` 判断。会员预约时自动使用自己的会员编号，前台和
管理员才需要输入代约的会员编号。
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from src.errors.business import PermissionDenied
from src.models.contracts import (
    Actor,
    BookingInput,
    BookingQuery,
    PageRequest,
)
from src.services.booking_service import BookingService
from src.services.course_service import CourseService
from src.services.product_service import ProductService
from src.ui.cli import formatters, prompts
from src.ui.cli.handlers.common import (
    date_window,
    optional_choice,
    optional_date,
    optional_int,
)


class BookingHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成。
    """

    def __init__(
        self,
        service: BookingService,
        get_actor: Callable[[], Actor],
        course_service: CourseService,
        product_service: ProductService,
        *, timezone_name: str,
    ) -> None:
        """接收服务、身份回调、课程/产品查询服务及门店时区。"""
        self._service = service
        self._get_actor = get_actor
        self._course_service = course_service
        self._product_service = product_service
        self._timezone_name = timezone_name

    def book(self) -> None:
        """采集会员（或本人）、课次和会员卡，确认后创建预约。"""
        actor = self._get_actor()
        if actor.role == "member":
            if actor.member_id is None:
                raise PermissionDenied("当前账号未关联会员档案")
            member_id = actor.member_id
        elif actor.role == "coach":
            raise PermissionDenied("教练不能预约课次")
        else:
            member_id = prompts.prompt_member_id()
        session_id = prompts.prompt_int("课次编号", minimum=1)
        membership_id = prompts.prompt_int("会员卡编号", minimum=1)
        if not prompts.prompt_confirm("确认预约该课次并占用 1 节私教额度？"):
            print("已取消操作")
            return
        view = self._service.book(
            actor,
            BookingInput(
                member_id=member_id,
                session_id=session_id,
                membership_id=membership_id,
            ),
            str(uuid4()),
        )
        print(formatters.format_booking(view, timezone_name=self._timezone_name))

    def get_booking(self) -> None:
        """按编号查看预约详情。"""
        actor = self._get_actor()
        booking_id = prompts.prompt_int("预约编号", minimum=1)
        print(formatters.format_booking(
            self._service.get_booking(actor, booking_id),
            timezone_name=self._timezone_name,
        ))

    def get_booking_by_request(self) -> None:
        """按原请求编号核实预约或取消结果，不重新写数据。"""
        actor = self._get_actor()
        request_id = prompts.prompt_text("原请求编号")
        print(formatters.format_booking(
            self._service.get_booking_by_request(actor, request_id),
            timezone_name=self._timezone_name,
        ))

    def cancel(self) -> None:
        """确认后取消开课前的未签到预约，并释放私教额度占用。"""
        actor = self._get_actor()
        booking_id = prompts.prompt_int("预约编号", minimum=1)
        current = self._service.get_booking(actor, booking_id)
        print(formatters.format_booking(current, timezone_name=self._timezone_name))
        if not prompts.prompt_confirm("确认取消该预约并释放 1 节私教额度？"):
            print("已取消操作")
            return
        view = self._service.cancel(actor, booking_id, str(uuid4()))
        print(formatters.format_booking(view, timezone_name=self._timezone_name))

    def list_bookings(self) -> None:
        """按会员、课次、日期和状态筛选预约；会员和教练的范围由服务收窄。"""
        actor = self._get_actor()
        member_id = None
        if actor.role != "member":
            member_id = optional_int("会员编号（留空=不限）")
        session_id = optional_int("课次编号（留空=不限）")
        day = optional_date("上课日期（YYYY-MM-DD，留空=不限）")
        status = optional_choice(
            "预约状态（reserved/checked_in/completed/cancelled/no_show，留空=不限）",
            {
                "reserved": "reserved",
                "checked_in": "checked_in",
                "completed": "completed",
                "cancelled": "cancelled",
                "no_show": "no_show",
            },
        )
        page = self._service.list_bookings(
            actor,
            BookingQuery(
                member_id=member_id,
                session_id=session_id,
                window=date_window(day, self._timezone_name) if day else None,
                status=status,  # type: ignore[arg-type]
                paging=PageRequest(),
            ),
        )
        print(formatters.format_bookings(page, timezone_name=self._timezone_name))
