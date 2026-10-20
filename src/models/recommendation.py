"""推荐计算输入及进程内快照；构建函数保证映射及嵌套值只读。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from src.models.contracts import CourseTagView, CourseView


@dataclass(frozen=True, kw_only=True)
class RecommendationSignal:
    member_id: int
    course_id: int
    weight: float


@dataclass(frozen=True, kw_only=True)
class RecommendationSource:
    as_of: datetime
    courses: tuple[CourseView, ...]
    signals: tuple[RecommendationSignal, ...]
    tags: tuple[CourseTagView, ...]


@dataclass(frozen=True, kw_only=True)
class RecommendationSnapshot:
    generated_at: datetime
    course_vectors: Mapping[int, tuple[float, ...]]
    member_vectors: Mapping[int, tuple[float, ...]]
    member_weights: Mapping[int, tuple[tuple[int, float], ...]]
    cooccurrence: Mapping[int, Mapping[int, int]]
    popularity: Mapping[int, int]
    course_tags: Mapping[int, tuple[str, ...]]
