"""HTTP 请求与响应类型。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator

from src.errors.base import ErrorAction
from src.models.contracts import Actor, Role


def _validate_business_id(value: str) -> str:
    """业务编号保留 BIGINT 精度，范围为 1～2^63-1。"""
    if int(value) > 2**63 - 1:
        raise ValueError("业务编号超出范围")
    return value


BusinessId = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[1-9][0-9]{0,18}$"),
    AfterValidator(_validate_business_id),
]


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class LoginRequest(ApiModel):
    username: str = Field(min_length=3, max_length=50)
    password: SecretStr = Field(min_length=6, max_length=32, repr=False)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if re.fullmatch(r"[a-z0-9_]{3,50}", normalized) is None:
            raise ValueError("用户名格式不正确")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_format(cls, value: SecretStr) -> SecretStr:
        if re.fullmatch(r"[A-Za-z0-9_-]{6,32}", value.get_secret_value()) is None:
            raise ValueError("密码格式不正确")
        return value


class ActorResponse(ApiModel):
    account_id: BusinessId
    role: Role
    member_id: BusinessId | None
    coach_id: BusinessId | None

    @classmethod
    def from_actor(cls, actor: Actor) -> ActorResponse:
        return cls(
            account_id=str(actor.account_id),
            role=actor.role,
            member_id=str(actor.member_id) if actor.member_id is not None else None,
            coach_id=str(actor.coach_id) if actor.coach_id is not None else None,
        )


class LoginResponse(ApiModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    actor: ActorResponse


class LogoutResponse(ApiModel):
    logged_out: Literal[True] = True


class ApiErrorResponse(ApiModel):
    """全部 HTTP 失败共用的安全字段和恢复动作。"""

    message: str
    action: ErrorAction
    error_type: str
    request_id: str | None = None
    record_id: BusinessId | None = None
