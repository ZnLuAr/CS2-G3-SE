"""体测输入校验、当前授课授权和历史读取范围。"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from src.db.booking_repo import BookingRepository
from src.db.measurement_repo import MeasurementRepository
from src.db.member_repo import MemberRepository
from src.errors import InvalidInputError, InvalidState, NotFoundError, PermissionDenied
from src.models.contracts import (
    Actor,
    DateWindow,
    MeasurementComparison,
    MeasurementInput,
    MeasurementQuery,
    MeasurementView,
    Page,
    PageRequest,
)
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _positive_id(value: int) -> None:
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise InvalidInputError("记录编号必须是有效的正整数")


def _timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InvalidInputError("时刻必须包含时区信息")
    try:
        utc = value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise InvalidInputError("时刻超出数据库可用范围") from exc
    if utc.year < 1000:
        raise InvalidInputError("时刻超出数据库可用范围")
    return utc


def _number(value: Decimal, minimum: str, maximum: str, label: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise InvalidInputError(f"{label}必须是有效的十进制数值")
    if not Decimal(minimum) <= value <= Decimal(maximum):
        raise InvalidInputError(f"{label}必须在 {minimum} 至 {maximum} 范围内")
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class MeasurementService:
    """体测服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md的返回、异常、权限和事务约定。
    会员只查本人；教练历史查看权永久保留，最后有效预约结束后停止更新，再预约恢复。
    前台和管理员不能查看个人体测明细，也不能调用详情、列表或对比接口绕过限制。
    截止时间由本教练的预约记录计算，按体测 created_at 过滤，不按可补录的 measured_at。
    详情、历史总数及内容、对比两条记录共用同一范围和 as_of；不能只在界面隐藏。
    业务方法共用传入 Session，由调用方 Logic 提交或回滚。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def record(self, session: Session, actor: Actor, data: MeasurementInput) -> MeasurementView:
        """录入会员体测。

        身高为 100.00–250.00 cm，体重为 30.00–150.00 kg，含边界；体脂可空或 0.00–100.00%。
        超出范围抛 InvalidInputError，不写入记录。
        教练须有该会员的当前有效预约；历史只读权限不能用于新增，越权抛 PermissionDenied。
        获得会员行锁后生成一次可信 created_at，同一时刻用于预约授权的 at 和记录写入；原记录不可编辑或删除。
        measured_at 必须带时区且不能晚于 created_at，未来测量时刻抛 InvalidInputError。

        返回：MeasurementView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：InvalidInputError、PermissionDenied、NotFoundError、InvalidState。"""
        if not isinstance(data, MeasurementInput):
            raise InvalidInputError("体测输入格式不正确")
        _positive_id(data.member_id)
        measured_at = _timestamp(data.measured_at)
        data = replace(
            data, measured_at=measured_at,
            height_cm=_number(data.height_cm, "100.00", "250.00", "身高"),
            weight_kg=_number(data.weight_kg, "30.00", "150.00", "体重"),
            body_fat_pct=None if data.body_fat_pct is None else _number(
                data.body_fat_pct, "0.00", "100.00", "体脂率",
            ),
        )
        actor = self._auth.verify_actor(session, actor)
        if actor.role != "coach" or actor.coach_id is None:
            raise PermissionDenied("只有当前授课教练可以录入体测")
        member = MemberRepository(session).lock(data.member_id)
        if member is None:
            raise NotFoundError("会员档案不存在")
        if member.status != "active":
            raise InvalidState("归档会员不能新增体测记录")
        created_at = datetime.now(timezone.utc)
        if measured_at > created_at:
            raise InvalidInputError("测量时刻不能晚于实际录入时刻")
        if not BookingRepository(session).has_current_coaching_booking(
            data.member_id, actor.coach_id, at=created_at,
        ):
            raise PermissionDenied("没有该会员当前有效的授课预约")
        return MeasurementRepository(session).create(data, actor.coach_id, created_at=created_at)

    def get_measurement(self, session: Session, actor: Actor, measurement_id: int) -> MeasurementView:
        """查看体测详情。

        会员只能查看本人；教练只能查看授权范围；前台和管理员无权查看明细。
        数据访问必须带服务生成的身份范围和查询时刻；范围外或不存在均抛 NotFoundError。
        返回：MeasurementView。不修改业务数据。
        异常：InvalidInputError、PermissionDenied、NotFoundError。"""
        _positive_id(measurement_id)
        actor = self._auth.verify_actor(session, actor)
        member_id, coach_id = self._scope(actor)
        result = MeasurementRepository(session).get(
            measurement_id, scope_member_id=member_id, scope_coach_id=coach_id,
            as_of=datetime.now(timezone.utc),
        )
        if result is None:
            raise NotFoundError("体测记录不存在或不可见")
        return result

    def list_measurements(self, session: Session, actor: Actor, query: MeasurementQuery) -> Page[MeasurementView]:
        """分页查看体测历史。

        会员只能查询本人；前台和管理员无权查询个人体测历史。
        教练只得到可见截止内的记录，total 也按该范围统计；没有历史授权时为正常空 Page。
        返回：Page[MeasurementView]。不修改业务数据。
        异常：InvalidInputError、PermissionDenied。"""
        if not isinstance(query, MeasurementQuery) or not isinstance(query.paging, PageRequest):
            raise InvalidInputError("体测查询格式不正确")
        _positive_id(query.member_id)
        paging = query.paging
        if (
            type(paging.page) is not int or not 1 <= paging.page <= 2**63 - 1
            or type(paging.page_size) is not int
        ):
            raise InvalidInputError("分页参数必须是正整数")
        if not 1 <= paging.page_size <= 100:
            raise InvalidInputError("每页条数必须在 1 至 100 之间")
        if (paging.page - 1) * paging.page_size > 2**63 - 1:
            raise InvalidInputError("分页位置超出数据库可用范围")
        if query.window is not None:
            if not isinstance(query.window, DateWindow):
                raise InvalidInputError("时间窗格式不正确")
            start, end = _timestamp(query.window.start), _timestamp(query.window.end)
            if start >= end:
                raise InvalidInputError("开始时刻必须早于结束时刻")
            query = replace(query, window=DateWindow(start=start, end=end))
        actor = self._auth.verify_actor(session, actor)
        member_id, coach_id = self._scope(actor)
        if member_id is not None and query.member_id != member_id:
            raise PermissionDenied("会员只能查询本人的体测记录")
        return MeasurementRepository(session).list(
            query, scope_member_id=member_id, scope_coach_id=coach_id,
            as_of=datetime.now(timezone.utc),
        )

    def compare(self, session: Session, actor: Actor, before_id: int, after_id: int) -> MeasurementComparison:
        """对比同会员先后两次体测。

        会员只能对比本人记录；教练只能对比授权范围；前台和管理员无权对比明细。
        两条记录使用同一 as_of 和身份范围；任一条不可见抛 NotFoundError，不泄露差值。
        两个编号必须不同，并按 (measured_at, id) 使用与列表相同的稳定先后顺序。
        返回：MeasurementComparison。不修改业务数据。
        异常：InvalidInputError、PermissionDenied、NotFoundError。"""
        _positive_id(before_id)
        _positive_id(after_id)
        if before_id == after_id:
            raise InvalidInputError("请选择两条不同的体测记录")
        actor = self._auth.verify_actor(session, actor)
        member_id, coach_id = self._scope(actor)
        as_of = datetime.now(timezone.utc)
        repo = MeasurementRepository(session)
        before = repo.get(before_id, scope_member_id=member_id, scope_coach_id=coach_id, as_of=as_of)
        after = repo.get(after_id, scope_member_id=member_id, scope_coach_id=coach_id, as_of=as_of)
        if before is None or after is None:
            raise NotFoundError("体测记录不存在或不可见")
        if before.member_id != after.member_id:
            raise InvalidInputError("只能对比同一会员的体测记录")
        if (before.measured_at, before.id) >= (after.measured_at, after.id):
            raise InvalidInputError("体测记录必须按测量时刻和编号从早到晚选择")
        return MeasurementComparison(
            before=before, after=after,
            height_delta_cm=after.height_cm - before.height_cm,
            weight_delta_kg=after.weight_kg - before.weight_kg,
            body_fat_delta_pct=None if before.body_fat_pct is None or after.body_fat_pct is None
            else after.body_fat_pct - before.body_fat_pct,
        )

    @staticmethod
    def _scope(actor: Actor) -> tuple[int | None, int | None]:
        if actor.role == "member" and actor.member_id is not None:
            return actor.member_id, None
        if actor.role == "coach" and actor.coach_id is not None:
            return None, actor.coach_id
        raise PermissionDenied("当前身份不能读取个人体测记录")
