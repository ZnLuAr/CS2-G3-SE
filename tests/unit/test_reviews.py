"""评价服务、用例事务和 CLI 的隔离回归。"""

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.config import LogConfig
from src.db.booking_repo import BookingRepository
from src.db.review_repo import ReviewRepository
from src.errors import (
    AuthenticationError, ConflictError, InvalidInputError, InvalidState,
    NotFoundError, OutcomeUnknownError, PermissionDenied, StorageError,
)
from src.logic.review_logic import ReviewLogic
from src.models.contracts import Actor, Page, PageRequest, ReviewInput, ReviewQuery, ReviewView
from src.services.auth_service import AuthService
from src.services.review_service import ReviewService
from src.ui.cli.app import GymCLI, invoke_action
from src.ui.cli.handlers.review import ReviewHandler
from src.ui.cli.menus import review_menu


MEMBER = Actor(account_id=1, role="member", member_id=10, coach_id=None)
COACH = Actor(account_id=3, role="coach", member_id=None, coach_id=20)
ADMIN = Actor(account_id=5, role="admin", member_id=None, coach_id=None)
RECEPTIONIST = Actor(account_id=6, role="receptionist", member_id=None, coach_id=None)


def review(booking_id=40, rating=5, comment="课程很清楚"):
    return ReviewInput(booking_id=booking_id, rating=rating, comment=comment)


def review_view(comment="课程很清楚"):
    return ReviewView(
        id=1, booking_id=40, member_id=10, session_id=30, coach_id=20,
        rating=5, comment=comment, created_at=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )


@pytest.fixture
def repositories(monkeypatch):
    bookings = Mock(spec=BookingRepository)
    reviews = Mock(spec=ReviewRepository)
    monkeypatch.setattr("src.services.review_service.BookingRepository", Mock(return_value=bookings))
    monkeypatch.setattr("src.services.review_service.ReviewRepository", Mock(return_value=reviews))
    return bookings, reviews


@pytest.fixture
def auth():
    auth = Mock(spec=AuthService)
    auth.verify_actor.side_effect = lambda session, actor: actor
    return auth


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
def test_rejected_submission_does_not_insert(repositories, auth, data, error):
    bookings, reviews = repositories
    bookings.lock.side_effect = {
        41: SimpleNamespace(member_id=10, status="reserved"),
        43: SimpleNamespace(member_id=11, status="completed"),
        999: None,
    }.__getitem__
    with pytest.raises(error):
        ReviewService(auth).create_review(Mock(spec=Session), MEMBER, data)
    assert not reviews.mock_calls


@pytest.mark.parametrize("code,expected", [(1062, ConflictError), (1452, IntegrityError)])
def test_insert_only_maps_mysql_duplicate_key_to_conflict(code, expected):
    session = Mock(spec=Session)
    session.execute.side_effect = IntegrityError("INSERT", {}, Exception(code, "driver details"))
    with pytest.raises(expected):
        ReviewRepository(session).create(review())


@pytest.mark.parametrize("query", [
    ReviewQuery(member_id=True), ReviewQuery(coach_id=-1), ReviewQuery(paging=None),
    ReviewQuery(paging=PageRequest(page_size=101)), ReviewQuery(paging=PageRequest(page=0)),
    ReviewQuery(paging=PageRequest(page=2**63 - 1, page_size=100)),
])
def test_invalid_query_cannot_reach_repository(repositories, auth, query):
    _, reviews = repositories
    with pytest.raises(InvalidInputError):
        ReviewService(auth).list_reviews(Mock(spec=Session), ADMIN, query)
    assert not reviews.mock_calls


def test_role_checks(repositories, auth):
    service = ReviewService(auth)
    session = Mock(spec=Session)
    for actor in (COACH, ADMIN, RECEPTIONIST):
        with pytest.raises(PermissionDenied):
            service.create_review(session, actor, review())
    with pytest.raises(PermissionDenied):
        service.get_review(session, RECEPTIONIST, 1)
    with pytest.raises(PermissionDenied):
        service.list_reviews(session, RECEPTIONIST, ReviewQuery())
    assert all(not repository.mock_calls for repository in repositories)


@pytest.mark.parametrize("method,data", [
    ("create_review", review()), ("get_review", 1), ("list_reviews", ReviewQuery()),
])
def test_disabled_account_cannot_submit_or_query_reviews(repositories, monkeypatch, method, data):
    accounts = Mock()
    accounts.lock.return_value = SimpleNamespace(role=MEMBER.role, is_active=False)
    account_repository = Mock(return_value=accounts)
    monkeypatch.setattr("src.services.auth_service.AccountRepository", account_repository)
    session = Mock(spec=Session)
    service = ReviewService(AuthService(log_config=LogConfig()))

    with pytest.raises(AuthenticationError, match="当前登录身份已失效"):
        getattr(service, method)(session, MEMBER, data)

    account_repository.assert_called_once_with(session)
    accounts.lock.assert_called_once_with(MEMBER.account_id)
    accounts.lock_profile_links.assert_not_called()
    assert all(not repository.mock_calls for repository in repositories)


def test_review_permissions_use_the_verified_actor(repositories):
    bookings, reviews = repositories
    bookings.lock.return_value = SimpleNamespace(id=40, member_id=10, status="completed")
    reviews.has_for_booking.return_value = False
    auth = Mock(spec=AuthService)
    auth.verify_actor.return_value = MEMBER
    session = Mock(spec=Session)
    service = ReviewService(auth)
    query = ReviewQuery()

    service.create_review(session, RECEPTIONIST, review())
    service.get_review(session, RECEPTIONIST, 1)
    service.list_reviews(session, RECEPTIONIST, query)

    assert auth.verify_actor.call_args_list == [call(session, RECEPTIONIST)] * 3
    reviews.create.assert_called_once_with(review())
    reviews.get.assert_called_once_with(1, scope_member_id=10, scope_coach_id=None)
    reviews.list.assert_called_once_with(query, scope_member_id=10, scope_coach_id=None)


@pytest.mark.parametrize("code,failures,attempts", [(1213, 1, 2), (1213, 2, 2), (1205, 1, 1)])
def test_retries_only_a_confirmed_mysql_deadlock_once(code, failures, attempts):
    sessions = [Mock(spec=Session) for _ in range(attempts)]
    factory = Mock(side_effect=[nullcontext(session) for session in sessions])
    service = Mock(spec=ReviewService)
    result = review_view()
    service.create_review.side_effect = [
        OperationalError("INSERT", {}, Exception(code, "driver details")) for _ in range(failures)
    ] + [result]
    logic = ReviewLogic(factory, service)

    if attempts > failures:
        assert logic.create_review(MEMBER, review()) == result
        sessions[-1].commit.assert_called_once_with()
    else:
        with pytest.raises(StorageError):
            logic.create_review(MEMBER, review())

    assert service.create_review.call_args_list == [call(session, MEMBER, review()) for session in sessions]
    for session in sessions[:failures]:
        session.rollback.assert_called_once_with()
        session.commit.assert_not_called()


def test_unknown_commit_identifies_the_review():
    session = Mock(spec=Session)
    session.commit.side_effect = SQLAlchemyError("connection lost")
    factory = Mock(return_value=nullcontext(session))
    result = review_view()
    service = Mock(spec=ReviewService)
    service.create_review.return_value = result
    with pytest.raises(OutcomeUnknownError) as error:
        ReviewLogic(factory, service).create_review(MEMBER, review())
    assert error.value.record_id == result.id
    factory.assert_called_once_with()


def test_cli_navigation_success_and_missing_detail(monkeypatch, capsys):
    logic = Mock(spec=ReviewLogic)
    result = review_view(comment="谢谢教练")
    logic.create_review.side_effect = [result, ConflictError("这条预约已有评价")]
    logic.get_review.side_effect = NotFoundError("评价不存在或不可见")
    logic.list_reviews.return_value = Page(items=[result], total=1, page=1, page_size=20)
    handler = ReviewHandler(logic, lambda: MEMBER, timezone_name="Asia/Shanghai")
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
    assert logic.create_review.call_args_list == [
        call(MEMBER, review(comment="谢谢教练")), call(MEMBER, review(rating=1, comment="")),
    ]
    logic.get_review.assert_called_once_with(MEMBER, 999)
    logic.list_reviews.assert_called_once_with(MEMBER, ReviewQuery())


@pytest.mark.parametrize("answers", [("40", "5", "q"), ("40", "5", "", "n")])
def test_cli_cancellation_never_calls_write(monkeypatch, answers):
    inputs = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    logic = Mock(spec=ReviewLogic)
    handler = ReviewHandler(logic, lambda: MEMBER, timezone_name="Asia/Shanghai")
    result = invoke_action(handler.create_review, operation="review.create")
    assert result.action == "continue"
    logic.create_review.assert_not_called()


@pytest.mark.parametrize("actor,keys", [
    (MEMBER, ["1", "2", "3"]), (COACH, ["2", "3"]), (ADMIN, ["2", "3"]), (RECEPTIONIST, []),
])
def test_role_specific_review_menu(actor, keys):
    handler = ReviewHandler(Mock(spec=ReviewLogic), lambda: actor, timezone_name="Asia/Shanghai")
    assert [item.key for item in review_menu(handler)] == keys


def test_cli_empty_page(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: "0")
    logic = Mock(spec=ReviewLogic)
    logic.list_reviews.return_value = Page(items=[], total=0, page=1, page_size=20)
    handler = ReviewHandler(logic, lambda: COACH, timezone_name="Asia/Shanghai")
    handler.list_reviews()
    assert "暂无记录" in capsys.readouterr().out


def test_review_success_event_follows_commit_without_comment(monkeypatch, capsys):
    session = Mock(spec=Session)
    service = Mock(spec=ReviewService)
    service.create_review.return_value = review_view()
    events = []

    def capture(level, **event):
        session.commit.assert_called_once_with()
        events.append(event)
        raise OSError("log writer unavailable")

    monkeypatch.setattr("src.logic.review_logic.log_event", capture)
    result = ReviewLogic(lambda: nullcontext(session), service).create_review(MEMBER, review())
    assert events == [{
        "operation": "review.create", "outcome": "success",
        "actor_id": MEMBER.account_id, "result_id": result.id,
    }]
    assert capsys.readouterr().err == "操作日志记录失败（review.create，OSError）\n"
