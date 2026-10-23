"""使用内存 SQL 数据库验证仓储筛选与聚合，不连接业务库。"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


@pytest.fixture
def report_db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def bind_dates(connection, cursor, statement, parameters, context, executemany):
        """显式绑定日期，避免依赖 Python 3.12 起弃用的 SQLite 默认适配器。"""
        def adapt(value):
            if isinstance(value, datetime):
                return value.isoformat(sep=" ")
            if isinstance(value, date):
                return value.isoformat()
            return value

        if executemany:
            parameters = [tuple(adapt(value) for value in row) for row in parameters]
        else:
            parameters = tuple(adapt(value) for value in parameters)
        return statement, parameters

    definitions = (
        "members (id INTEGER PRIMARY KEY, status TEXT NOT NULL)",
        "sale_orders (id INTEGER PRIMARY KEY, member_id INTEGER, kind TEXT NOT NULL)",
        "payments (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_order_id INTEGER UNIQUE, "
        "member_id INTEGER, amount NUMERIC NOT NULL CHECK (amount > 0), method TEXT, "
        "paid_at DATETIME, operator_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)",
        "gym_cards (id INTEGER PRIMARY KEY, member_id INTEGER, kind TEXT, status TEXT)",
        "duration_gym_cards (gym_card_id INTEGER PRIMARY KEY, valid_from DATE, valid_until DATE)",
        "visit_gym_cards (gym_card_id INTEGER PRIMARY KEY, remaining_entries INTEGER)",
        "lesson_packages (id INTEGER PRIMARY KEY, status TEXT, valid_from DATE, valid_until DATE, "
        "remaining_lessons INTEGER, reserved_lessons INTEGER)",
        "coaches (id INTEGER PRIMARY KEY, name TEXT)",
        "course_sessions (id INTEGER PRIMARY KEY, kind TEXT, coach_id INTEGER, room_id INTEGER, "
        "starts_at DATETIME, ends_at DATETIME, status TEXT)",
        "bookings (id INTEGER PRIMARY KEY, session_id INTEGER, status TEXT)",
    )
    with engine.begin() as connection:
        for definition in definitions:
            connection.exec_driver_sql("CREATE TABLE " + definition)
    with Session(engine) as session:
        yield session
    engine.dispose()
