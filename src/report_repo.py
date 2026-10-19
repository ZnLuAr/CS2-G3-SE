"""报表查询 Repository。所有查询使用调用方传入的 Session，不提交事务。"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.models.contracts import (CoachStatsView, DateWindow, MembershipStats, Page, PageRequest, RevenueView, SessionQuery, SessionStatsView)

class ReportRepository:
    def __init__(self, session: Session) -> None: self.session=session

    def revenue(self, window: DateWindow) -> RevenueView:
        row=self.session.execute(text("SELECT COUNT(*) AS n, COALESCE(SUM(amount),0.00) AS total FROM payments WHERE paid_at >= :start AND paid_at < :end"),{'start':window.start,'end':window.end}).mappings().one()
        return RevenueView(window=window,payment_count=int(row['n']),total_amount=Decimal(str(row['total'])).quantize(Decimal('0.01')))

    def membership_stats(self, as_of, *, business_date: date) -> MembershipStats:
        members=self.session.execute(text("SELECT SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) active_n,SUM(CASE WHEN is_active=0 THEN 1 ELSE 0 END) inactive_n FROM members")).mappings().one()
        cards=self.session.execute(text("""SELECT SUM(CASE WHEN status='void' THEN 1 ELSE 0 END) void_n,
          SUM(CASE WHEN status<>'void' AND valid_from>:today THEN 1 ELSE 0 END) future_n,
          SUM(CASE WHEN status<>'void' AND kind<>'count' AND valid_from<=:today AND valid_until<=:today THEN 1 ELSE 0 END) expired_n,
          SUM(CASE WHEN status<>'void' AND valid_from<=:today AND (kind='count' AND remaining_accesses=0) THEN 1 ELSE 0 END) exhausted_n,
          SUM(CASE WHEN status<>'void' AND valid_from<=:today AND ((kind='count' AND remaining_accesses>0) OR (kind<>'count' AND valid_until>:today)) THEN 1 ELSE 0 END) valid_n
          FROM memberships"""),{'today':business_date}).mappings().one()
        n=lambda x:int(x or 0)
        return MembershipStats(as_of=as_of,active_members=n(members['active_n']),inactive_members=n(members['inactive_n']),valid_cards=n(cards['valid_n']),expired_cards=n(cards['expired_n']),future_cards=n(cards['future_n']),void_cards=n(cards['void_n']),exhausted_cards=n(cards['exhausted_n']))

    def session_stats(self, query: SessionQuery) -> Page[SessionStatsView]:
        where=[]; p={}
        if query.window:
            if query.window.start>=query.window.end: raise ValueError('开始时间必须早于结束时间')
            where += ['cs.starts_at>=:start_at','cs.starts_at<:end_at']; p.update(start_at=query.window.start,end_at=query.window.end)
        for field,col in [('coach_id','cs.coach_id'),('room_id','cs.room_id'),('status','cs.status'),('kind','cs.kind')]:
            value=getattr(query,field,None)
            if value is not None: where.append(f'{col}=:{field}'); p[field]=value
        clause=(' WHERE '+' AND '.join(where)) if where else ''
        joins=""" FROM course_sessions cs LEFT JOIN bookings b ON b.session_id=cs.id """
        grouped="""SELECT cs.id session_id,cs.starts_at,
          SUM(CASE WHEN b.status='reserved' THEN 1 ELSE 0 END) reserved_n,
          SUM(CASE WHEN b.status='checked_in' THEN 1 ELSE 0 END) checked_n,
          SUM(CASE WHEN b.status='completed' THEN 1 ELSE 0 END) completed_n,
          SUM(CASE WHEN b.status='no_show' THEN 1 ELSE 0 END) no_show_n,
          SUM(CASE WHEN b.status='cancelled' THEN 1 ELSE 0 END) cancelled_n"""+joins+clause+" GROUP BY cs.id,cs.starts_at"
        total=int(self.session.execute(text('SELECT COUNT(*) FROM course_sessions cs'+clause),p).scalar_one())
        pg=query.paging; offset=(pg.page-1)*pg.page_size
        rows=self.session.execute(text(grouped+' ORDER BY cs.starts_at DESC,cs.id DESC LIMIT :lim OFFSET :off'),{**p,'lim':pg.page_size,'off':offset}).mappings().all()
        items=[]
        for r in rows:
            reserved,checked,completed,no_show,cancelled=(int(r[k] or 0) for k in ('reserved_n','checked_n','completed_n','no_show_n','cancelled_n'))
            denominator=reserved+checked+completed+no_show
            rate=None if denominator==0 else (Decimal(checked+completed)/Decimal(denominator)).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)
            items.append(SessionStatsView(session_id=int(r['session_id']),starts_at=r['starts_at'],reserved_count=reserved,checked_in_count=checked,completed_count=completed,no_show_count=no_show,cancelled_count=cancelled,attendance_rate=rate))
        return Page(items=items,total=total,page=pg.page,page_size=pg.page_size)

    def coach_stats(self, window: DateWindow, paging: PageRequest) -> Page[CoachStatsView]:
        if window.start>=window.end: raise ValueError('开始时间必须早于结束时间')
        total=int(self.session.execute(text('SELECT COUNT(*) FROM coaches')).scalar_one())
        sql="""SELECT c.id coach_id,c.name coach_name,
          SUM(CASE WHEN cs.status='completed' THEN 1 ELSE 0 END) completed_n,
          SUM(CASE WHEN cs.status='completed' AND b.checked_in_at IS NOT NULL THEN 1 ELSE 0 END) attended_n
          FROM coaches c LEFT JOIN course_sessions cs ON cs.coach_id=c.id AND cs.starts_at>=:start AND cs.starts_at<:end
          LEFT JOIN bookings b ON b.session_id=cs.id GROUP BY c.id,c.name ORDER BY c.id ASC LIMIT :lim OFFSET :off"""
        rows=self.session.execute(text(sql),{'start':window.start,'end':window.end,'lim':paging.page_size,'off':(paging.page-1)*paging.page_size}).mappings().all()
        return Page(items=[CoachStatsView(coach_id=int(r['coach_id']),coach_name=r['coach_name'],completed_sessions=int(r['completed_n'] or 0),attended_members=int(r['attended_n'] or 0)) for r in rows],total=total,page=paging.page,page_size=paging.page_size)
