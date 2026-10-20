"""HTTP 请求级 Logic 与身份依赖。"""

from __future__ import annotations

from fastapi import Request

from src.errors.business import AuthenticationError, InvalidState
from src.logic import LogicBundle
from src.models.contracts import Actor
from src.web.security import TokenManager


def get_logic_bundle(request: Request) -> LogicBundle:
    runtime = getattr(request.app.state, "application", None)
    if runtime is None:
        raise InvalidState("应用尚未启动")
    return runtime.logic_bundle


def get_current_actor(request: Request) -> Actor:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token or " " in token:
        raise AuthenticationError("请使用有效的 Bearer 访问令牌")
    manager: TokenManager | None = getattr(request.app.state, "token_manager", None)
    if manager is None:
        raise InvalidState("身份服务尚未启动")
    return manager.decode(token)
