"""收款数据访问层。调用方负责事务；一个会员卡最多一笔收款由数据库唯一约束保障。"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.errors import ConflictError
from src.models.contracts import Page, PaymentMethod, PaymentQuery, PaymentView

_SELECT = "SELECT id,membership_id,member_id,amount,method,paid_at,operator_id FROM payments"
def _view(r) -> PaymentView:
    return PaymentView(id=int(r['id']), membership_id=int(r['membership_id']), member_id=int(r['member_id']), amount=Decimal(str(r['amount'])), method=r['method'], paid_at=r['paid_at'], operator_id=int(r['operator_id']))

class PaymentRepository:
    """不提交、不处理界面权限；写入与 memberships 创建共用同一个 Session/事务。"""
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, membership_id: int, member_id: int, amount: Decimal, method: PaymentMethod, paid_at: datetime, operator_id: int) -> PaymentView:
        if amount < Decimal('0.00'):
            raise ValueError('收款金额不能为负数')
        try:
            result = self.session.execute(text("INSERT INTO payments (membership_id,member_id,amount,method,paid_at,operator_id,created_at) VALUES (:membership_id,:member_id,:amount,:method,:paid_at,:operator_id,:created_at)"),
                {"membership_id":membership_id,"member_id":member_id,"amount":amount,"method":method,"paid_at":paid_at,"operator_id":operator_id,"created_at":datetime.now(paid_at.tzinfo) if paid_at.tzinfo else datetime.utcnow()})
        except IntegrityError as exc:
            raise ConflictError('该会员卡已存在收款记录，不能重复收费') from exc
        row = self.session.execute(text(f"{_SELECT} WHERE id=:id"), {"id":result.lastrowid}).mappings().one()
        return _view(row)

    def get(self, payment_id: int) -> PaymentView | None:
        row = self.session.execute(text(f"{_SELECT} WHERE id=:id"), {"id":payment_id}).mappings().first()
        return _view(row) if row else None

    def get_by_membership(self, membership_id: int) -> PaymentView | None:
        row = self.session.execute(text(f"{_SELECT} WHERE membership_id=:id"), {"id":membership_id}).mappings().first()
        return _view(row) if row else None

    def list(self, query: PaymentQuery) -> Page[PaymentView]:
        p = {}; conditions=[]
        if query.window:
            if query.window.start >= query.window.end: raise ValueError('开始时间必须早于结束时间')
            conditions += ['paid_at >= :start_at','paid_at < :end_at']; p.update(start_at=query.window.start,end_at=query.window.end)
        if query.member_id is not None: conditions.append('member_id=:member_id'); p['member_id']=query.member_id
        if query.method is not None: conditions.append('method=:method'); p['method']=query.method
        where = (' WHERE ' + ' AND '.join(conditions)) if conditions else ''
        pg=query.paging; offset=(pg.page-1)*pg.page_size
        total=int(self.session.execute(text(f'SELECT COUNT(*) FROM payments{where}'),p).scalar_one())
        rows=self.session.execute(text(f'{_SELECT}{where} ORDER BY paid_at DESC,id DESC LIMIT :lim OFFSET :off'),{**p,'lim':pg.page_size,'off':offset}).mappings().all()
        return Page(items=[_view(r) for r in rows],total=total,page=pg.page,page_size=pg.page_size)
