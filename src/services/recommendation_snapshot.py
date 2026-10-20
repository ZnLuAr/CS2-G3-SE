"""推荐纯计算占位与跨查询、后台刷新共用的快照存储。"""

from __future__ import annotations

from threading import Lock

from src.models.recommendation import RecommendationSnapshot, RecommendationSource


def build_recommendation_snapshot(
    source: RecommendationSource,
) -> RecommendationSnapshot:
    """从同一读取快照构建共现、画像及向量；输出内部映射与向量只读。

    计算在数据库 Session 关闭后执行；失败抛 ResourceError，由 Logic 保留旧快照。
    当前算法尚未实现，调用抛 NotImplementedError。
    """
    raise NotImplementedError("推荐快照计算尚未实现")


class RecommendationSnapshotStore:
    """只同步引用与刷新请求；数据库读取和计算在锁外进行。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot: RecommendationSnapshot | None = None
        self._refresh_requested = True

    def current(self) -> RecommendationSnapshot | None:
        """返回当前完整快照；首次构建前返回 None，不修改业务数据。"""
        with self._lock:
            return self._snapshot

    def replace(self, snapshot: RecommendationSnapshot) -> None:
        """交换已完整构建的只读快照；保留构建期间到达的刷新请求。"""
        with self._lock:
            self._snapshot = snapshot

    def request_refresh(self) -> None:
        """合并标签变化或过期触发的刷新请求，由下次 Worker 回调接收。"""
        with self._lock:
            self._refresh_requested = True

    def take_refresh_request(self) -> bool:
        """构建前原子读取并清除当前请求；构建失败时 Logic 再次申请。"""
        with self._lock:
            requested = self._refresh_requested
            self._refresh_requested = False
            return requested
