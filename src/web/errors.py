"""项目异常和请求校验错误的 HTTP 映射。"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from src.errors.base import ErrorAction, GymError
from src.errors.business import (
    AuthenticationError,
    CapacityExceeded,
    CardNotEligible,
    ConflictError,
    InsufficientCredits,
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
    ResourceError,
    ScheduleConflict,
)
from src.errors.storage import OutcomeUnknownError, StorageError
from src.web.schemas import ApiErrorResponse


def register_error_handlers(application: FastAPI) -> None:
    application.add_exception_handler(GymError, gym_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)


async def gym_error_handler(_: Request, error: GymError) -> JSONResponse:
    if isinstance(error, OutcomeUnknownError):
        status, action = 503, "verify"
    elif isinstance(error, AuthenticationError):
        status, action = 401, "login"
    elif isinstance(error, PermissionDenied):
        status, action = 403, "continue"
    elif isinstance(error, NotFoundError):
        status, action = 404, "continue"
    elif isinstance(error, InvalidInputError):
        status, action = 422, "continue"
    elif isinstance(error, StorageError | ResourceError):
        status, action = 503, "exit"
    elif isinstance(
        error,
        (ConflictError, InvalidState, CapacityExceeded, CardNotEligible,
         InsufficientCredits, ScheduleConflict),
    ):
        status, action = 409, "continue"
    else:
        status, action = 500, "exit"
    message = error.message if status < 500 else "服务暂时不可用，请联系维护人员检查。"
    return JSONResponse(
        status_code=status,
        content=_error_payload(
            message=message,
            action=action,
            error_type=type(error).__name__,
            request_id=error.request_id if isinstance(error, OutcomeUnknownError) else None,
            record_id=error.record_id if isinstance(error, OutcomeUnknownError) else None,
        ),
    )


async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    fields = []
    for detail in error.errors():
        path = [str(part) for part in detail.get("loc", ()) if part not in {"body", "query", "path"}]
        fields.append(".".join(path))
    return JSONResponse(
        status_code=422,
        content={
            **_error_payload(
                message="请求字段格式不正确",
                action="continue",
                error_type="RequestValidationError",
            ),
            "fields": fields,
        },
    )


async def http_error_handler(_: Request, error: HTTPException) -> JSONResponse:
    """把路由缺失和方法不匹配等 HTTP 错误转为统一响应。"""
    message = {
        404: "请求地址不存在",
        405: "请求方法不支持",
    }.get(error.status_code, "请求无法完成")
    return JSONResponse(
        status_code=error.status_code,
        content=_error_payload(
            message=message,
            action="exit" if error.status_code >= 500 else "login" if error.status_code == 401 else "continue",
            error_type="HTTPException",
        ),
        headers=error.headers,
    )


async def unexpected_error_handler(_: Request, error: Exception) -> JSONResponse:
    logging.getLogger("src.web.errors").error(
        "Web API 请求失败",
        extra={"error_type": type(error).__name__},
    )
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            message="服务暂时不可用，请联系维护人员检查。",
            action="exit",
            error_type=type(error).__name__,
        ),
    )


def _error_payload(
    *,
    message: str,
    action: ErrorAction,
    error_type: str,
    request_id: str | None = None,
    record_id: int | None = None,
) -> dict[str, object]:
    return ApiErrorResponse(
        message=message,
        action=action,
        error_type=error_type,
        request_id=request_id,
        record_id=str(record_id) if record_id is not None else None,
    ).model_dump(by_alias=True)
