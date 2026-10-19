"""收款查询、报表和 CSV 导出业务服务。"""
from __future__ import annotations
import csv, io
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from src.db.payment_repo import PaymentRepository
from src.db.report_repo import ReportRepository
from src.errors import InvalidInputError, NotFoundError, PermissionDenied, StorageError
from src.models.contracts import (Actor, CoachStatsView, CsvExport, DateWindow, MembershipStats, Page, PageRequest, PaymentQuery, PaymentView, RevenueView, SessionQuery, SessionStatsView)
from src.services.auth_service import AuthService

class ReportService:
    def __init__(self, session_factory: Callable, auth: AuthService, *, timezone_name: str) -> None:
        try: self.zone=ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError,ValueError) as exc: raise ValueError('门店时区配置无效') from exc
        self.session_factory=session_factory; self.auth=auth

    @staticmethod
    def _verify_actor(session, actor: Actor) -> None:
        row=session.execute(text('SELECT role,is_active FROM accounts WHERE id=:id'),{'id':actor.account_id}).mappings().first()
        if not row or not row['is_active'] or row['role']!=actor.role: raise PermissionDenied('当前登录身份已失效，请重新登录')
        if actor.role=='member': raise PermissionDenied('会员不能访问收款与经营报表')
        if actor.role=='coach': raise PermissionDenied('教练不能访问收款与经营报表')

    @staticmethod
    def _require(actor: Actor, roles: tuple[str,...]) -> None:
        if actor.role not in roles: raise PermissionDenied('当前角色无权执行此操作')

    @staticmethod
    def _window(window: DateWindow) -> None:
        if window.start.tzinfo is None or window.end.tzinfo is None: raise InvalidInputError('报表时间范围必须包含时区信息')
        if window.start>=window.end: raise InvalidInputError('开始时间必须早于结束时间')

    @staticmethod
    def _paging(pg: PageRequest) -> None:
        if pg.page<1 or not 1<=pg.page_size<=100: raise InvalidInputError('分页参数不合法，每页最多 100 条')

    def get_payment(self, actor: Actor, payment_id: int) -> PaymentView:
        self._require(actor,('admin','receptionist'))
        if payment_id<=0: raise InvalidInputError('收款编号必须为正整数')
        try:
            with self.session_factory() as session, session.begin():
                self._verify_actor(session,actor); item=PaymentRepository(session).get(payment_id)
                if item is None: raise NotFoundError('收款记录不存在')
                return item
        except (InvalidInputError,NotFoundError,PermissionDenied): raise
        except SQLAlchemyError as exc: raise StorageError('查询收款详情失败') from exc

    def list_payments(self, actor: Actor, query: PaymentQuery) -> Page[PaymentView]:
        self._require(actor,('admin','receptionist')); self._paging(query.paging)
        if query.window: self._window(query.window)
        if query.member_id is not None and query.member_id<=0: raise InvalidInputError('会员编号必须为正整数')
        if query.method is not None and query.method not in ('cash','card','transfer'): raise InvalidInputError('收款方式不合法')
        try:
            with self.session_factory() as session, session.begin(): self._verify_actor(session,actor); return PaymentRepository(session).list(query)
        except (InvalidInputError,PermissionDenied,ValueError): raise
        except SQLAlchemyError as exc: raise StorageError('查询收款流水失败') from exc

    def revenue(self, actor: Actor, window: DateWindow) -> RevenueView:
        self._require(actor,('admin',)); self._window(window)
        try:
            with self.session_factory() as session, session.begin(): self._verify_actor(session,actor); return ReportRepository(session).revenue(window)
        except (InvalidInputError,PermissionDenied): raise
        except SQLAlchemyError as exc: raise StorageError('生成营收报表失败') from exc

    def membership_stats(self, actor: Actor) -> MembershipStats:
        self._require(actor,('admin',)); now=datetime.now(timezone.utc); business_date=now.astimezone(self.zone).date()
        try:
            with self.session_factory() as session, session.begin(): self._verify_actor(session,actor); return ReportRepository(session).membership_stats(now.replace(tzinfo=None),business_date=business_date)
        except PermissionDenied: raise
        except SQLAlchemyError as exc: raise StorageError('生成会员卡统计失败') from exc

    def session_stats(self, actor: Actor, query: SessionQuery) -> Page[SessionStatsView]:
        self._require(actor,('admin',)); self._paging(query.paging)
        if query.window: self._window(query.window)
        try:
            with self.session_factory() as session, session.begin(): self._verify_actor(session,actor); return ReportRepository(session).session_stats(query)
        except (InvalidInputError,PermissionDenied,ValueError): raise
        except SQLAlchemyError as exc: raise StorageError('生成课次统计失败') from exc

    def coach_stats(self, actor: Actor, window: DateWindow, paging: PageRequest) -> Page[CoachStatsView]:
        self._require(actor,('admin',)); self._window(window); self._paging(paging)
        try:
            with self.session_factory() as session, session.begin(): self._verify_actor(session,actor); return ReportRepository(session).coach_stats(window,paging)
        except (InvalidInputError,PermissionDenied,ValueError): raise
        except SQLAlchemyError as exc: raise StorageError('生成教练统计失败') from exc

    @staticmethod
    def _csv(filename: str, headers: list[str], rows: list[list[object]]) -> CsvExport:
        stream=io.StringIO(newline=''); writer=csv.writer(stream,lineterminator='\r\n'); writer.writerow(headers)
        for row in rows:
            safe=[]
            for value in row:
                if value is None: safe.append(''); continue
                if isinstance(value,datetime): value=value.isoformat(timespec='microseconds')
                elif isinstance(value,Decimal): value=format(value,'f')
                elif isinstance(value,(int,float)): value=str(value)
                else:
                    value=str(value)
                    if value.startswith(('=','+','-','@','\t','\r')): value="'"+value
                safe.append(value)
            writer.writerow(safe)
        return CsvExport(filename=filename,content=('\ufeff'+stream.getvalue()).encode('utf-8'),row_count=len(rows))

    def _all_payments(self, session, query: PaymentQuery) -> list[PaymentView]:
        # 使用同一事务快照，按固定排序逐页读取，不受单页上限影响。
        out=[]; page=1
        while True:
            q=PaymentQuery(window=query.window,member_id=query.member_id,method=query.method,paging=PageRequest(page=page,page_size=100))
            result=PaymentRepository(session).list(q); out.extend(result.items)
            if len(out)>=result.total or not result.items: break
            page+=1
        return out

    def export_payments(self, actor: Actor, query: PaymentQuery) -> CsvExport:
        self._require(actor,('admin',));
        if query.window: self._window(query.window)
        if query.member_id is not None and query.member_id<=0: raise InvalidInputError('会员编号必须为正整数')
        try:
            with self.session_factory() as session, session.begin():
                self._verify_actor(session,actor); items=self._all_payments(session,query)
                rows=[[x.id,x.membership_id,x.member_id,f'{x.amount:.2f}',x.method,x.paid_at,x.operator_id] for x in items]
            return self._csv(f'payments_{datetime.now(self.zone):%Y%m%d}.csv',['id','membership_id','member_id','amount','method','paid_at','operator_id'],rows)
        except (InvalidInputError,PermissionDenied): raise
        except SQLAlchemyError as exc: raise StorageError('导出收款流水失败') from exc

    def export_revenue(self, actor: Actor, window: DateWindow) -> CsvExport:
        result=self.revenue(actor,window)
        return self._csv(f'revenue_{datetime.now(self.zone):%Y%m%d}.csv',['start','end','payment_count','total_amount'],[[window.start,window.end,result.payment_count,f'{result.total_amount:.2f}']])

    def export_memberships(self, actor: Actor) -> CsvExport:
        result=self.membership_stats(actor)
        row=[result.as_of,result.active_members,result.inactive_members,result.valid_cards,result.expired_cards,result.future_cards,result.void_cards,result.exhausted_cards]
        return self._csv(f'memberships_{datetime.now(self.zone):%Y%m%d}.csv',['as_of','active_members','inactive_members','valid_cards','expired_cards','future_cards','void_cards','exhausted_cards'],[row])

    def export_sessions(self, actor: Actor, query: SessionQuery) -> CsvExport:
        self._require(actor,('admin',)); self._paging(query.paging)
        if query.window: self._window(query.window)
        try:
            with self.session_factory() as session, session.begin():
                self._verify_actor(session,actor); rows=[]; page=1
                while True:
                    q=SessionQuery(window=query.window,kind=query.kind,coach_id=query.coach_id,room_id=query.room_id,status=query.status,paging=PageRequest(page=page,page_size=100))
                    result=ReportRepository(session).session_stats(q); rows.extend(result.items)
                    if len(rows)>=result.total or not result.items: break
                    page+=1
            data=[[x.session_id,x.starts_at,x.reserved_count,x.checked_in_count,x.completed_count,x.no_show_count,x.cancelled_count,x.attendance_rate] for x in rows]
            return self._csv(f'sessions_{datetime.now(self.zone):%Y%m%d}.csv',['session_id','starts_at','reserved_count','checked_in_count','completed_count','no_show_count','cancelled_count','attendance_rate'],data)
        except (InvalidInputError,PermissionDenied,ValueError): raise
        except SQLAlchemyError as exc: raise StorageError('导出课次统计失败') from exc

    def export_coaches(self, actor: Actor, window: DateWindow) -> CsvExport:
        self._require(actor,('admin',)); self._window(window)
        try:
            with self.session_factory() as session, session.begin():
                self._verify_actor(session,actor); rows=[]; page=1
                while True:
                    result=ReportRepository(session).coach_stats(window,PageRequest(page=page,page_size=100)); rows.extend(result.items)
                    if len(rows)>=result.total or not result.items: break
                    page+=1
            data=[[x.coach_id,x.coach_name,x.completed_sessions,x.attended_members] for x in rows]
            return self._csv(f'coaches_{datetime.now(self.zone):%Y%m%d}.csv',['coach_id','coach_name','completed_sessions','attended_members'],data)
        except (InvalidInputError,PermissionDenied,ValueError): raise
        except SQLAlchemyError as exc: raise StorageError('导出教练统计失败') from exc
