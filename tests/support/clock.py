"""单元测试共用的时间替身。"""

from __future__ import annotations

from datetime import datetime, timezone

# 带时区调用 now() 得到的约定时刻；不带时区调用得到另一个时刻，便于区分。
AWARE_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
NAIVE_NOW = datetime(2026, 1, 2)


class UtcClock(datetime):
    """替换 datetime.datetime：只有带 tz 调用 now() 才返回 AWARE_NOW。

    用来区分合同要求的 datetime.now(timezone.utc) 和依赖本机时区的 datetime.now()，
    断言结果与运行测试的机器时区无关。
    """

    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 1, 1, tzinfo=tz) if tz is not None else NAIVE_NOW
