"""JWT 访问令牌签发与校验。"""

from __future__ import annotations

from datetime import datetime, timezone
import os

import jwt

from src.config import WebConfig
from src.errors.business import AuthenticationError, InvalidInputError
from src.models.contracts import Actor


_ROLES = {"member", "coach", "receptionist", "admin"}


class TokenManager:
    """使用 HS256 签名并校验受众、签发者和时效。"""

    def __init__(self, secret: str, settings: WebConfig) -> None:
        if len(secret.encode("utf-8")) < 32:
            raise InvalidInputError("Web API 签名密钥至少需要 32 字节")
        self._secret = secret
        self._issuer = settings.issuer
        self._audience = settings.audience
        self._lifetime_seconds = settings.token_lifetime_seconds

    @classmethod
    def from_environment(cls, settings: WebConfig) -> TokenManager:
        secret = os.environ.get(settings.jwt_secret_env_var)
        if secret is None:
            raise InvalidInputError(
                f"请设置 Web API 签名密钥环境变量：{settings.jwt_secret_env_var}"
            )
        return cls(secret, settings)

    def issue(self, actor: Actor) -> tuple[str, datetime]:
        now = int(datetime.now(timezone.utc).timestamp())
        expires_at = datetime.fromtimestamp(now + self._lifetime_seconds, timezone.utc)
        payload = {
            "sub": str(actor.account_id),
            "role": actor.role,
            "member_id": actor.member_id,
            "coach_id": actor.coach_id,
            "iss": self._issuer,
            "aud": self._audience,
            "iat": now,
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256"), expires_at

    def decode(self, token: str) -> Actor:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub", "role", "iat", "exp"]},
            )
            return _actor_from_claims(payload)
        except (jwt.InvalidTokenError, TypeError, ValueError) as exc:
            raise AuthenticationError("身份凭据无效或已过期") from exc


def _actor_from_claims(payload: dict[str, object]) -> Actor:
    # 档案声明必须存在；会员的 coach_id、教练的 member_id 及员工档案值允许为空。
    if "member_id" not in payload or "coach_id" not in payload:
        raise ValueError("令牌缺少档案声明")
    subject = payload.get("sub")
    role = payload.get("role")
    if not isinstance(subject, str) or not subject.isdecimal() or role not in _ROLES:
        raise ValueError("令牌身份字段无效")
    account_id = int(subject)
    member_id = _optional_positive_id(payload.get("member_id"))
    coach_id = _optional_positive_id(payload.get("coach_id"))
    if account_id <= 0:
        raise ValueError("令牌账号编号无效")
    if role == "member" and (member_id is None or coach_id is not None):
        raise ValueError("令牌会员身份无效")
    if role == "coach" and (coach_id is None or member_id is not None):
        raise ValueError("令牌教练身份无效")
    if role in {"receptionist", "admin"} and (member_id is not None or coach_id is not None):
        raise ValueError("令牌员工身份无效")
    return Actor(
        account_id=account_id,
        role=role,  # type: ignore[arg-type]
        member_id=member_id,
        coach_id=coach_id,
    )


def _optional_positive_id(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("令牌档案编号无效")
    return value
