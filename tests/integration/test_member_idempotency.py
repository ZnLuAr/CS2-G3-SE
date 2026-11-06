"""MEM-01 / TEST-06：重复请求并发写入时验证回滚和结果重放。"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock, local

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import LogConfig
from src.db.operation_repo import OperationRepository
from src.errors import ConflictError
from src.logic.member_logic import MemberLogic
from src.models.contracts import Actor, MemberInput
from src.services.auth_service import AuthService
from src.services.member_service import MemberService


REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
ACTORS = (
    Actor(account_id=1, role="receptionist", member_id=None, coach_id=None),
    Actor(account_id=2, role="receptionist", member_id=None, coach_id=None),
)


class _UnlockedAuth:
    """让同一账号的请求同时越过身份锁，单独验证唯一键竞态。"""

    def verify_actor(self, session, actor):
        return actor


@pytest.mark.parametrize("case", ["same_request", "different_payload", "different_actor"])
def test_concurrent_duplicate_request_rolls_back_and_replays(
    initialized_mysql_database, monkeypatch, case,
):
    engine = initialized_mysql_database
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO accounts (id,username,password_hash,role) VALUES "
            "(1,'member_reception_1','test-unused','receptionist'),"
            "(2,'member_reception_2','test-unused','receptionist')"
        ))

    # 同账号的真实身份复核会串行化；替身使两次相同账号请求也能覆盖唯一键竞态。
    # 不同账号的场景使用真实身份复核，覆盖生产调用路径。
    auth = AuthService(log_config=LogConfig()) if case == "different_actor" else _UnlockedAuth()
    logic = MemberLogic(lambda: Session(engine), MemberService(auth))
    actors = (ACTORS[0], ACTORS[1] if case == "different_actor" else ACTORS[0])
    inputs = (
        MemberInput(name="Concurrent member", phone=None),
        MemberInput(name="Other member" if case == "different_payload" else "Concurrent member", phone=None),
    )

    barrier = Barrier(2, timeout=15)
    thread_state = local()
    original_get = OperationRepository.get_by_request

    def synchronize_first_miss(repository, request_id):
        record = original_get(repository, request_id)
        if record is None and not getattr(thread_state, "synchronized", False):
            thread_state.synchronized = True
            barrier.wait()
        return record

    monkeypatch.setattr(OperationRepository, "get_by_request", synchronize_first_miss)
    original_attempt = logic._create_member_once
    failures = []
    failures_lock = Lock()

    def count_duplicate_failures(*args):
        try:
            return original_attempt(*args)
        except IntegrityError as exc:
            with failures_lock:
                failures.append(exc.orig.args[0])
            raise

    monkeypatch.setattr(logic, "_create_member_once", count_duplicate_failures)

    def create(index):
        try:
            return logic.create_member(actors[index], inputs[index], REQUEST_ID)
        except ConflictError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create, index) for index in range(2)]
        results = [future.result(timeout=30) for future in futures]

    assert failures == [1062]  # 两次都先查不到请求，后到事务确实撞上唯一键。
    winners = [result for result in results if not isinstance(result, ConflictError)]
    if case == "same_request":
        assert len(winners) == 2
        assert winners[0] == winners[1]
    else:
        assert len(winners) == 1
        assert sum(isinstance(result, ConflictError) for result in results) == 1

    with Session(engine) as session:
        members = session.execute(text("SELECT id, name FROM members")).all()
        operations = session.execute(text(
            "SELECT actor_id, result_id FROM operation_records WHERE request_id = :request_id"
        ), {"request_id": REQUEST_ID}).all()
    assert members == [(winners[0].id, winners[0].name)]
    assert len(operations) == 1 and operations[0].result_id == winners[0].id
    winner_actor = next(actor for actor in actors if actor.account_id == operations[0].actor_id)
    assert logic.get_member_by_request(winner_actor, REQUEST_ID) == winners[0]
