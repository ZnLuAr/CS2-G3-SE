"""收款持久化与筛选；事务由调用方管理。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Numeric, bindparam, text
from sqlalchemy.exc import SQLAlchemyError

from src.errors.storage import StorageError
from src.models.contracts import DateWindow, PaymentMethod, PaymentQuery, PaymentTotals
from src.models.payment import Payment

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_COLUMNS = (
    "id, sale_order_id, member_id, amount, method, paid_at, operator_id, created_at"
)


def _utc_input(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_output(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _payment(row: Any) -> Payment:
    return Payment(
        id=row["id"], sale_order_id=row["sale_order_id"],
        member_id=row["member_id"], amount=Decimal(str(row["amount"])).quantize(
            Decimal("0.01")
        ), method=row["method"], paid_at=_utc_output(row["paid_at"]),
        operator_id=row["operator_id"], created_at=_utc_output(row["created_at"]),
    )


def _filters(query: PaymentQuery) -> tuple[str, dict[str, Any]]:
    clauses = ["1 = 1"]
    params: dict[str, Any] = {}
    if query.window is not None:
        clauses.extend(("paid_at >= :window_start", "paid_at < :window_end"))
        params.update(
            window_start=_utc_input(query.window.start),
            window_end=_utc_input(query.window.end),
        )
    if query.member_id is not None:
        clauses.append("member_id = :member_id")
        params["member_id"] = query.member_id
    if query.method is not None:
        clauses.append("method = :method")
        params["method"] = query.method
    return " AND ".join(clauses), params


class PaymentRepository:
    """收款数据访问；只使用传入会话，不提交、不输出提示。

    返回领域模型 Payment（非 View）；查询未命中返回 None，由服务转换异常。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def _rows(self, sql: str, params: dict[str, Any]) -> list[Any]:
        try:
            result = self._session.execute(text(sql), params)
            try:
                return result.mappings().all()
            finally:
                result.close()
        except SQLAlchemyError as exc:
            raise StorageError("读取收款记录失败") from exc

    def create(
        self,
        sale_order_id: int,
        member_id: int,
        amount: Decimal,
        method: PaymentMethod,
        paid_at: datetime,
        operator_id: int,
    ) -> Payment:
        """保存模拟实收并取得编号，与销售共用事务。"""
        statement = text(
            "INSERT INTO payments "
            "(sale_order_id, member_id, amount, method, paid_at, operator_id) "
            "VALUES (:sale_order_id, :member_id, :amount, :method, :paid_at, :operator_id)"
        ).bindparams(bindparam("amount", type_=Numeric(10, 2)))
        try:
            result = self._session.execute(statement, {
                "sale_order_id": sale_order_id, "member_id": member_id,
                "amount": amount, "method": method, "paid_at": _utc_input(paid_at),
                "operator_id": operator_id,
            })
            try:
                payment_id = result.lastrowid
            finally:
                result.close()
        except SQLAlchemyError as exc:
            raise StorageError("保存收款记录失败") from exc
        payment = self.get(payment_id)
        if payment is None:
            raise StorageError("保存后未能读取收款记录")
        return payment

    def get_by_order(self, sale_order_id: int) -> Payment | None:
        """按销售订单读取唯一收款。"""
        rows = self._rows(
            f"SELECT {_COLUMNS} FROM payments WHERE sale_order_id = :order_id",
            {"order_id": sale_order_id},
        )
        return _payment(rows[0]) if rows else None

    def get(self, payment_id: int) -> Payment | None:
        """按收款编号读取记录；不存在返回 None，由服务转换异常。"""
        rows = self._rows(
            f"SELECT {_COLUMNS} FROM payments WHERE id = :payment_id",
            {"payment_id": payment_id},
        )
        return _payment(rows[0]) if rows else None

    def list(self, query: PaymentQuery) -> tuple[list[Payment], int]:
        """按时间、会员和方式筛选，再按 paid_at、id 降序稳定分页，返回（当页记录, 总数）。"""
        where, params = _filters(query)
        total = self._rows(
            f"SELECT COUNT(*) AS total FROM payments WHERE {where}", params,
        )[0]["total"]
        rows = self._rows(
            f"SELECT {_COLUMNS} FROM payments WHERE {where} "
            "ORDER BY paid_at DESC, id DESC LIMIT :limit OFFSET :offset",
            {**params, "limit": query.paging.page_size,
             "offset": (query.paging.page - 1) * query.paging.page_size},
        )
        return [_payment(row) for row in rows], int(total)

    def aggregate(self, window: DateWindow, method: PaymentMethod | None) -> PaymentTotals:
        """按窗口和收款方式汇总收入总额。"""
        where, params = _filters(PaymentQuery(window=window, method=method))
        row = self._rows(
            "SELECT COUNT(*) AS payment_count, COALESCE(SUM(amount), 0) AS total_amount "
            f"FROM payments WHERE {where}", params,
        )[0]
        return PaymentTotals(
            payment_count=int(row["payment_count"]),
            total_amount=Decimal(str(row["total_amount"])).quantize(Decimal("0.01")),
        )

    def list_batch(
        self, query: PaymentQuery, *, after_id: int = 0, limit: int = 500,
    ) -> list[Payment]:
        """在当前快照按主键游标导出一批记录，保留列表全部筛选。"""
        where, params = _filters(query)
        rows = self._rows(
            f"SELECT {_COLUMNS} FROM payments WHERE {where} AND id > :after_id "
            "ORDER BY id ASC LIMIT :limit",
            {**params, "after_id": after_id, "limit": limit},
        )
        return [_payment(row) for row in rows]
