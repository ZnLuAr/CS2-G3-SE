"""登录、当前身份和退出路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.logic import LogicBundle
from src.models.contracts import Actor
from src.web.deps import get_current_actor, get_logic_bundle
from src.web.schemas import ActorResponse, LoginRequest, LoginResponse, LogoutResponse


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, logic: LogicBundle = Depends(get_logic_bundle)) -> LoginResponse:
    actor = logic.auth.login(payload.username, payload.password.get_secret_value())
    access_token, expires_at = request.app.state.token_manager.issue(actor)
    return LoginResponse(
        access_token=access_token,
        expires_at=expires_at,
        actor=ActorResponse.from_actor(actor),
    )


@router.get("/me", response_model=ActorResponse)
def current_actor(
    actor: Actor = Depends(get_current_actor),
    logic: LogicBundle = Depends(get_logic_bundle),
) -> ActorResponse:
    return ActorResponse.from_actor(logic.auth.get_current_actor(actor))


@router.post("/logout", response_model=LogoutResponse)
def logout(_: Actor = Depends(get_current_actor)) -> LogoutResponse:
    return LogoutResponse()
