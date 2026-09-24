"""统一导出异常类型与处理入口；处理行为仍待实现。"""

from .base import ErrorAction, ErrorResult, GymError
from .business import (
    AuthenticationError,
    CapacityExceeded,
    CardNotEligible,
    ConflictError,
    InputCancelled,
    InsufficientCredits,
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
    ScheduleConflict,
)
from .handler import handle_error
from .storage import MigrationError, OutcomeUnknownError, StorageError

__all__ = [
    "ErrorAction",
    "ErrorResult",
    "GymError",
    "InvalidInputError",
    "AuthenticationError",
    "PermissionDenied",
    "NotFoundError",
    "InvalidState",
    "ConflictError",
    "CardNotEligible",
    "InsufficientCredits",
    "ScheduleConflict",
    "CapacityExceeded",
    "InputCancelled",
    "OutcomeUnknownError",
    "StorageError",
    "MigrationError",
    "handle_error",
]
