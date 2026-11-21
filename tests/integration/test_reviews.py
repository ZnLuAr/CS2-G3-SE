"""REVIEW-01/02：在 MySQL v4 结构验证持久化、授权分页、锁和并发。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from threading import Barrier

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.config import LogConfig
from src.db.booking_repo import BookingRepository
from src.db.review_repo import ReviewRepository
from src.errors import AuthenticationError, ConflictError, NotFoundError, StorageError
from src.logic.review_logic import ReviewLogic
from src.models.contracts import Actor, PageRequest, ReviewInput, ReviewQuery
from src.services.auth_service import AuthService
from src.services.review_service import ReviewService


MEMBER = Actor(account_id=1, role="member", member_id=10, coach_id=None)
OTHER_MEMBER = Actor(account_id=2, role="member", member_id=11, coach_id=None)
COACH = Actor(account_id=3, role="coach", member_id=None, coach_id=20)
OTHER_COACH = Actor(account_id=4, role="coach", member_id=None, coach_id=21)
ADMIN = Actor(account_id=5, role="admin", member_id=None, coach_id=None)


@pytest.fixture
def review_logic(initialized_mysql_database):
    engine = initialized_mysql_database
    statements = [
        """INSERT INTO accounts (id, username, password_hash, role) VALUES
           (1, 'review_member1', 'unused', 'member'), (2, 'review_member2', 'unused', 'member'),
           (3, 'review_coach1', 'unused', 'coach'), (4, 'review_coach2', 'unused', 'coach'),
           (5, 'review_admin', 'unused', 'admin')""",
        "INSERT INTO members (id, name) VALUES (10, 'Member 1'), (11, 'Member 2')",
        "INSERT INTO coaches (id, name) VALUES (20, 'Coach 1'), (21, 'Coach 2')",
        """INSERT INTO member_account_links (account_id, member_id, linked_at, linked_by)
           VALUES (1, 10, :booked, 5), (2, 11, :booked, 5)""",
        """INSERT INTO coach_account_links (account_id, coach_id, linked_at, linked_by)
           VALUES (3, 20, :booked, 5), (4, 21, :booked, 5)""",
        "INSERT INTO courses (id, name, duration_minutes) VALUES (1, 'Private review session', 60)",
        "INSERT INTO rooms (id, name) VALUES (1, 'Review room')",
        """INSERT INTO course_sessions
           (id, course_id, coach_id, room_id, course_name, kind, starts_at, ends_at, capacity, status)
           VALUES
           (30, 1, 20, 1, 'Private review session', 'private', :start30, :end30, 1, 'completed'),
           (31, 1, 21, 1, 'Private review session', 'private', :start31, :end31, 1, 'completed'),
           (32, 1, 20, 1, 'Private review session', 'private', :start32, :end32, 1, 'completed'),
           (33, 1, 21, 1, 'Private review session', 'private', :start33, :end33, 1, 'completed'),
           (34, 1, 21, 1, 'Private review session', 'private', :start34, :end34, 1, 'scheduled')""",
        """INSERT INTO lesson_package_products (id, name, price, lesson_credits)
           VALUES (1, 'Review lessons', 100.00, 10)""",
        """INSERT INTO sale_orders (id, member_id, kind, total_amount, sold_at, operator_id)
           VALUES (1, 10, 'lesson_package', 100.00, :booked, 5),
                  (2, 11, 'lesson_package', 100.00, :booked, 5)""",
        """INSERT INTO sale_items
           (id, sale_order_id, member_id, kind, product_name, quantity, unit_price, line_amount)
           VALUES (1, 1, 10, 'lesson_package', 'Review lessons', 1, 100.00, 100.00),
                  (2, 2, 11, 'lesson_package', 'Review lessons', 1, 100.00, 100.00)""",
        """INSERT INTO lesson_package_sale_items (sale_item_id, member_id, lesson_package_product_id)
           VALUES (1, 10, 1), (2, 11, 1)""",
        """INSERT INTO lesson_packages
           (id, member_id, product_id, purchase_sale_item_id, name, total_lessons,
            remaining_lessons, reserved_lessons, valid_from)
           VALUES (1, 10, 1, 1, 'Review lessons', 10, 8, 1, '2026-11-01'),
                  (2, 11, 1, 2, 'Review lessons', 10, 8, 0, '2026-11-01')""",
        """INSERT INTO bookings
           (id, member_id, session_id, lesson_package_id, status, booked_at, checked_in_at, closed_at)
           VALUES (40, 10, 30, 1, 'completed', :booked, :start30, :end30),
                  (41, 10, 34, 1, 'reserved', :booked, NULL, NULL),
                  (42, 10, 31, 1, 'completed', :booked, :start31, :end31),
                  (43, 11, 32, 2, 'completed', :booked, :start32, :end32),
                  (44, 11, 33, 2, 'completed', :booked, :start33, :end33)""",
    ]
    dates = {"booked": "2026-11-01 10:00:00"}
    for session_id, day in enumerate(range(2, 7), start=30):
        dates[f"start{session_id}"] = f"2026-11-{day:02} 10:00:00"
        dates[f"end{session_id}"] = f"2026-11-{day:02} 11:00:00"
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement), dates)
    return ReviewLogic(sessionmaker(bind=engine), ReviewService(AuthService(log_config=LogConfig())))


def review(booking_id=40, rating=5, comment="课程很清楚"):
    return ReviewInput(booking_id=booking_id, rating=rating, comment=comment)


@pytest.mark.parametrize("rating,comment,expected", [
    (1, "   ", ""), (5, "  体验很好  ", "体验很好"), (3, "课" * 1000, "课" * 1000),
])
def test_create_review_returns_and_persists_the_completed_booking(
    initialized_mysql_database, review_logic, rating, comment, expected,
):
    view = review_logic.create_review(MEMBER, review(rating=rating, comment=comment))
    assert (view.member_id, view.session_id, view.coach_id) == (10, 30, 20)
    assert view.rating == rating
    assert view.comment == expected
    assert view.created_at.tzinfo is timezone.utc
    assert review_logic.get_review(MEMBER, view.id) == view
    with initialized_mysql_database.connect() as connection:
        assert connection.scalar(text("SELECT status FROM bookings WHERE id = 40")) == "completed"


def test_duplicate_preserves_original_and_uses_mysql_locking_reads(initialized_mysql_database, review_logic):
    statements = []
    engine = initialized_mysql_database

    def capture(connection, cursor, statement, parameters, context, executemany):
        if "FOR UPDATE" in statement and ("FROM bookings" in statement or "FROM reviews" in statement):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        original = review_logic.create_review(MEMBER, review())
        with pytest.raises(ConflictError):
            review_logic.create_review(MEMBER, review(rating=1, comment="再次提交"))
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    with Session(engine) as session, pytest.raises(ConflictError) as duplicate:
        ReviewRepository(session).create(review(rating=1))
    assert isinstance(duplicate.value.__cause__, IntegrityError)
    assert duplicate.value.__cause__.orig.args[0] == 1062
    assert review_logic.get_review(MEMBER, original.id) == original
    assert review_logic.list_reviews(ADMIN, ReviewQuery()).total == 1

    assert len(statements) == 4
    for booking_lock, review_lock in zip(statements[::2], statements[1::2]):
        assert "FROM bookings" in booking_lock and "WHERE bookings.id" in booking_lock
        assert "FROM reviews" in review_lock and "WHERE reviews.booking_id" in review_lock
        assert "JOIN" not in booking_lock + review_lock


def test_reads_scope_details_count_and_stable_pages(initialized_mysql_database, review_logic):
    reviews = {
        booking_id: review_logic.create_review(actor, review(booking_id=booking_id))
        for actor, booking_id in ((MEMBER, 40), (MEMBER, 42), (OTHER_MEMBER, 43), (OTHER_MEMBER, 44))
    }
    with initialized_mysql_database.begin() as connection:
        connection.execute(text("UPDATE reviews SET created_at = '2026-11-08 12:00:00'"))

    for actor, visible in (
        (MEMBER, [42, 40]), (OTHER_MEMBER, [44, 43]), (COACH, [43, 40]),
        (OTHER_COACH, [44, 42]), (ADMIN, [44, 43, 42, 40]),
    ):
        first = review_logic.list_reviews(actor, ReviewQuery(paging=PageRequest(page_size=1)))
        second = review_logic.list_reviews(actor, ReviewQuery(paging=PageRequest(page=2, page_size=1)))
        assert first.total == second.total == len(visible)
        assert [item.booking_id for item in first.items + second.items] == visible[:2]
        assert review_logic.get_review(actor, reviews[visible[0]].id).booking_id == visible[0]

    for actor, hidden in ((MEMBER, 43), (OTHER_MEMBER, 40), (COACH, 42), (OTHER_COACH, 40)):
        with pytest.raises(NotFoundError, match="评价不存在或不可见"):
            review_logic.get_review(actor, reviews[hidden].id)
    with pytest.raises(NotFoundError, match="评价不存在或不可见"):
        review_logic.get_review(ADMIN, max(item.id for item in reviews.values()) + 1)

    assert review_logic.list_reviews(MEMBER, ReviewQuery(member_id=11)).total == 0
    assert review_logic.list_reviews(COACH, ReviewQuery(coach_id=21)).total == 0
    assert review_logic.list_reviews(ADMIN, ReviewQuery(member_id=10, coach_id=21)).total == 1


@pytest.mark.parametrize("repository, method", [
    (BookingRepository, "lock"), (ReviewRepository, "has_for_booking"),
])
def test_locking_read_blocks_until_transaction_ends(initialized_mysql_database, review_logic, repository, method):
    review_logic.create_review(MEMBER, review())
    engine = initialized_mysql_database
    with Session(engine) as first, Session(engine) as second:
        second.execute(text("SET SESSION innodb_lock_wait_timeout = 1"))
        assert getattr(repository(first), method)(40)
        with pytest.raises(OperationalError) as error:
            getattr(repository(second), method)(40)
        assert error.value.orig.args[0] == 1205
        second.rollback()
        first.rollback()
        assert getattr(repository(second), method)(40)


def test_committed_account_deactivation_blocks_all_review_operations(initialized_mysql_database, review_logic):
    original = review_logic.create_review(MEMBER, review())
    assert review_logic.get_review(MEMBER, original.id) == original
    assert review_logic.list_reviews(MEMBER, ReviewQuery()).total == 1
    with initialized_mysql_database.begin() as connection:
        connection.execute(text("UPDATE accounts SET is_active = 0 WHERE id = :id"), {"id": MEMBER.account_id})

    for method, data in (
        (review_logic.create_review, review(booking_id=42)),
        (review_logic.get_review, original.id),
        (review_logic.list_reviews, ReviewQuery()),
    ):
        with pytest.raises(AuthenticationError, match="当前登录身份已失效"):
            method(MEMBER, data)
    assert review_logic.list_reviews(ADMIN, ReviewQuery()).items == [original]


def test_write_failure_rolls_back_insert(initialized_mysql_database, review_logic, monkeypatch):
    def fail(repository, review_id, **scope):
        assert repository._session.scalar(
            text("SELECT booking_id FROM reviews WHERE id = :id"), {"id": review_id},
        ) == 40
        raise SQLAlchemyError("driver details")

    monkeypatch.setattr(ReviewRepository, "get", fail)
    with pytest.raises(StorageError, match="保存评价失败"):
        review_logic.create_review(MEMBER, review())
    assert review_logic.list_reviews(ADMIN, ReviewQuery()).total == 0


@pytest.mark.parametrize("same_booking", [True, False], ids=["same-booking", "different-bookings"])
def test_concurrent_review_submissions(review_logic, same_booking):
    start = Barrier(2)
    second_actor, second_booking = (MEMBER, 40) if same_booking else (OTHER_MEMBER, 43)

    def submit(actor, booking_id, rating):
        start.wait(timeout=10)
        return review_logic.create_review(actor, review(booking_id=booking_id, rating=rating))

    saved = []
    conflicts = 0
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(submit, MEMBER, 40, 5)
        second = workers.submit(submit, second_actor, second_booking, 1)
        for future in (first, second):
            try:
                saved.append(future.result(timeout=20))
            except ConflictError:
                conflicts += 1

    assert conflicts == int(same_booking)
    assert {item.booking_id for item in saved} == {40, second_booking}
    page = review_logic.list_reviews(ADMIN, ReviewQuery())
    assert page.total == len(saved)
    assert {item.id: item for item in page.items} == {item.id: item for item in saved}
