"""预约业务服务实现。

预约把“课次名额”和“会员卡私教额度占用”放在同一个事务中：
- 成功：写一条预约，`reserved_private_lessons + 1`；
- 失败：两处都不留记录；
- 取消：预约改为 `cancelled`，额度占用减 1，实际剩余节数不变，消课时才扣剩余。

时间判断使用门店时区：课次按 UTC 保存，检查会员卡有效期时转换成门店日期，
再按 `valid_from <= 上课日期 < valid_until` 判断。这样上海时间 00:30 的课
归属当天，而不会因为 UTC 还是前一天而被误判为卡未生效。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import SQLAlchemyError

from src.db.booking_repo import (
    BookingRepository,
    lock_member,
    lock_memberships,
    release_private_lessons,
    reserve_private_lesson,
)
from src.db.course_repo import SessionRepository
from src.db.operation_repo import OperationRepository
from src.db.support import utc_now
from src.errors.base import GymError
from src.errors.business import (
    CapacityExceeded,
    CardNotEligible,
    ConflictError,
    InsufficientCredits,
    InvalidInputError,
    InvalidState,
    NotFoundError,
    PermissionDenied,
    ScheduleConflict,
)
from src.errors.storage import StorageError
from src.models.contracts import (
    Actor,
    BookingInput,
    BookingQuery,
    BookingView,
    DateWindow,
    Page,
)
from src.services.auth_service import AuthService
from src.services.idempotency import (
    ensure_replay_matches,
    payload_hash,
    validate_request_id,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

T = TypeVar("T")


def _read(
    session_factory: Callable[[], Session],
    auth: AuthService,
    actor: Actor,
    operation: Callable[[Session, Actor], T],
) -> T:
    """在只读会话中重验身份后执行查询；不提交事务。"""
    with session_factory() as session:
        current = auth.verify_actor(session, actor)
        return operation(session, current)


def _write(
    session_factory: Callable[[], Session],
    auth: AuthService,
    actor: Actor,
    operation: Callable[[Session, Actor], T],
    *,
    request_id: str,
) -> T:
    """在一个事务中重验身份、执行预约写操作并提交。

    取消或预约失败时业务记录和额度占用一起回滚；提交阶段的异常无法判断
    数据库是否已写入，因此抛 OutcomeUnknownError，让用户按原请求编号核实。
    """
    session = session_factory()
    committing = False
    try:
        session.begin()
        current = auth.verify_actor(session, actor)
        result = operation(session, current)
        committing = True
        session.commit()
        return result
    except GymError:
        session.rollback()
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        if committing:
            from src.errors.storage import OutcomeUnknownError

            raise OutcomeUnknownError(
                "提交结果待核实，请按原请求编号查询，不要直接重试",
                request_id=request_id,
            ) from exc
        raise StorageError("数据库操作失败，请稍后重试") from exc
    finally:
        session.close()


def _check_book_permission(actor: Actor, member_id: int) -> None:
    """预约权限：会员只能给自己约，前台和管理员可以代约，教练不能预约。"""
    if actor.role in ("receptionist", "admin"):
        return
    if actor.role == "member" and actor.member_id == member_id:
        return
    raise PermissionDenied("只能为自己预约课次")


def _check_cancel_permission(actor: Actor, view: BookingView) -> None:
    """取消权限：会员只能取消自己的，前台和管理员可以代取消。"""
    if actor.role in ("receptionist", "admin"):
        return
    if actor.role == "member" and actor.member_id == view.member_id:
        return
    raise PermissionDenied("只能取消自己的预约")


def _ensure_booking_visible(actor: Actor, view: BookingView) -> None:
    """检查预约可见范围；越权时抛 NotFoundError，不泄露记录是否存在。"""
    if actor.role in ("receptionist", "admin"):
        return
    if actor.role == "member":
        if actor.member_id is None or view.member_id != actor.member_id:
            raise NotFoundError("预约不存在")
        return
    if actor.role == "coach":
        if actor.coach_id is None or view.session.coach_id != actor.coach_id:
            raise NotFoundError("预约不存在")
        return
    raise PermissionDenied("当前角色不能查看预约")


def _book_payload(data: BookingInput) -> str:
    """预约请求摘要：会员、课次和会员卡必须完全一致才能复用请求编号。"""
    return payload_hash({
        "member_id": data.member_id,
        "session_id": data.session_id,
        "membership_id": data.membership_id,
    })


class BookingService:
    """预约服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；异常和事务约定见设计第 4 节。
    """

    def __init__(
        self, session_factory: Callable[[], Session], auth: AuthService,
        *, timezone_name: str,
    ) -> None:
        """接收会话工厂、共用身份校验服务和门店时区；时区由 App 配置传入。"""
        try:
            self._timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise InvalidInputError("门店时区配置无效") from exc
        self._session_factory = session_factory
        self._auth = auth

    def book(self, actor: Actor, data: BookingInput, request_id: str) -> BookingView:
        """校验权限、私教课次时间和私教节数；同事务保存预约与节数占用。

        membership_id 固定为提供资格及赠课的同一张卡，不得组合旧赠课与新门禁卡。
        对期限卡按课次开始时刻转门店日期检查 valid_from <= 上课日期 < valid_until。
        次卡不能约私教；未来生效的期限卡可约其有效期内的课，失败不写预约或占用余额。
        卡不适用抛 CardNotEligible；私教节数不足抛 InsufficientCredits；
        撞期抛 ScheduleConflict；满员抛 CapacityExceeded；已有预约抛 ConflictError。
        """
        request_id = validate_request_id(request_id)
        payload = _book_payload(data)

        def action(session: Session, current: Actor) -> BookingView:
            _check_book_permission(current, data.member_id)

            operations = OperationRepository(session)
            existing = operations.get_by_request(request_id)
            if existing is not None:
                ensure_replay_matches(
                    existing,
                    actor_id=current.account_id,
                    operation="book",
                    payload=payload,
                )
                view = BookingRepository(session).get(existing.result_id)
                if view is None:
                    raise ConflictError("原预约记录不存在，请核实请求编号")
                return view

            member = lock_member(session, data.member_id)
            if member is None:
                raise NotFoundError("会员不存在")
            if not member["is_active"]:
                raise InvalidState("会员档案已停用，不能预约")
            if member["account_active"] is not None and not member["account_active"]:
                raise InvalidState("会员账号已停用，不能预约")

            repo = BookingRepository(session)
            session_repo = SessionRepository(session)
            course_session = session_repo.lock(data.session_id)
            if course_session is None:
                raise NotFoundError("课次不存在")
            if course_session.status != "scheduled":
                raise InvalidState("课次已取消或已完成，不能预约")
            now = utc_now()
            if course_session.starts_at <= now:
                raise InvalidState("课次已开始，不能预约")

            # 先判断重复预约，再判断满员：会员重复提交同一课次应得到“已预约过”
            # 的明确提示，而不是被自己的占位误报为满员。
            if repo.find_for_member_session(data.member_id, data.session_id) is not None:
                raise ConflictError("该会员已预约过此课次")
            if repo.count_occupied(data.session_id) >= course_session.capacity:
                raise CapacityExceeded("课次已满员")
            if repo.has_member_conflict(
                data.member_id,
                DateWindow(
                    start=course_session.starts_at,
                    end=course_session.ends_at,
                ),
            ):
                raise ScheduleConflict("会员在该时段已有其他预约")

            cards = lock_memberships(session, [data.membership_id])
            card = cards.get(data.membership_id)
            if card is None:
                raise NotFoundError("会员卡不存在")
            if int(card["member_id"]) != data.member_id:
                raise CardNotEligible("会员卡不属于该会员")
            if card["status"] != "active":
                raise CardNotEligible("会员卡已作废")
            if card["kind"] == "count":
                raise CardNotEligible("次卡不能预约私教课")
            if card["kind"] not in ("monthly", "quarterly", "yearly"):
                raise CardNotEligible("会员卡类型不支持私教预约")
            class_date = course_session.starts_at.astimezone(self._timezone).date()
            if card["valid_from"] is None or class_date < card["valid_from"]:
                raise CardNotEligible("会员卡尚未生效")
            if card["valid_until"] is None or class_date >= card["valid_until"]:
                raise CardNotEligible("上课日期不在会员卡有效期内")
            if (
                int(card["remaining_private_lessons"])
                - int(card["reserved_private_lessons"])
                <= 0
            ):
                raise InsufficientCredits("私教节数不足")

            reserve_private_lesson(session, data.membership_id)
            view = repo.create(data, now)
            operations.create(
                request_id=request_id,
                actor_id=current.account_id,
                operation="book",
                payload_hash=payload,
                result_id=view.id,
            )
            return view

        return _write(
            self._session_factory, self._auth, actor, action, request_id=request_id,
        )

    def get_booking(self, actor: Actor, booking_id: int) -> BookingView:
        """查询预约详情。

        返回：BookingView。不修改业务数据；会员只能查自己的，教练只能查
        自己课次的预约，前台和管理员可以查全部。
        """
        def action(session: Session, current: Actor) -> BookingView:
            view = BookingRepository(session).get(booking_id)
            if view is None:
                raise NotFoundError("预约不存在")
            _ensure_booking_visible(current, view)
            return view

        return _read(self._session_factory, self._auth, actor, action)

    def get_booking_by_request(self, actor: Actor, request_id: str) -> BookingView:
        """按本人原预约或取消请求核实结果，返回当前 BookingView。

        不写数据；无记录或不可见抛 NotFoundError，操作类型不匹配抛 ConflictError。
        查不到不能证明原提交失败；其余异常按设计第 4.1 节。
        """
        request_id = validate_request_id(request_id)

        def action(session: Session, current: Actor) -> BookingView:
            record = OperationRepository(session).get_by_request(request_id)
            if record is None:
                raise NotFoundError("没有该请求编号的记录")
            if record.actor_id != current.account_id:
                raise NotFoundError("没有该请求编号的记录")
            if record.operation not in ("book", "cancel_booking"):
                raise ConflictError("该请求编号属于其他操作")
            view = BookingRepository(session).get(record.result_id)
            if view is None:
                raise NotFoundError("预约不存在")
            _ensure_booking_visible(current, view)
            return view

        return _read(self._session_factory, self._auth, actor, action)

    def cancel(self, actor: Actor, booking_id: int, request_id: str) -> BookingView:
        """在私教课开始前取消未签到预约并释放私教节数占用。

        返回：BookingView。在同一服务事务中修改对应记录，失败清理后抛异常。
        """
        request_id = validate_request_id(request_id)
        payload = payload_hash({"booking_id": booking_id})

        def action(session: Session, current: Actor) -> BookingView:
            operations = OperationRepository(session)
            existing = operations.get_by_request(request_id)
            if existing is not None:
                ensure_replay_matches(
                    existing,
                    actor_id=current.account_id,
                    operation="cancel_booking",
                    payload=payload,
                )
                view = BookingRepository(session).get(existing.result_id)
                if view is None:
                    raise ConflictError("原取消记录不存在，请核实请求编号")
                return view

            repo = BookingRepository(session)
            view = repo.get(booking_id)
            if view is None:
                raise NotFoundError("预约不存在")
            _check_cancel_permission(current, view)

            # 锁顺序：课次 → 会员卡 → 预约，与预约创建和取消课次保持一致。
            course_session = SessionRepository(session).lock(view.session.id)
            if course_session is None:
                raise StorageError("预约关联的课次不存在，请核实数据")
            if course_session.status == "cancelled":
                raise InvalidState("课次已取消，预约不能再取消")

            cards = lock_memberships(session, [view.membership_id])
            if view.membership_id not in cards:
                raise StorageError("预约关联的会员卡不存在，请核实数据")
            locked = repo.lock(booking_id)
            if locked is None:
                raise NotFoundError("预约不存在")
            if locked.membership_id != view.membership_id:
                cards.update(lock_memberships(session, [locked.membership_id]))
                if locked.membership_id not in cards:
                    raise StorageError("预约关联的会员卡不存在，请核实数据")

            if locked.status != "reserved":
                raise InvalidState("已签到、已完成或已取消的预约不能取消")
            now = utc_now()
            if course_session.starts_at <= now:
                raise InvalidState("课次已开始，不能取消预约")

            release_private_lessons(session, locked.membership_id)
            result = repo.set_state(
                locked.id,
                status="cancelled",
                checked_in_at=None,
                closed_at=now,
            )
            operations.create(
                request_id=request_id,
                actor_id=current.account_id,
                operation="cancel_booking",
                payload_hash=payload,
                result_id=result.id,
            )
            return result

        return _write(
            self._session_factory, self._auth, actor, action, request_id=request_id,
        )

    def list_bookings(self, actor: Actor, query: BookingQuery) -> Page[BookingView]:
        """在授权范围内分页查询预约。

        会员只能查自己的；教练只能查自己课次的学员名单；前台和管理员可以查全部。
        返回：Page[BookingView]。不修改业务数据。
        """
        def action(session: Session, current: Actor) -> Page[BookingView]:
            scope_member_id: int | None = None
            scope_coach_id: int | None = None
            if current.role == "member":
                if current.member_id is None:
                    raise PermissionDenied("当前账号未关联会员档案")
                if query.member_id is not None and query.member_id != current.member_id:
                    raise PermissionDenied("会员只能查看自己的预约")
                scope_member_id = current.member_id
            elif current.role == "coach":
                if current.coach_id is None:
                    raise PermissionDenied("当前账号未关联教练档案")
                scope_coach_id = current.coach_id
            elif current.role not in ("receptionist", "admin"):
                raise PermissionDenied("当前角色不能查询预约")
            return BookingRepository(session).list(
                query,
                scope_member_id=scope_member_id,
                scope_coach_id=scope_coach_id,
            )

        return _read(self._session_factory, self._auth, actor, action)
