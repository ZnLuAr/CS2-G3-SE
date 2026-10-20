from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jwt")
pytest.importorskip("httpx")

import jwt

from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.config import AppSettings, DatabaseConfig, WebConfig
from src.errors.business import AuthenticationError
from src.errors.storage import OutcomeUnknownError
from src.models.contracts import Actor
from src.web.main import create_app
from src.web.security import TokenManager
from src.web.schemas import ActorResponse


ACTOR = Actor(account_id=7, role="member", member_id=12, coach_id=None)


class FakeAuthLogic:
    def __init__(self) -> None:
        self.username: str | None = None
        self.current_actor: Actor | None = None

    def login(self, username: str, password: str) -> Actor:
        self.username = username
        if password != "secret_1":
            raise AuthenticationError("用户名或密码不正确")
        return ACTOR

    def get_current_actor(self, actor: Actor) -> Actor:
        self.current_actor = actor
        return actor


class FakeRuntime:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.logic_bundle = SimpleNamespace(auth=FakeAuthLogic())
        self.started = False
        self.closed = False

    def start(self, *, with_worker: bool = False) -> None:
        assert with_worker is True
        self.started = True

    def close(self) -> None:
        self.closed = True


def settings() -> AppSettings:
    return AppSettings(
        database=DatabaseConfig(
            host="localhost",
            port=3306,
            database="gym_test",
            username="tester",
            password="",
        ),
        web=WebConfig(token_lifetime_seconds=3600),
    )


def test_login_me_and_logout_use_typed_actor_and_camel_case(monkeypatch):
    import src.web.main as web_main

    runtime: FakeRuntime | None = None

    def create_runtime(config: AppSettings) -> FakeRuntime:
        nonlocal runtime
        runtime = FakeRuntime(config)
        return runtime

    monkeypatch.setattr(web_main, "App", create_runtime)
    monkeypatch.setenv("GYM_JWT_SECRET", "x" * 32)
    with TestClient(create_app(settings())) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "  TEST_USER ", "password": "secret_1"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["tokenType"] == "bearer"
        assert body["actor"] == {
            "accountId": "7",
            "role": "member",
            "memberId": "12",
            "coachId": None,
        }
        assert runtime is not None
        assert runtime.logic_bundle.auth.username == "test_user"

        headers = {"Authorization": f"Bearer {body['accessToken']}"}
        current = client.get("/api/auth/me", headers=headers)
        assert current.status_code == 200
        assert current.json() == body["actor"]
        assert runtime.logic_bundle.auth.current_actor == ACTOR

        logout = client.post("/api/auth/logout", headers=headers)
        assert logout.status_code == 200
        assert logout.json() == {"loggedOut": True}

    assert runtime is not None and runtime.started and runtime.closed


def test_authentication_errors_have_fixed_http_contract(monkeypatch):
    import src.web.main as web_main

    monkeypatch.setattr(web_main, "App", FakeRuntime)
    monkeypatch.setenv("GYM_JWT_SECRET", "x" * 32)
    with TestClient(create_app(settings())) as client:
        missing = client.get("/api/auth/me")
        assert missing.status_code == 401
        assert missing.json() == {
            "message": "请使用有效的 Bearer 访问令牌",
            "action": "login",
            "errorType": "AuthenticationError",
            "requestId": None,
            "recordId": None,
        }
        rejected = client.post(
            "/api/auth/login",
            json={"username": "valid_name", "password": "wrong_1"},
        )
        assert rejected.status_code == 401
        assert rejected.json()["action"] == "login"


def test_invalid_login_shape_does_not_echo_password(monkeypatch):
    import src.web.main as web_main

    monkeypatch.setattr(web_main, "App", FakeRuntime)
    monkeypatch.setenv("GYM_JWT_SECRET", "x" * 32)
    with TestClient(create_app(settings())) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "valid_name", "password": "private" * 8},
        )
    assert response.status_code == 422
    assert "private" not in response.text
    assert response.json()["errorType"] == "RequestValidationError"


def test_token_manager_rejects_tampered_and_malformed_actor_claims():
    manager = TokenManager("s" * 32, WebConfig())
    token, _ = manager.issue(ACTOR)
    assert manager.decode(token) == ACTOR
    with pytest.raises(AuthenticationError):
        manager.decode(token[:-1] + ("a" if token[-1] != "a" else "b"))


@pytest.mark.parametrize("actor", [
    ACTOR,
    Actor(account_id=8, role="coach", member_id=None, coach_id=13),
    Actor(account_id=9, role="receptionist", member_id=None, coach_id=None),
    Actor(account_id=10, role="admin", member_id=None, coach_id=None),
])
def test_tokens_preserve_nullable_profile_ids_for_each_role(actor):
    manager = TokenManager("s" * 32, WebConfig())
    token, _ = manager.issue(actor)
    assert manager.decode(token) == actor


@pytest.mark.parametrize("claim", ["member_id", "coach_id"])
def test_tokens_require_profile_claim_presence_even_when_nullable(claim):
    secret = "s" * 32
    manager = TokenManager(secret, WebConfig())
    token, _ = manager.issue(ACTOR)
    claims = jwt.decode(token, options={"verify_signature": False})
    del claims[claim]
    with pytest.raises(AuthenticationError):
        manager.decode(jwt.encode(claims, secret, algorithm="HS256"))


def test_http_actor_ids_preserve_bigint_precision(monkeypatch):
    """HTTP 使用十进制字符串；JWT 继续保持服务器内部身份声明。"""
    import src.web.main as web_main

    actor = Actor(account_id=2**63 - 1, role="member", member_id=2**53 + 1, coach_id=None)
    monkeypatch.setattr(web_main, "App", FakeRuntime)
    monkeypatch.setattr(FakeAuthLogic, "login", lambda *_: actor)
    monkeypatch.setenv("GYM_JWT_SECRET", "x" * 32)
    with TestClient(create_app(settings())) as client:
        login = client.post(
            "/api/auth/login", json={"username": "valid_name", "password": "secret_1"},
        )
        assert login.status_code == 200
        body = login.json()
        assert body["actor"]["accountId"] == str(2**63 - 1)
        assert body["actor"]["memberId"] == str(2**53 + 1)
        current = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {body['accessToken']}"},
        )
        assert current.json() == body["actor"]


@pytest.mark.parametrize("identifier", [True, 7, "0", "01", "+1", "-1", "1.0", str(2**63)])
def test_http_business_ids_reject_noncanonical_or_out_of_range_values(identifier):
    with pytest.raises(ValidationError):
        ActorResponse(
            account_id=identifier, role="admin", member_id=None, coach_id=None,
        )


def test_unknown_commit_error_preserves_record_id_as_string(monkeypatch):
    import src.web.main as web_main

    def unknown_commit(*_) -> Actor:
        raise OutcomeUnknownError("提交结果未知", record_id=2**53 + 1)

    monkeypatch.setattr(web_main, "App", FakeRuntime)
    monkeypatch.setattr(FakeAuthLogic, "login", unknown_commit)
    monkeypatch.setenv("GYM_JWT_SECRET", "x" * 32)
    with TestClient(create_app(settings())) as client:
        response = client.post(
            "/api/auth/login", json={"username": "valid_name", "password": "secret_1"},
        )
    assert response.status_code == 503
    assert response.json()["action"] == "verify"
    assert response.json()["recordId"] == str(2**53 + 1)


@pytest.mark.parametrize(("method", "path", "status"), [
    ("GET", "/api/missing", 404),
    ("GET", "/api/auth/login", 405),
])
def test_routing_errors_use_the_shared_error_contract(monkeypatch, method, path, status):
    import src.web.main as web_main

    monkeypatch.setattr(web_main, "App", FakeRuntime)
    monkeypatch.setenv("GYM_JWT_SECRET", "x" * 32)
    with TestClient(create_app(settings())) as client:
        response = client.request(method, path)
    assert response.status_code == status
    assert set(response.json()) == {"message", "action", "errorType", "requestId", "recordId"}
    assert response.json()["action"] == "continue"
    if status == 405:
        assert response.headers["allow"] == "POST"
