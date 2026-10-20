"""验证刷新期间的请求不会随快照交换丢失；不验证尚未实现的推荐算法。"""

from datetime import datetime, timezone
from types import MappingProxyType

from src.models.recommendation import RecommendationSnapshot
from src.services.recommendation_snapshot import RecommendationSnapshotStore


def test_refresh_requested_during_build_survives_snapshot_replacement():
    store = RecommendationSnapshotStore()
    assert store.current() is None
    assert store.take_refresh_request() is True

    # Worker 已开始计算本轮输入，管理员随后修改标签。
    store.request_refresh()
    empty = MappingProxyType({})
    snapshot = RecommendationSnapshot(
        generated_at=datetime.now(timezone.utc),
        course_vectors=empty, member_vectors=empty, member_weights=empty,
        cooccurrence=empty, popularity=empty, course_tags=empty,
    )
    store.replace(snapshot)

    assert store.current() is snapshot
    assert store.take_refresh_request() is True
    assert store.take_refresh_request() is False
