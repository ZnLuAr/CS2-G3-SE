"""候补仓储合同；状态规则由服务校验，SQL 方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import (
    Page, WaitlistInput, WaitlistQuery, WaitlistStatus, WaitlistSummaryView, WaitlistView,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class WaitlistRepository:
    """使用调用方Session，失败抛StorageError；候补锁位于预约锁之后。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, waitlist_id: int) -> WaitlistView | None:
        """读取详情并计算waiting位置；未找到返回None。"""
        raise NotImplementedError

    def list(
        self, query: WaitlistQuery, *, scope_member_id: int | None,
    ) -> Page[WaitlistView]:
        """按明确的本人或员工范围分页，total和内容使用同一快照。"""
        raise NotImplementedError

    def get_summary(self, session_id: int) -> WaitlistSummaryView:
        """只返回课次编号与waiting人数，由服务验证本课教练权限。"""
        raise NotImplementedError

    def find_waiting_for_member_session(
        self, member_id: int, session_id: int,
    ) -> WaitlistView | None:
        """会员/课次/课包/预约锁取得后以锁定当前读检查活动候补。"""
        raise NotImplementedError

    def list_reconciliation_session_ids(self, as_of: datetime) -> tuple[int, ...]:
        """按固定时刻定位有空位或已开课且仍有waiting的课次，按id升序。"""
        raise NotImplementedError

    def list_waiting_for_session(self, session_id: int) -> tuple[WaitlistView, ...]:
        """按joined_at/id顺序返回候选；事务写入前须重新锁定复核。"""
        raise NotImplementedError

    def lock(self, waitlist_id: int) -> WaitlistView | None:
        """按全局锁序锁定当前候补，未找到返回None。"""
        raise NotImplementedError

    def create(self, data: WaitlistInput, joined_at: datetime) -> WaitlistView:
        """写入waiting记录，返回含位置的View；互斥与满员已由服务检查。"""
        raise NotImplementedError

    def set_state(
        self, waitlist_id: int, *, status: WaitlistStatus,
        booking_id: int | None, closed_at: datetime,
    ) -> WaitlistView:
        """持候补锁后写终态、关联预约和结束时间；状态规则由服务校验。"""
        raise NotImplementedError
