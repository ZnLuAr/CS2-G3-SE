"""MEASURE-01/02/03：在 v4 MySQL 结构验证写入、授权截止和会员行锁。"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.config import LogConfig
from src.db.measurement_repo import MeasurementRepository
from src.db.member_repo import MemberRepository
from src.errors import NotFoundError, PermissionDenied
from src.logic.measurement_logic import MeasurementLogic
from src.models.contracts import Actor, MeasurementInput, MeasurementQuery
from src.services.auth_service import AuthService
from src.services.measurement_service import MeasurementService


def _seed(engine):
    now = datetime.now(timezone.utc)
    params = {
        "now": now.replace(tzinfo=None), "start": (now - timedelta(minutes=30)).replace(tzinfo=None),
        "end": (now + timedelta(minutes=30)).replace(tzinfo=None),
    }
    statements = [
        "INSERT INTO accounts (id,username,password_hash,role) VALUES (1,'measurement_coach','test-unused','coach')",
        "INSERT INTO members (id,name) VALUES (10,'Measurement member'),(11,'Other member')",
        "INSERT INTO coaches (id,name) VALUES (20,'Measurement coach')",
        "INSERT INTO coach_account_links (account_id,coach_id,linked_at,linked_by) VALUES (1,20,:now,1)",
        "INSERT INTO courses (id,name,duration_minutes) VALUES (1,'Private session',60)",
        "INSERT INTO rooms (id,name) VALUES (1,'Test room')",
        "INSERT INTO course_sessions (id,course_id,coach_id,room_id,course_name,kind,starts_at,ends_at,capacity) "
        "VALUES (30,1,20,1,'Private session','private',:start,:end,1)",
        "INSERT INTO lesson_package_products (id,name,price,lesson_credits) VALUES (1,'Test lessons',100.00,10)",
        "INSERT INTO sale_orders (id,member_id,kind,total_amount,sold_at,operator_id) "
        "VALUES (1,10,'lesson_package',100.00,:now,1)",
        "INSERT INTO sale_items (id,sale_order_id,member_id,kind,product_name,quantity,unit_price,line_amount) "
        "VALUES (1,1,10,'lesson_package','Test lessons',1,100.00,100.00)",
        "INSERT INTO lesson_package_sale_items (sale_item_id,member_id,lesson_package_product_id) VALUES (1,10,1)",
        "INSERT INTO lesson_packages (id,member_id,product_id,purchase_sale_item_id,name,total_lessons,"
        "remaining_lessons,reserved_lessons,valid_from) VALUES (1,10,1,1,'Test lessons',10,10,1,'2026-01-01')",
        "INSERT INTO bookings (id,member_id,session_id,lesson_package_id,booked_at) VALUES (40,10,30,1,:start)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement), params)
    return now


def test_record_and_cancelled_cutoff_with_real_auth(initialized_mysql_database):
    engine = initialized_mysql_database
    now = _seed(engine)
    actor = Actor(account_id=1, role="coach", member_id=None, coach_id=20)
    logic = MeasurementLogic(
        lambda: Session(engine), MeasurementService(AuthService(log_config=LogConfig())),
    )
    data = MeasurementInput(
        member_id=10, measured_at=now.astimezone(timezone(timedelta(hours=8))),
        height_cm=Decimal("170.05"), weight_kg=Decimal("60.15"), body_fat_pct=None,
    )
    recorded = logic.record(actor, data)
    assert recorded.measured_at == now
    assert logic.get_measurement(actor, recorded.id).weight_kg == Decimal("60.15")
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE bookings SET status='cancelled',closed_at=:cutoff WHERE id=40"
        ), {"cutoff": recorded.created_at.replace(tzinfo=None)})
    with Session(engine) as session:
        hidden = MeasurementRepository(session).create(
            data, 20, created_at=recorded.created_at + timedelta(microseconds=1),
        )
        session.commit()
    page = logic.list_measurements(actor, MeasurementQuery(member_id=10))
    assert page.total == 1 and [item.id for item in page.items] == [recorded.id]
    with pytest.raises(NotFoundError):
        logic.get_measurement(actor, hidden.id)
    with pytest.raises(PermissionDenied):
        logic.record(actor, data)
    with Session(engine) as session:
        assert session.execute(text("SELECT COUNT(*) FROM body_measurements")).scalar_one() == 2


def test_member_lock_blocks_another_transaction(initialized_mysql_database):
    engine = initialized_mysql_database
    _seed(engine)
    with Session(engine) as first, Session(engine) as second:
        assert MemberRepository(first).lock(10).id == 10
        second.execute(text("SET SESSION innodb_lock_wait_timeout=1"))
        with pytest.raises(OperationalError) as caught:
            MemberRepository(second).lock(10)
        assert caught.value.orig.args[0] == 1205
        second.rollback()
        first.rollback()
        assert MemberRepository(second).lock(10).id == 10
