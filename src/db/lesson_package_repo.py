"""私教课包数据访问；余额更新不自行提交。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, insert, select, update

from src.db.support import from_db_utc, utc_now, validate_paging
from src.db.tables import lesson_packages
from src.errors.business import InsufficientCredits, InvalidState, NotFoundError
from src.errors.storage import StorageError
from src.models.contracts import (
    LessonPackageCreate, LessonPackageQuery, LessonPackageStatus,
)
from src.models.lesson_package import LessonPackage

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _model(row) -> LessonPackage:
    remaining = int(row["remaining_lessons"])
    reserved = int(row["reserved_lessons"])
    return LessonPackage(
        id=int(row["id"]), member_id=int(row["member_id"]), product_id=int(row["product_id"]),
        purchase_sale_item_id=int(row["purchase_sale_item_id"]), name=row["name"],
        total_lessons=int(row["total_lessons"]), remaining_lessons=remaining,
        reserved_lessons=reserved, available_lessons=remaining - reserved,
        valid_from=row["valid_from"], valid_until=row["valid_until"], status=row["status"],
        created_at=from_db_utc(row["created_at"]), updated_at=from_db_utc(row["updated_at"]),
    )


class LessonPackageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data: LessonPackageCreate) -> LessonPackage:
        now = utc_now()
        result = self._session.execute(insert(lesson_packages).values(
            member_id=data.member_id, product_id=data.product_id,
            purchase_sale_item_id=data.purchase_sale_item_id, name=data.name,
            total_lessons=data.total_lessons, remaining_lessons=data.remaining_lessons,
            reserved_lessons=data.reserved_lessons, valid_from=data.valid_from,
            valid_until=data.valid_until, status=data.status,
            created_at=now, updated_at=now,
        ))
        view = self.get(int(result.inserted_primary_key[0]))
        if view is None:
            raise StorageError("保存私教课包失败")
        return view

    def get(self, lesson_package_id: int) -> LessonPackage | None:
        row = self._session.execute(
            select(lesson_packages).where(lesson_packages.c.id == lesson_package_id)
        ).mappings().first()
        return None if row is None else _model(row)

    def lock(self, lesson_package_id: int) -> LessonPackage | None:
        row = self._session.execute(
            select(lesson_packages).where(
                lesson_packages.c.id == lesson_package_id
            ).with_for_update()
        ).mappings().first()
        return None if row is None else _model(row)

    def list(self, query: LessonPackageQuery) -> tuple[list[LessonPackage], int]:
        page, size = validate_paging(query.paging)
        conditions = []
        if query.member_id is not None:
            conditions.append(lesson_packages.c.member_id == query.member_id)
        if query.status is not None:
            conditions.append(lesson_packages.c.status == query.status)
        if query.valid_on is not None:
            conditions.extend((
                lesson_packages.c.valid_from <= query.valid_on,
                (lesson_packages.c.valid_until.is_(None))
                | (lesson_packages.c.valid_until > query.valid_on),
            ))
        if query.expires_before is not None:
            conditions.append(lesson_packages.c.valid_until < query.expires_before)
        if query.available_lessons_at_most is not None:
            conditions.append(
                lesson_packages.c.remaining_lessons - lesson_packages.c.reserved_lessons
                <= query.available_lessons_at_most
            )
        total = int(self._session.scalar(
            select(func.count()).select_from(lesson_packages).where(*conditions)
        ) or 0)
        rows = self._session.execute(
            select(lesson_packages).where(*conditions).order_by(lesson_packages.c.id)
            .limit(size).offset((page - 1) * size)
        ).mappings().all()
        return [_model(row) for row in rows], total

    def reserve_one(self, lesson_package_id: int) -> LessonPackage:
        result = self._session.execute(
            update(lesson_packages).where(
                lesson_packages.c.id == lesson_package_id,
                lesson_packages.c.status == "active",
                lesson_packages.c.remaining_lessons - lesson_packages.c.reserved_lessons >= 1,
            ).values(
                reserved_lessons=lesson_packages.c.reserved_lessons + 1,
                updated_at=utc_now(),
            )
        )
        if result.rowcount == 0:
            raise InsufficientCredits("私教课节不足")
        view = self.get(lesson_package_id)
        if view is None:
            raise StorageError("读取私教课包失败")
        return view

    def release_one(self, lesson_package_id: int) -> LessonPackage:
        result = self._session.execute(
            update(lesson_packages).where(
                lesson_packages.c.id == lesson_package_id,
                lesson_packages.c.reserved_lessons >= 1,
            ).values(
                reserved_lessons=lesson_packages.c.reserved_lessons - 1,
                updated_at=utc_now(),
            )
        )
        if result.rowcount == 0:
            raise InvalidState("课包占用与实际不一致")
        view = self.get(lesson_package_id)
        if view is None:
            raise StorageError("读取私教课包失败")
        return view

    def consume_reserved_one(self, lesson_package_id: int) -> LessonPackage:
        result = self._session.execute(
            update(lesson_packages).where(
                lesson_packages.c.id == lesson_package_id,
                lesson_packages.c.remaining_lessons >= 1,
                lesson_packages.c.reserved_lessons >= 1,
            ).values(
                remaining_lessons=lesson_packages.c.remaining_lessons - 1,
                reserved_lessons=lesson_packages.c.reserved_lessons - 1,
                updated_at=utc_now(),
            )
        )
        if result.rowcount == 0:
            raise InvalidState("课包余额或占用不一致")
        view = self.get(lesson_package_id)
        if view is None:
            raise StorageError("读取私教课包失败")
        return view

    def set_status(self, lesson_package_id: int, status: LessonPackageStatus) -> LessonPackage:
        result = self._session.execute(update(lesson_packages).where(
            lesson_packages.c.id == lesson_package_id
        ).values(status=status, updated_at=utc_now()))
        if result.rowcount == 0:
            raise NotFoundError("私教课包不存在")
        view = self.get(lesson_package_id)
        if view is None:
            raise NotFoundError("私教课包不存在")
        return view
