"""统一导出异常类型与处理入口。"""

from .base import ErrorAction, ErrorResult, GymError
from .business import (
    AuthenticationError,
    BookingEntryNotEligible,
    CapacityExceeded,
    CardNotEligible,
    ConflictError,
    GymCardNotEligible,
    InputCancelled,
    InsufficientCredits,
    InsufficientLessonCredits,
    InvalidInputError,
    InvalidState,
    LessonPackageNotEligible,
    NotFoundError,
    PermissionDenied,
    ResourceError,
    ScheduleConflict,
)
from .handler import handle_error
from .storage import InitializationError, OutcomeUnknownError, StorageError

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
    "GymCardNotEligible",
    "BookingEntryNotEligible",
    "LessonPackageNotEligible",
    "InsufficientLessonCredits",
    "CardNotEligible",
    "InsufficientCredits",
    "ScheduleConflict",
    "CapacityExceeded",
    "InputCancelled",
    "ResourceError",
    "OutcomeUnknownError",
    "StorageError",
    "InitializationError",
    "handle_error",
]
