"""教练、课程和场地服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import (
    Actor,
    CoachInput,
    CoachUpdateInput,
    CoachView,
    CourseInput,
    CourseQuery,
    CourseView,
    NamedQuery,
    Page,
    RoomInput,
    RoomView,
    SessionInput,
    SessionQuery,
    SessionView,
)
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CourseService:
    """教练、课程和场地服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture.md“开发前必读”的返回、异常、权限和事务约定。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_coach(self, actor: Actor, data: CoachInput) -> CoachView:
        """创建教练档案。

        返回：CoachView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.create_coach 尚未实现")

    def update_coach(self, actor: Actor, coach_id: int, data: CoachUpdateInput) -> CoachView:
        """修改教练资料。

        返回：CoachView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.update_coach 尚未实现")

    def get_coach(self, actor: Actor, coach_id: int) -> CoachView:
        """查询教练详情。

        返回：CoachView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.get_coach 尚未实现")

    def list_coaches(self, actor: Actor, query: NamedQuery) -> Page[CoachView]:
        """分页查询教练。

        返回：Page[CoachView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.list_coaches 尚未实现")

    def set_coach_active(self, actor: Actor, coach_id: int, active: bool) -> CoachView:
        """停用或恢复教练。

        停用前锁定教练并拒绝仍有 scheduled 课次的情况；排课使用同一教练锁。
        返回：CoachView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.set_coach_active 尚未实现")

    def create_course(self, actor: Actor, data: CourseInput) -> CourseView:
        """创建课程模板。

        仅接受 private 私教类型；duration_minutes 为 1–150 的整数，越界抛 InvalidInputError。
        返回：CourseView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.create_course 尚未实现")

    def update_course(self, actor: Actor, course_id: int, data: CourseInput) -> CourseView:
        """修改课程模板。

        仅接受 private 类型及 1–150 整数分钟；越界抛 InvalidInputError，不改变已发布课次。
        返回：CourseView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.update_course 尚未实现")

    def get_course(self, actor: Actor, course_id: int) -> CourseView:
        """查询课程模板详情。

        返回：CourseView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.get_course 尚未实现")

    def list_courses(self, actor: Actor, query: CourseQuery) -> Page[CourseView]:
        """分页查询课程模板。

        返回：Page[CourseView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.list_courses 尚未实现")

    def set_course_active(self, actor: Actor, course_id: int, active: bool) -> CourseView:
        """归档或恢复课程模板。

        返回：CourseView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.set_course_active 尚未实现")

    def create_room(self, actor: Actor, data: RoomInput) -> RoomView:
        """创建场地。

        返回：RoomView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.create_room 尚未实现")

    def update_room(self, actor: Actor, room_id: int, data: RoomInput) -> RoomView:
        """修改场地资料。

        锁定场地后更新；容量至少为 1，满足当前固定容量为 1 的私教课。
        返回：RoomView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.update_room 尚未实现")

    def get_room(self, actor: Actor, room_id: int) -> RoomView:
        """查询场地基础详情；指定日期的时段由 list_sessions 使用 room_id 和时间窗口查询。

        返回：RoomView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.get_room 尚未实现")

    def list_rooms(self, actor: Actor, query: NamedQuery) -> Page[RoomView]:
        """分页查询场地。

        返回：Page[RoomView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.list_rooms 尚未实现")

    def set_room_active(self, actor: Actor, room_id: int, active: bool) -> RoomView:
        """停用或恢复场地。

        停用前锁定场地并拒绝仍有 scheduled 课次的情况；排课使用同一场地锁。
        返回：RoomView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.set_room_active 尚未实现")

    def create_session(self, actor: Actor, data: SessionInput, request_id: str) -> SessionView:
        """创建具体课次。

        起止时间差必须等于模板分钟数，且不超过 150 分钟；容量固定为 1。
        不限定营业时段，允许跨午夜；全部资源锁取得后重新确认 starts_at 仍晚于当前时刻。
        越界抛 InvalidInputError，教练或场地撞期抛 ScheduleConflict。
        返回：SessionView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.create_session 尚未实现")

    def get_session(self, actor: Actor, session_id: int) -> SessionView:
        """查询课次详情。

        会员只能查未开始的 scheduled 公开课次；教练只能查自己的课次。
        越出角色可见范围与记录不存在一样抛 NotFoundError。
        返回：SessionView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.get_session 尚未实现")

    def list_sessions(self, actor: Actor, query: SessionQuery) -> Page[SessionView]:
        """分页查询课表。

        会员强制只查未开始的 scheduled 课次；教练强制限定为本人课次；
        前台和管理员可使用全部筛选条件。范围必须在仓储计数和分页前应用。
        返回：Page[SessionView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.list_sessions 尚未实现")

    def get_session_by_request(self, actor: Actor, request_id: str) -> SessionView:
        """按本人原排课或取消请求核实结果，返回课次的当前 SessionView。

        不写数据；无记录或不可见抛 NotFoundError，操作类型不匹配抛 ConflictError。
        查不到不能证明原提交失败；其余异常遵守 docs/architecture.md“开发前必读”的约定。当前仅占位。"""
        raise NotImplementedError("CourseService.get_session_by_request 尚未实现")

    def complete_session(self, actor: Actor, session_id: int) -> SessionView:
        """本课教练或管理员结束已到结束时间且没有待处理预约的课次。

        锁定课次后生成当前时刻并复核 ends_at、状态，并以锁定当前读检查开放预约。
        返回 SessionView；同事务更新课次状态，重复完成返回当前结果。
        尚未结束、有 reserved/checked_in 预约或已取消时抛 InvalidState。
        其余异常遵守 docs/architecture.md“开发前必读”的约定；当前仅占位。"""
        raise NotImplementedError("CourseService.complete_session 尚未实现")

    def cancel_session(self, actor: Actor, session_id: int, request_id: str) -> SessionView:
        """取消课次并释放预约占用。

        先在独立只读事务取得开放预约候选，再用新事务按会员、课次、已售会员卡、预约顺序加锁。
        课次锁内重读的候选发生变化时，提交前最多重开事务 3 次；提交未知不得自动重试。
        每次重开都使用新的锁后时刻；等待跨过开课时刻则拒绝取消且不写防重记录。
        返回：SessionView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture.md“开发前必读”的输入、权限、异常和事务约定。"""
        raise NotImplementedError("CourseService.cancel_session 尚未实现")
