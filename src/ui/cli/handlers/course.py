"""按业务划分的 CLI 交互接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable

from src.models.contracts import Actor
from src.services.course_service import CourseService


class CourseHandler:
    """收集输入、确认操作、调用业务服务并展示结果。

    get_actor 每次取得当前身份；不接收数据库会话，不实现业务规则。
    各操作返回 None 表示交互完成；当前只声明接口，调用即报未实现。
    """

    def __init__(
        self,
        service: CourseService,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收服务、身份回调及 App 提供的门店时区；需要时另接查询服务或登录回调。"""
        self._service = service
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    def create_coach(self) -> None:
        """组织 CourseService.create_coach 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.create_coach 尚未实现")

    def update_coach(self) -> None:
        """组织 CourseService.update_coach 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.update_coach 尚未实现")

    def get_coach(self) -> None:
        """组织 CourseService.get_coach 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.get_coach 尚未实现")

    def list_coaches(self) -> None:
        """组织 CourseService.list_coaches 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.list_coaches 尚未实现")

    def set_coach_active(self) -> None:
        """组织 CourseService.set_coach_active 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.set_coach_active 尚未实现")

    def create_course(self) -> None:
        """组织 CourseService.create_course 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.create_course 尚未实现")

    def update_course(self) -> None:
        """组织 CourseService.update_course 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.update_course 尚未实现")

    def get_course(self) -> None:
        """组织 CourseService.get_course 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.get_course 尚未实现")

    def list_courses(self) -> None:
        """组织 CourseService.list_courses 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.list_courses 尚未实现")

    def set_course_active(self) -> None:
        """组织 CourseService.set_course_active 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.set_course_active 尚未实现")

    def create_room(self) -> None:
        """组织 CourseService.create_room 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.create_room 尚未实现")

    def update_room(self) -> None:
        """组织 CourseService.update_room 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.update_room 尚未实现")

    def get_room(self) -> None:
        """展示场地基础详情，并可按门店日期分页展示已排课时段。

        日期转换为本地当日的 UTC DateWindow，再以 room_id 调用 list_sessions；日期为空只查详情。
        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.get_room 尚未实现")

    def list_rooms(self) -> None:
        """组织 CourseService.list_rooms 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.list_rooms 尚未实现")

    def set_room_active(self) -> None:
        """组织 CourseService.set_room_active 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.set_room_active 尚未实现")

    def create_session(self) -> None:
        """组织 CourseService.create_session 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.create_session 尚未实现")

    def get_session(self) -> None:
        """组织 CourseService.get_session 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.get_session 尚未实现")

    def list_sessions(self) -> None:
        """组织 CourseService.list_sessions 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.list_sessions 尚未实现")

    def get_session_by_request(self) -> None:
        """采集原请求编号，调用服务只读核实课次并展示结果；异常交操作边界。

        不重新排课；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseHandler.get_session_by_request 尚未实现")

    def complete_session(self) -> None:
        """采集课次编号并确认后调用收尾服务，展示 SessionView；异常交操作边界。

        当前调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseHandler.complete_session 尚未实现")

    def cancel_session(self) -> None:
        """组织 CourseService.cancel_session 的交互步骤。

        输入由 prompts 采集；成功结果交给 formatters 展示。
        异常交给 CLI 操作边界处理；取消输入不写业务数据。"""
        raise NotImplementedError("CourseHandler.cancel_session 尚未实现")
