"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import (
    CoachInput,
    CoachUpdateInput,
    CoachView,
    CourseInput,
    CourseKind,
    CourseQuery,
    CourseView,
    DateWindow,
    NamedQuery,
    Page,
    RoomInput,
    RoomView,
    SessionInput,
    SessionQuery,
    SessionStatus,
    SessionView,
)
from src.models.course import Coach, Course, CourseSession, Room

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CoachRepository:
    """教练数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("CoachRepository.__init__ 尚未实现")

    def get(self, coach_id: int) -> CoachView | None:
        """查询教练详情。

        返回：CoachView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CoachRepository.get 尚未实现")

    def list(self, query: NamedQuery) -> Page[CoachView]:
        """按 id 升序稳定分页查询教练。

        返回：Page[CoachView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CoachRepository.list 尚未实现")

    def create(self, data: CoachInput) -> CoachView:
        """保存教练资料和账号关联。

        返回：CoachView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CoachRepository.create 尚未实现")

    def update(self, coach_id: int, data: CoachUpdateInput) -> CoachView:
        """更新姓名和专长。

        返回：CoachView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CoachRepository.update 尚未实现")

    def set_active(self, coach_id: int, active: bool) -> CoachView:
        """更改教练启用状态。

        返回：CoachView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CoachRepository.set_active 尚未实现")

    def set_account(self, coach_id: int, account_id: int) -> CoachView:
        """更改教练账号关联；不能留下无账号的教练。

        返回：CoachView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CoachRepository.set_account 尚未实现")

    def lock(self, coach_id: int) -> Coach | None:
        """锁定教练，供排课冲突校验。

        返回：Coach | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CoachRepository.lock 尚未实现")


class CourseRepository:
    """课程模板数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("CourseRepository.__init__ 尚未实现")

    def get(self, course_id: int) -> CourseView | None:
        """查询课程模板详情。

        返回：CourseView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseRepository.get 尚未实现")

    def lock(self, course_id: int) -> Course | None:
        """在当前事务锁定课程模板并读取最新 Course，不存在返回 None。

        协调模板修改和排课快照；不提交。当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseRepository.lock 尚未实现")

    def list(self, query: CourseQuery) -> Page[CourseView]:
        """按 id 升序稳定分页查询模板。

        返回：Page[CourseView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseRepository.list 尚未实现")

    def create(self, data: CourseInput) -> CourseView:
        """保存课程模板。

        返回：CourseView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseRepository.create 尚未实现")

    def update(self, course_id: int, data: CourseInput) -> CourseView:
        """更新课程模板；引用约束由服务检查。

        返回：CourseView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseRepository.update 尚未实现")

    def set_active(self, course_id: int, active: bool) -> CourseView:
        """归档或恢复课程模板。

        返回：CourseView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("CourseRepository.set_active 尚未实现")


class RoomRepository:
    """场地数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("RoomRepository.__init__ 尚未实现")

    def get(self, room_id: int) -> RoomView | None:
        """查询场地详情。

        返回：RoomView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("RoomRepository.get 尚未实现")

    def list(self, query: NamedQuery) -> Page[RoomView]:
        """按 id 升序稳定分页查询场地。

        返回：Page[RoomView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("RoomRepository.list 尚未实现")

    def create(self, data: RoomInput) -> RoomView:
        """新增场地与容量。

        返回：RoomView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("RoomRepository.create 尚未实现")

    def update(self, room_id: int, data: RoomInput) -> RoomView:
        """更新场地资料；容量影响由服务检查。

        返回：RoomView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("RoomRepository.update 尚未实现")

    def set_active(self, room_id: int, active: bool) -> RoomView:
        """停用或恢复场地。

        返回：RoomView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("RoomRepository.set_active 尚未实现")

    def lock(self, room_id: int) -> Room | None:
        """锁定场地，供排课冲突校验。

        返回：Room | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("RoomRepository.lock 尚未实现")


class SessionRepository:
    """具体课次数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("SessionRepository.__init__ 尚未实现")

    def get(self, session_id: int) -> SessionView | None:
        """读取课次及余位展示数据。

        返回：SessionView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.get 尚未实现")

    def list(
        self,
        query: SessionQuery,
        *,
        scope_coach_id: int | None,
        bookable_after: datetime | None,
    ) -> Page[SessionView]:
        """在角色范围内按 starts_at、id 升序稳定分页读取课表。

        教练传 scope_coach_id；会员传 bookable_after 并强制只读未开始的 scheduled 课次；
        前台和管理员两项都传 None。范围在计数和分页前应用，不附带会员名单。

        返回：Page[SessionView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.list 尚未实现")

    def create(
        self, data: SessionInput, *, course_name: str, kind: CourseKind,
    ) -> SessionView:
        """保存已校验的排课资料。

        返回：SessionView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.create 尚未实现")

    def set_status(self, session_id: int, status: SessionStatus) -> SessionView:
        """更新课次状态，不自行处理关联预约。

        返回：SessionView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.set_status 尚未实现")

    def has_conflict(self, *, coach_id: int, room_id: int, window: DateWindow) -> bool:
        """锁定当前读检查教练或场地时间重叠，排除取消课次。

        调用方须先锁定教练和场地；不得沿用事务先前的一致性读快照。
        返回：bool；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.has_conflict 尚未实现")

    def has_scheduled_for_coach(self, coach_id: int) -> bool:
        """锁定当前读检查教练是否仍有 scheduled 课次；调用方已经锁定教练。

        返回 bool，不写数据；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.has_scheduled_for_coach 尚未实现")

    def has_scheduled_for_room(self, room_id: int) -> bool:
        """锁定当前读检查场地是否仍有 scheduled 课次；调用方已经锁定场地。

        返回 bool，不写数据；当前调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.has_scheduled_for_room 尚未实现")

    def lock(self, session_id: int) -> CourseSession | None:
        """锁定并读取课次，供容量与状态校验。

        返回：CourseSession | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("SessionRepository.lock 尚未实现")
