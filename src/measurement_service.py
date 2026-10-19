"""体测业务服务：权限、业务校验和事务边界。"""
from __future__ import annotations
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from src.db.measurement_repo import MeasurementRepository
from src.errors import InvalidInputError, NotFoundError, PermissionDenied, StorageError
from src.models.contracts import Actor, MeasurementComparison, MeasurementInput, MeasurementQuery, MeasurementView, Page
from src.services.auth_service import AuthService
if TYPE_CHECKING:
    from sqlalchemy.orm import Session

class MeasurementService:
    def __init__(self, session_factory: Callable[[], "Session"], auth: AuthService) -> None:
        self.session_factory=session_factory; self.auth=auth

    @staticmethod
    def _verify_actor(session, actor: Actor) -> None:
        row=session.execute(text("SELECT id,role,is_active FROM accounts WHERE id=:id"),{'id':actor.account_id}).mappings().first()
        if not row or not row['is_active'] or row['role']!=actor.role:
            raise PermissionDenied('当前登录身份已失效，请重新登录')
        if actor.role=='member':
            linked=session.execute(text('SELECT id FROM members WHERE id=:pid AND account_id=:aid AND is_active=1'),{'pid':actor.member_id,'aid':actor.account_id}).first() if actor.member_id is not None else None
            if not linked: raise PermissionDenied('会员账号关联无效')
        elif actor.role=='coach':
            linked=session.execute(text('SELECT id FROM coaches WHERE id=:pid AND account_id=:aid AND is_active=1'),{'pid':actor.coach_id,'aid':actor.account_id}).first() if actor.coach_id is not None else None
            if not linked: raise PermissionDenied('教练账号关联无效')

    @staticmethod
    def _scope(actor: Actor) -> tuple[int | None,int | None]:
        if actor.role=='member' and actor.member_id is not None: return actor.member_id,None
        if actor.role=='coach' and actor.coach_id is not None: return None,actor.coach_id
        raise PermissionDenied('当前角色不能查看个人体测记录')

    def record(self, actor: Actor, data: MeasurementInput) -> MeasurementView:
        if actor.role!='coach' or actor.coach_id is None: raise PermissionDenied('只有教练可以录入体测记录')
        try:
            h,w=Decimal(str(data.height_cm)),Decimal(str(data.weight_kg))
            bf=None if data.body_fat_pct is None else Decimal(str(data.body_fat_pct))
        except (InvalidOperation,ValueError,TypeError) as exc: raise InvalidInputError('体测数值格式不正确') from exc
        if not h.is_finite() or not Decimal('100')<=h<=Decimal('250'): raise InvalidInputError('身高必须在 100.00–250.00 cm 范围内')
        if not w.is_finite() or not Decimal('30')<=w<=Decimal('150'): raise InvalidInputError('体重必须在 30.00–150.00 kg 范围内')
        if bf is not None and (not bf.is_finite() or not Decimal('0')<=bf<=Decimal('100')): raise InvalidInputError('体脂率必须在 0.00–100.00% 范围内')
        if data.measured_at.tzinfo is None: raise InvalidInputError('测量时间必须包含时区信息')
        try:
            with self.session_factory() as session:
                with session.begin():
                    self._verify_actor(session,actor)
                    member=session.execute(text('SELECT id,is_active FROM members WHERE id=:id FOR UPDATE'),{'id':data.member_id}).mappings().first()
                    if not member or not member['is_active']: raise NotFoundError('会员不存在或未启用')
                    now=datetime.now(timezone.utc)
                    current=session.execute(text("""SELECT 1 FROM bookings b JOIN course_sessions cs ON cs.id=b.session_id WHERE b.member_id=:mid AND cs.coach_id=:cid AND b.status IN ('reserved','checked_in') AND cs.status='scheduled' AND b.booked_at<=:now AND :now<cs.ends_at LIMIT 1"""),{'mid':data.member_id,'cid':actor.coach_id,'now':now.replace(tzinfo=None)}).first()
                    if not current: raise PermissionDenied('没有该会员当前有效的授课预约，不能录入体测')
                    result=MeasurementInput(member_id=data.member_id,measured_at=data.measured_at.astimezone(timezone.utc).replace(tzinfo=None),height_cm=h.quantize(Decimal('.01')),weight_kg=w.quantize(Decimal('.01')),body_fat_pct=None if bf is None else bf.quantize(Decimal('.01')))
                    return MeasurementRepository(session).create(result,actor.coach_id,created_at=now.replace(tzinfo=None))
        except (InvalidInputError,NotFoundError,PermissionDenied): raise
        except SQLAlchemyError as exc: raise StorageError('保存体测记录失败，事务已回滚') from exc

    def get_measurement(self, actor: Actor, measurement_id: int) -> MeasurementView:
        if measurement_id<=0: raise InvalidInputError('体测记录编号必须为正整数')
        try:
            with self.session_factory() as session, session.begin():
                self._verify_actor(session,actor); member_id,coach_id=self._scope(actor); now=datetime.now(timezone.utc).replace(tzinfo=None)
                result=MeasurementRepository(session).get(measurement_id,scope_member_id=member_id,scope_coach_id=coach_id,as_of=now)
                if result is None: raise NotFoundError('体测记录不存在或不可见')
                return result
        except (InvalidInputError,NotFoundError,PermissionDenied): raise
        except SQLAlchemyError as exc: raise StorageError('查询体测记录失败') from exc

    def list_measurements(self, actor: Actor, query: MeasurementQuery) -> Page[MeasurementView]:
        if query.member_id<=0: raise InvalidInputError('会员编号必须为正整数')
        if query.paging.page<1 or not 1<=query.paging.page_size<=100: raise InvalidInputError('分页参数不合法，每页最多 100 条')
        if query.window and query.window.start>=query.window.end: raise InvalidInputError('开始时间必须早于结束时间')
        try:
            with self.session_factory() as session, session.begin():
                self._verify_actor(session,actor); member_id,coach_id=self._scope(actor)
                if member_id is not None and query.member_id!=member_id: raise PermissionDenied('会员只能查询本人的体测记录')
                if coach_id is not None:
                    # 无历史预约授权时返回正常空页，不泄露会员是否存在。
                    has=session.execute(text('SELECT 1 FROM bookings b JOIN course_sessions cs ON cs.id=b.session_id WHERE b.member_id=:mid AND cs.coach_id=:cid LIMIT 1'),{'mid':query.member_id,'cid':coach_id}).first()
                    if not has: return Page(items=[],total=0,page=query.paging.page,page_size=query.paging.page_size)
                return MeasurementRepository(session).list(query,scope_member_id=member_id,scope_coach_id=coach_id,as_of=datetime.now(timezone.utc).replace(tzinfo=None))
        except (InvalidInputError,PermissionDenied): raise
        except SQLAlchemyError as exc: raise StorageError('查询体测历史失败') from exc

    def compare(self, actor: Actor, before_id: int, after_id: int) -> MeasurementComparison:
        if before_id<=0 or after_id<=0: raise InvalidInputError('体测记录编号必须为正整数')
        try:
            with self.session_factory() as session, session.begin():
                self._verify_actor(session,actor); member_id,coach_id=self._scope(actor); now=datetime.now(timezone.utc).replace(tzinfo=None); repo=MeasurementRepository(session)
                before=repo.get(before_id,scope_member_id=member_id,scope_coach_id=coach_id,as_of=now)
                after=repo.get(after_id,scope_member_id=member_id,scope_coach_id=coach_id,as_of=now)
                if before is None or after is None: raise NotFoundError('体测记录不存在或不可见')
                if before.member_id!=after.member_id: raise InvalidInputError('只能对比同一会员的体测记录')
                if before.measured_at>after.measured_at: raise InvalidInputError('前一次体测时间不能晚于后一次')
                fat_delta=None if before.body_fat_pct is None or after.body_fat_pct is None else after.body_fat_pct-before.body_fat_pct
                return MeasurementComparison(before=before,after=after,height_delta_cm=after.height_cm-before.height_cm,weight_delta_kg=after.weight_kg-before.weight_kg,body_fat_delta_pct=fat_delta)
        except (InvalidInputError,NotFoundError,PermissionDenied): raise
        except SQLAlchemyError as exc: raise StorageError('对比体测记录失败') from exc
