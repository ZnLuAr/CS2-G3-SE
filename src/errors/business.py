"""业务错误与交互取消的类型。"""

from __future__ import annotations

from src.errors.base import GymError


class InvalidInputError(GymError):
    """输入类型、长度或范围不合法。"""


class AuthenticationError(GymError):
    """登录失败或当前登录身份失效。"""


class PermissionDenied(GymError):
    """当前角色没有执行该操作的权限。"""


class NotFoundError(GymError):
    """目标记录不存在或对操作者不可见。"""


class InvalidState(GymError):
    """当前业务状态不允许该操作。"""


class ConflictError(GymError):
    """唯一数据、重复请求或请求内容冲突。"""


class GymCardNotEligible(GymError):
    """已确认归属的健身房卡状态或日期不满足入场。"""


class BookingEntryNotEligible(GymError):
    """已确认归属的预约状态或业务日期不满足入场。"""


class LessonPackageNotEligible(GymError):
    """已确认归属的课包状态或课次日期不满足预约。"""


class InsufficientLessonCredits(GymError):
    """私教课包可用课节不足。"""


class ScheduleConflict(GymError):
    """会员、教练或场地时间冲突。"""


class CapacityExceeded(GymError):
    """课次没有可用名额。"""


class InputCancelled(Exception):
    """用户主动取消输入；后续统一处理时不记为业务错误。"""


class ResourceError(GymError):
    """文件、终端能力或外部工具不可用。"""


# 兼容仓库内较早使用的短名称；新代码使用架构分册中的完整名称。
CardNotEligible = GymCardNotEligible
InsufficientCredits = InsufficientLessonCredits
