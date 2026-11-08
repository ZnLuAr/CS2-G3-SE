"""评价授权、SQL 分页、事务与 CLI 回归。行锁语法按 MySQL 方言验证。"""

from datetime import timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.db.review_repo import ReviewRepository
from src.errors import (
    AuthenticationError, ConflictError, InvalidInputError, InvalidState,
    NotFoundError, OutcomeUnknownError, PermissionDenied, StorageError,
)
from src.logic.review_logic import ReviewLogic
from src.models.contracts import Actor, PageRequest, ReviewInput, ReviewQuery
from src.services.review_service import ReviewService
from src.ui.cli.app import GymCLI, invoke_action
from src.ui.cli.handlers.review import ReviewHandler
from src.ui.cli.menus import review_menu


MEMBER = Actor(account_id=1, role="member", member_id=10, coach_id=None)
OTHER_MEMBER = Actor(account_id=2, role="member", member_id=11, coach_id=None)
COACH = Actor(account_id=3, role="coach", member_id=None, coach_id=20)
OTHER_COACH = Actor(account_id=4, role="coach", member_id=None, coach_id=21)
ADMIN = Actor(account_id=5, role="admin", member_id=None, coach_id=None)
RECEPTIONIST = Actor(account_id=6, role="receptionist", member_id=None, coach_id=None)


def review(booking_id=40, rating=5, comment="课程很清楚"):
    return ReviewInput(booking_id=booking_id, rating=rating, comment=comment)


@pytest.fixture
def app():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for statement in (
            "CREATE TABLE course_sessions (id INTEGER PRIMARY KEY, coach_id INTEGER NOT NULL)",
            """CREATE TABLE bookings (
                id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL, session_id INTEGER NOT NULL,
                lesson_package_id INTEGER NOT NULL DEFAULT 100, status TEXT NOT NULL,
                booked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, checked_in_at DATETIME,
                closed_at DATETIME, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE reviews (
                id INTEGER PRIMARY KEY, booking_id INTEGER NOT NULL UNIQUE,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT NOT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            "INSERT INTO course_sessions VALUES (30, 20), (31, 21)",
            """INSERT INTO bookings (id, member_id, session_id, status) VALUES
                (40, 10, 30, 'completed'), (41, 10, 31, 'reserved'),
                (42, 10, 31, 'completed'), (43, 11, 30, 'completed'),
                (44, 11, 31, 'completed')""",
        ):
            connection.execute(text(statement))
    factory = sessionmaker(bind=engine)
    auth = Mock()
    auth.verify_actor.side_effect = lambda session, actor: actor
    service = ReviewService(auth)
    yield SimpleNamespace(engine=engine, factory=factory, logic=ReviewLogic(factory, service), auth=auth)
    engine.dispose()


@pytest.mark.parametrize("rating,comment,expected", [
    (1, "   ", ""), (5, "  体验很好  ", "体验很好"), (3, "课" * 1000, "课" * 1000),
])
def test_create_review_returns_and_persists_the_completed_booking(app, rating, comment, expected):
    view = app.logic.create_review(MEMBER, review(rating=rating, comment=comment))
    assert (view.member_id, view.session_id, view.coach_id) == (10, 30, 20)
    assert view.rating == rating
    assert view.comment == expected
    assert view.created_at.tzinfo is timezone.utc
    assert app.logic.get_review(MEMBER, view.id) == view
    with app.factory() as session:
        assert session.scalar(text("SELECT status FROM bookings WHERE id = 40")) == "completed"


@pytest.mark.parametrize("data,error", [
    (review(booking_id=0), InvalidInputError),
    (review(booking_id=True), InvalidInputError),
    (review(rating=True), InvalidInputError),
    (review(rating=4.0), InvalidInputError),
    (review(rating=6), InvalidInputError),
    (review(comment=None), InvalidInputError),
    (review(comment="课" * 1001), InvalidInputError),
    (review(booking_id=41), InvalidState),
    (review(booking_id=43), NotFoundError),
    (review(booking_id=999), NotFoundError),
])
def test_rejected_submission_does_not_insert(app, data, error):
    with pytest.raises(error):
        app.logic.create_review(MEMBER, data)
    assert app.logic.list_reviews(ADMIN, ReviewQuery()).total == 0


def test_duplicate_preserves_original_and_uses_mysql_locking_reads(app):
    statements = []

    @event.listens_for(app.engine, "before_execute")
    def capture(connection, statement, multiparams, params, execution_options):
        statements.append(str(statement.compile(dialect=mysql.dialect())))

    original = app.logic.create_review(MEMBER, review())
    with pytest.raises(ConflictError):
        app.logic.create_review(MEMBER, review(rating=1, comment="再次提交"))
    assert app.logic.get_review(MEMBER, original.id) == original
    assert app.logic.list_reviews(ADMIN, ReviewQuery()).total == 1
    locked = [statement for statement in statements if "FOR UPDATE" in statement]
    assert len(locked) == 4
    for booking_lock, review_lock in zip(locked[::2], locked[1::2]):
        assert "FROM bookings" in booking_lock and "WHERE bookings.id" in booking_lock
        assert "FROM reviews" in review_lock and "WHERE reviews.booking_id" in review_lock
        assert "JOIN" not in booking_lock + review_lock


@pytest.mark.parametrize("code,expected", [(1062, ConflictError), (1452, IntegrityError)])
def test_insert_only_maps_mysql_duplicate_key_to_conflict(code, expected):
    session = Mock(spec=Session)
    session.execute.side_effect = IntegrityError("INSERT", {}, Exception(code, "driver details"))
    with pytest.raises(expected):
        ReviewRepository(session).create(review())


def test_reads_scope_details_count_and_stable_pages(app):
    for actor, booking_id in ((MEMBER, 40), (MEMBER, 42), (OTHER_MEMBER, 43), (OTHER_MEMBER, 44)):
        app.logic.create_review(actor, review(booking_id=booking_id))
    with app.factory.begin() as session:
        session.execute(text("UPDATE reviews SET created_at = '2026-11-08 12:00:00'"))

    for actor, visible in (
        (MEMBER, [42, 40]), (OTHER_MEMBER, [44, 43]), (COACH, [43, 40]),
        (OTHER_COACH, [44, 42]), (ADMIN, [44, 43, 42, 40]),
    ):
        query = ReviewQuery(paging=PageRequest(page_size=1))
        page = app.logic.list_reviews(actor, query)
        assert page.total == len(visible)
        assert [item.booking_id for item in page.items] == visible[:1]
        query = ReviewQuery(paging=PageRequest(page=2, page_size=1))
        page = app.logic.list_reviews(actor, query)
        assert [item.booking_id for item in page.items] == visible[1:2]

    for actor, hidden_id in ((MEMBER, 3), (OTHER_MEMBER, 1), (COACH, 2), (OTHER_COACH, 1)):
        with pytest.raises(NotFoundError, match="评价不存在或不可见"):
            app.logic.get_review(actor, hidden_id)
    with pytest.raises(NotFoundError, match="评价不存在或不可见"):
        app.logic.get_review(ADMIN, 999)

    assert app.logic.list_reviews(MEMBER, ReviewQuery(member_id=11)).total == 0
    assert app.logic.list_reviews(COACH, ReviewQuery(coach_id=21)).total == 0
    assert app.logic.list_reviews(ADMIN, ReviewQuery(member_id=10, coach_id=21)).total == 1


@pytest.mark.parametrize("query", [
    ReviewQuery(member_id=True), ReviewQuery(coach_id=-1), ReviewQuery(paging=None),
    ReviewQuery(paging=PageRequest(page_size=101)), ReviewQuery(paging=PageRequest(page=0)),
    ReviewQuery(paging=PageRequest(page=2**63 - 1, page_size=100)),
])
def test_invalid_query_cannot_reach_sql(app, query):
    with pytest.raises(InvalidInputError):
        app.logic.list_reviews(ADMIN, query)


def test_role_checks_and_revoked_identity(app):
    for actor in (COACH, ADMIN, RECEPTIONIST):
        with pytest.raises(PermissionDenied):
            app.logic.create_review(actor, review())
    with pytest.raises(PermissionDenied):
        app.logic.get_review(RECEPTIONIST, 1)
    with pytest.raises(PermissionDenied):
        app.logic.list_reviews(RECEPTIONIST, ReviewQuery())

    app.auth.verify_actor.side_effect = AuthenticationError("请重新登录")
    for call in (
        lambda: app.logic.create_review(MEMBER, review()),
        lambda: app.logic.get_review(MEMBER, 1),
        lambda: app.logic.list_reviews(MEMBER, ReviewQuery()),
    ):
        with pytest.raises(AuthenticationError):
            call()


def test_write_failure_rolls_back_insert(app, monkeypatch):
    def fail(*args, **kwargs):
        raise SQLAlchemyError("driver details")

    monkeypatch.setattr(ReviewRepository, "get", fail)
    with pytest.raises(StorageError, match="保存评价失败"):
        app.logic.create_review(MEMBER, review())
    assert app.logic.list_reviews(ADMIN, ReviewQuery()).total == 0


@pytest.mark.parametrize("code,failures,attempts", [(1213, 1, 2), (1213, 2, 2), (1205, 1, 1)])
def test_retries_only_a_confirmed_mysql_deadlock_once(app, monkeypatch, code, failures, attempts):
    original = ReviewRepository.create
    sessions = []

    def create(repository, data):
        sessions.append(repository._session)
        if len(sessions) <= failures:
            raise OperationalError("INSERT", {}, Exception(code, "driver details"))
        return original(repository, data)

    monkeypatch.setattr(ReviewRepository, "create", create)
    if attempts > failures:
        assert app.logic.create_review(MEMBER, review()).id == 1
    else:
        with pytest.raises(StorageError):
            app.logic.create_review(MEMBER, review())
    assert len(set(sessions)) == attempts


def test_unknown_commit_identifies_the_review(app):
    class FailingCommit(Session):
        def commit(self):
            raise SQLAlchemyError("connection lost")

    logic = ReviewLogic(lambda: FailingCommit(app.engine), ReviewService(app.auth))
    with pytest.raises(OutcomeUnknownError) as error:
        logic.create_review(MEMBER, review())
    assert error.value.record_id == 1


def test_cli_navigation_success_and_missing_detail(app, monkeypatch, capsys):
    handler = ReviewHandler(app.logic, lambda: MEMBER, timezone_name="Asia/Shanghai")
    handlers = SimpleNamespace(review=handler, **{
        name: Mock() for name in (
            "member", "product", "course", "booking", "attendance", "equipment",
            "measurement", "notification", "recommendation",
        )
    })
    cli = GymCLI(handlers, lambda: MEMBER, lambda: None)
    answers = iter(("6", "1", "40", "5", "谢谢教练", "y", "1", "40", "1", "", "y", "2", "999", "3", "0", "0", "0"))
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    assert cli.run() == 0
    output = capsys.readouterr().out
    assert "谢谢教练" in output
    assert "这条预约已有评价" in output
    assert "评价不存在或不可见" in output
    assert "共 1 条" in output


@pytest.mark.parametrize("answers", [("40", "5", "q"), ("40", "5", "", "n")])
def test_cli_cancellation_never_calls_write(monkeypatch, answers):
    inputs = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    logic = Mock()
    handler = ReviewHandler(logic, lambda: MEMBER, timezone_name="Asia/Shanghai")
    result = invoke_action(handler.create_review, operation="review.create")
    assert result.action == "continue"
    logic.create_review.assert_not_called()


@pytest.mark.parametrize("actor,keys", [
    (MEMBER, ["1", "2", "3"]), (COACH, ["2", "3"]), (ADMIN, ["2", "3"]), (RECEPTIONIST, []),
])
def test_role_specific_review_menu(actor, keys):
    handler = ReviewHandler(Mock(), lambda: actor, timezone_name="Asia/Shanghai")
    assert [item.key for item in review_menu(handler)] == keys


def test_cli_empty_page(app, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "0")
    handler = ReviewHandler(app.logic, lambda: COACH, timezone_name="Asia/Shanghai")
    handler.list_reviews()
    assert "暂无记录" in capsys.readouterr().out


def test_review_success_event_follows_commit_without_comment(app, monkeypatch):
    logic, sessions = app.logic, app.factory
    events = []

    def capture(level, **event):
        with sessions() as session:
            assert session.execute(text("SELECT COUNT(*) FROM reviews")).scalar_one() == 1
        events.append(event)
        raise OSError("log writer unavailable")

    monkeypatch.setattr("src.logic.review_logic.log_event", capture)
    result = logic.create_review(MEMBER, review())
    assert events == [{
        "operation": "review.create", "outcome": "success",
        "actor_id": MEMBER.account_id, "result_id": result.id,
    }]
