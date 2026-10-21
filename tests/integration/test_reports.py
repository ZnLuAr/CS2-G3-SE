"""PAY-01/02/04、REPORT-01/05：真实 v4 MySQL 的收款、原子回滚和导出快照。"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import LogConfig
from src.db.connection import transaction
from src.db.payment_repo import PaymentRepository
from src.errors import PermissionDenied, StorageError
from src.logic.report_logic import ReportLogic
from src.models.contracts import Actor, DateWindow, PageRequest, PaymentQuery
from src.services.auth_service import AuthService
from src.services.report_service import ReportService


START = datetime(2026, 10, 20, tzinfo=timezone.utc)
WINDOW = DateWindow(start=START, end=START + timedelta(days=1))
ADMIN = Actor(account_id=1, role="admin", member_id=None, coach_id=None)
RECEPTIONIST = Actor(account_id=2, role="receptionist", member_id=None, coach_id=None)


def _seed(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO accounts (id,username,password_hash,role) VALUES "
            "(1,'report_admin','test-unused','admin'),"
            "(2,'report_receptionist','test-unused','receptionist')"
        ))
        connection.execute(text("INSERT INTO members (id,name) VALUES (10,'Report member')"))


def _order(session, order_id, *, kind="gym_card", amount=Decimal("100.10"), at=START, operator_id=2):
    session.execute(text(
        "INSERT INTO sale_orders (id,member_id,kind,total_amount,sold_at,operator_id) "
        "VALUES (:id,10,:kind,:amount,:at,:operator_id)"
    ), {"id": order_id, "kind": kind, "amount": amount,
        "at": at.astimezone(timezone.utc).replace(tzinfo=None), "operator_id": operator_id})


def _paid(session, order_id, *, kind="gym_card", amount=Decimal("100.10"), at=START, method="cash"):
    _order(session, order_id, kind=kind, amount=amount, at=at)
    return PaymentRepository(session).create(order_id, 10, amount, method, at, 2)


def _logic(engine):
    return ReportLogic(
        lambda: Session(engine),
        ReportService(AuthService(log_config=LogConfig()), timezone_name="Asia/Shanghai"),
    )


def _rows(export):
    return list(csv.DictReader(io.StringIO(export.content.decode("utf-8-sig"))))


def test_payment_and_order_share_rollback(initialized_mysql_database):
    engine = initialized_mysql_database
    _seed(engine)
    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="simulate downstream failure"):
            with transaction(session):
                _paid(session, 1)
                raise RuntimeError("simulate downstream failure")
    with Session(engine) as session:
        assert session.execute(text("SELECT COUNT(*) FROM sale_orders")).scalar_one() == 0
        assert session.execute(text("SELECT COUNT(*) FROM payments")).scalar_one() == 0


def test_one_payment_per_order_is_enforced_by_mysql(initialized_mysql_database):
    engine = initialized_mysql_database
    _seed(engine)
    with Session(engine) as session, transaction(session):
        original = _paid(session, 1)
    with Session(engine) as session:
        with pytest.raises(StorageError):
            with transaction(session):
                PaymentRepository(session).create(1, 10, Decimal("100.10"), "card", START, 2)
    with Session(engine) as session:
        recorded = PaymentRepository(session).get_by_order(1)
        assert recorded.id == original.id and recorded.method == "cash"
        assert session.execute(text("SELECT COUNT(*) FROM payments")).scalar_one() == 1


def test_revenue_half_open_window_and_csv_ignores_ui_page(initialized_mysql_database, monkeypatch):
    engine = initialized_mysql_database
    _seed(engine)
    with Session(engine) as session, transaction(session):
        first = _paid(session, 1, amount=Decimal("0.20"), at=START)
        second = _paid(session, 2, kind="lesson_package", amount=Decimal("100.10"), at=START + timedelta(hours=1))
        _paid(session, 3, amount=Decimal("800.00"), at=WINDOW.end)
    logic = _logic(engine)
    summary = logic.revenue(ADMIN, WINDOW)
    assert summary.total_payment_count == 2
    assert summary.total_amount == Decimal("100.30")
    assert [(item.sale_kind, item.total_amount) for item in summary.breakdowns] == [
        ("gym_card", Decimal("0.20")), ("lesson_package", Decimal("100.10")),
    ]
    monkeypatch.setattr("src.services.report_service._BATCH_SIZE", 1)
    query = PaymentQuery(window=WINDOW, member_id=10, method="cash", paging=PageRequest(page=99, page_size=1))
    exported = logic.export_payments(ADMIN, query)
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert exported.row_count == 2
    rows = _rows(exported)
    assert [int(row["id"]) for row in rows] == [first.id, second.id]
    assert [row["amount"] for row in rows] == ["0.20", "100.10"]
    assert rows[0]["paid_at"].endswith("+00:00")
    # 前台有流水查询权限，但导出仍只允许管理员。
    assert logic.list_payments(RECEPTIONIST, PaymentQuery(window=WINDOW)).total == 2
    with pytest.raises(PermissionDenied):
        logic.export_payments(RECEPTIONIST, query)


def test_payment_export_keeps_one_repeatable_read_snapshot(initialized_mysql_database, monkeypatch):
    engine = initialized_mysql_database
    _seed(engine)
    with Session(engine) as session, transaction(session):
        first = _paid(session, 1)
        second = _paid(session, 2)
    original_batch = PaymentRepository.list_batch
    inserted = []

    def batch_with_concurrent_insert(repository, query, *, after_id=0, limit=500):
        batch = original_batch(repository, query, after_id=after_id, limit=limit)
        if not inserted:
            # 导出锁的是管理员账号；另一个前台账号写入一笔付款，避免共享外键锁等待。
            with Session(engine) as writer, transaction(writer):
                inserted.append(_paid(writer, 3).id)
        return batch

    monkeypatch.setattr(PaymentRepository, "list_batch", batch_with_concurrent_insert)
    monkeypatch.setattr("src.services.report_service._BATCH_SIZE", 1)
    logic = _logic(engine)
    exported = logic.export_payments(ADMIN, PaymentQuery(window=WINDOW))
    assert [int(row["id"]) for row in _rows(exported)] == [first.id, second.id]
    assert logic.list_payments(ADMIN, PaymentQuery(window=WINDOW)).total == 3
