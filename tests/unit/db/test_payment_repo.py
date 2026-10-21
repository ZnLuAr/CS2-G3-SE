"""PAY-01/PAY-02：实际 SQL 的写入、回滚、筛选与金额精度。"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from src.db.payment_repo import PaymentRepository
from src.errors.storage import StorageError
from src.models.contracts import DateWindow, PageRequest, PaymentQuery
from src.models.payment import Payment


START = datetime(2026, 10, 20, tzinfo=timezone.utc)
WINDOW = DateWindow(start=START, end=START + timedelta(days=1))


def add_payment(repo, order_id, *, member_id=1, amount="12.30", method="cash", paid_at=START):
    return repo.create(
        sale_order_id=order_id, member_id=member_id, amount=Decimal(amount),
        method=method, paid_at=paid_at, operator_id=7,
    )


def test_create_returns_model_in_utc_and_respects_caller_rollback(report_db):
    repo = PaymentRepository(report_db)
    paid_at = START.astimezone(timezone(timedelta(hours=8)))
    payment = add_payment(repo, 1, paid_at=paid_at)
    assert isinstance(payment, Payment)
    assert payment.amount == Decimal("12.30")
    assert payment.paid_at == START
    assert payment.paid_at.tzinfo == timezone.utc
    assert payment.created_at.tzinfo == timezone.utc
    assert repo.get_by_order(1) == payment
    report_db.rollback()
    assert repo.get(payment.id) is None
    assert repo.get_by_order(1) is None


def test_duplicate_payment_raises_storage_error_without_committing(report_db):
    repo = PaymentRepository(report_db)
    add_payment(repo, 1)
    with pytest.raises(StorageError, match="保存收款记录失败"):
        add_payment(repo, 1)
    report_db.rollback()
    assert report_db.execute(text("SELECT COUNT(*) FROM payments")).scalar_one() == 0


def test_filters_are_combined_half_open_and_stable_across_pages(report_db):
    repo = PaymentRepository(report_db)
    first = add_payment(repo, 1)
    second = add_payment(repo, 2)
    add_payment(repo, 3, member_id=2)
    add_payment(repo, 4, method="card")
    add_payment(repo, 5, paid_at=WINDOW.end)
    add_payment(repo, 6, paid_at=START - timedelta(microseconds=1))
    query = PaymentQuery(
        window=WINDOW, member_id=1, method="cash", paging=PageRequest(page_size=1),
    )
    rows, total = repo.list(query)
    assert total == 2
    assert [item.id for item in rows] == [second.id]
    rows, total = repo.list(PaymentQuery(
        window=WINDOW, member_id=1, method="cash", paging=PageRequest(page=2, page_size=1),
    ))
    assert total == 2
    assert [item.id for item in rows] == [first.id]


def test_keyset_batches_preserve_filters_and_ignore_ui_page(report_db):
    repo = PaymentRepository(report_db)
    first = add_payment(repo, 1)
    add_payment(repo, 2, method="card")
    last = add_payment(repo, 3)
    add_payment(repo, 4, paid_at=WINDOW.end)
    query = PaymentQuery(window=WINDOW, method="cash", paging=PageRequest(page=99, page_size=1))
    batch = repo.list_batch(query, limit=1)
    assert [row.id for row in batch] == [first.id]
    assert [row.id for row in repo.list_batch(query, after_id=first.id, limit=1)] == [last.id]
    assert repo.list_batch(query, after_id=last.id) == []


def test_aggregate_uses_exact_decimal_and_method(report_db):
    repo = PaymentRepository(report_db)
    add_payment(repo, 1, amount="0.10")
    add_payment(repo, 2, amount="0.20")
    add_payment(repo, 3, amount="10.00", method="card")
    add_payment(repo, 4, amount="99.00", paid_at=WINDOW.end)
    totals = repo.aggregate(WINDOW, "cash")
    assert totals.payment_count == 2
    assert totals.total_amount == Decimal("0.30")
    assert isinstance(totals.total_amount, Decimal)
    assert repo.aggregate(WINDOW, None).total_amount == Decimal("10.30")
    assert repo.aggregate(WINDOW, "transfer").total_amount == Decimal("0.00")


def test_query_values_are_bound_as_data(report_db):
    repo = PaymentRepository(report_db)
    add_payment(repo, 1)
    rows, total = repo.list(PaymentQuery(method="cash' OR 1=1 --"))
    assert rows == []
    assert total == 0
