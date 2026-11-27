"""MEM-02 / MEM-03 / MEM-04：在 MySQL 结构上验证会员列表筛选分页、改资料与时间戳。"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import LogConfig
from src.errors import InvalidInputError, NotFoundError, PermissionDenied
from src.logic.member_logic import MemberLogic
from src.models.contracts import Actor, MemberInput, MemberQuery, PageRequest
from src.services.auth_service import AuthService
from src.services.member_service import MemberService

# 种子档案的时间戳固定在过去，和仓储按当前 UTC 写入的时间戳区分开。
PAST = datetime(2026, 1, 1, 0, 0, 0)
RECEPTIONIST = Actor(account_id=1, role="receptionist", member_id=None, coach_id=None)
MEMBER = Actor(account_id=2, role="member", member_id=10, coach_id=None)
COACH = Actor(account_id=3, role="coach", member_id=None, coach_id=30)
ADMIN = Actor(account_id=4, role="admin", member_id=None, coach_id=None)
REQUEST_ID = "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"

# 姓名 11 含 LIKE 通配符字面量；姓名 12 含 "50xy"，用来证明 % 与 _ 按字面量匹配：
# 关键字 "50%" 和 "_x" 不应命中它。
SEEDED_NAMES = {10: "Alice", 11: "Bob 50%_\\", 12: "Carol 50xy", 13: "Alice Chen", 14: "Eve"}


def _seed(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO accounts (id,username,password_hash,role) VALUES "
            "(1,'profile_reception','test-unused','receptionist'),"
            "(2,'profile_member','test-unused','member'),"
            "(3,'profile_coach','test-unused','coach'),"
            "(4,'profile_admin','test-unused','admin')"
        ))
        connection.execute(text("INSERT INTO coaches (id,name) VALUES (30,'Profile coach')"))
        connection.execute(text(
            "INSERT INTO members (id,name,phone,status,archived_at,created_at,updated_at) VALUES "
            "(10,:n10,'13800000010','active',NULL,:past,:past),"
            "(11,:n11,NULL,'active',NULL,:past,:past),"
            "(12,:n12,NULL,'active',NULL,:past,:past),"
            "(13,:n13,NULL,'active',NULL,:past,:past),"
            "(14,:n14,NULL,'archived',:past,:past,:past)"
        ), {"past": PAST, **{f"n{member_id}": name for member_id, name in SEEDED_NAMES.items()}})
        connection.execute(text(
            "INSERT INTO member_account_links (account_id,member_id,linked_at,linked_by) VALUES (2,10,:past,1)"
        ), {"past": PAST})
        connection.execute(text(
            "INSERT INTO coach_account_links (account_id,coach_id,linked_at,linked_by) VALUES (3,30,:past,1)"
        ), {"past": PAST})


def _logic(engine):
    return MemberLogic(lambda: Session(engine), MemberService(AuthService(log_config=LogConfig())))


def _ids(logic, actor, **query):
    page = logic.list_members(actor, MemberQuery(paging=PageRequest(), **query))
    return [view.id for view in page.items], page.total


def test_list_pages_and_filters_with_escaped_wildcards(initialized_mysql_database):
    engine = initialized_mysql_database
    _seed(engine)
    logic = _logic(engine)

    # 无条件：按 id 升序、总数与分页口径一致，越界页返回空 Page 但总数不变。
    assert _ids(logic, RECEPTIONIST) == ([10, 11, 12, 13, 14], 5)
    first = logic.list_members(RECEPTIONIST, MemberQuery(paging=PageRequest(page=1, page_size=2)))
    last = logic.list_members(RECEPTIONIST, MemberQuery(paging=PageRequest(page=3, page_size=2)))
    beyond = logic.list_members(RECEPTIONIST, MemberQuery(paging=PageRequest(page=4, page_size=2)))
    assert ([view.id for view in first.items], first.total, first.page, first.page_size) == ([10, 11], 5, 1, 2)
    assert ([view.id for view in last.items], last.total) == ([14], 5)
    assert ([view.id for view in beyond.items], beyond.total) == ([], 5)

    # 关键字按姓名包含匹配；输入里的 % 和 _ 按字面量处理（漏转义时会多出姓名 12）。
    assert _ids(logic, RECEPTIONIST, keyword="Alice") == ([10, 13], 2)
    assert _ids(logic, RECEPTIONIST, keyword="50%_\\") == ([11], 1)
    assert _ids(logic, RECEPTIONIST, keyword="50%") == ([11], 1)
    assert _ids(logic, RECEPTIONIST, keyword="_x") == ([], 0)
    assert _ids(logic, RECEPTIONIST, keyword="  50xy ") == ([12], 1)
    assert _ids(logic, RECEPTIONIST, keyword="nobody") == ([], 0)

    # 编号、状态、组合筛选，以及筛选与分页叠加。
    assert _ids(logic, RECEPTIONIST, member_id=12) == ([12], 1)
    assert _ids(logic, RECEPTIONIST, status="archived") == ([14], 1)
    assert _ids(logic, RECEPTIONIST, status="active") == ([10, 11, 12, 13], 4)
    assert _ids(logic, RECEPTIONIST, member_id=10, keyword="Alice", status="active") == ([10], 1)
    filtered = logic.list_members(
        RECEPTIONIST, MemberQuery(keyword="Alice", paging=PageRequest(page=2, page_size=1))
    )
    assert ([view.id for view in filtered.items], filtered.total) == ([13], 2)

    # 行映射：联系方式、归档时刻与时间戳（库内无时区 UTC 补回时区）。
    archived = logic.list_members(
        RECEPTIONIST, MemberQuery(status="archived", paging=PageRequest())
    ).items[0]
    assert archived.archived_at == PAST.replace(tzinfo=timezone.utc)
    assert first.items[0].phone == "13800000010"
    assert first.items[0].archived_at is None
    assert first.items[0].created_at == PAST.replace(tzinfo=timezone.utc)
    assert first.items[1].phone is None


def test_list_visibility_follows_roles(initialized_mysql_database):
    engine = initialized_mysql_database
    _seed(engine)
    logic = _logic(engine)

    # 会员只能查到本人；指定他人编号返回空 Page；详情同样按可见范围。
    assert _ids(logic, MEMBER) == ([10], 1)
    assert _ids(logic, MEMBER, keyword="Alice") == ([10], 1)
    assert _ids(logic, MEMBER, member_id=13) == ([], 0)
    assert logic.get_member(MEMBER, 10).created_at == PAST.replace(tzinfo=timezone.utc)
    with pytest.raises(NotFoundError):
        logic.get_member(MEMBER, 13)
    with pytest.raises(PermissionDenied):
        logic.list_members(COACH, MemberQuery(paging=PageRequest()))

    # 管理员可查看全部档案与任意详情。
    assert _ids(logic, ADMIN) == ([10, 11, 12, 13, 14], 5)
    assert logic.get_member(ADMIN, 13).name == "Alice Chen"


def test_update_profile_changes_only_name_and_phone(initialized_mysql_database):
    engine = initialized_mysql_database
    _seed(engine)
    logic = _logic(engine)
    before = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=2)

    view = logic.update_member(
        RECEPTIONIST, 10, MemberInput(name="  Alicia  ", phone=" 13900000001 ")
    )

    assert (view.id, view.name, view.phone) == (10, "Alicia", "13900000001")
    assert view.status == "active" and view.archived_at is None
    assert view.updated_at.tzinfo == timezone.utc
    assert before <= view.updated_at.replace(tzinfo=None) <= datetime.now(timezone.utc).replace(tzinfo=None)
    with Session(engine) as session:
        row = session.execute(text(
            "SELECT name,phone,status,archived_at,created_at,updated_at FROM members WHERE id = 10"
        )).mappings().one()
    assert row["name"] == "Alicia" and row["phone"] == "13900000001"
    assert row["status"] == "active" and row["archived_at"] is None
    assert row["created_at"] == PAST
    assert before <= row["updated_at"] <= datetime.now(timezone.utc).replace(tzinfo=None)
    assert row["updated_at"] == view.updated_at.replace(tzinfo=None)

    # phone=None 清空联系方式；其余档案的姓名与联系方式不受影响。
    cleared = logic.update_member(RECEPTIONIST, 10, MemberInput(name="Alicia", phone=None))
    assert (cleared.name, cleared.phone) == ("Alicia", None)
    with Session(engine) as session:
        assert session.execute(text("SELECT phone FROM members WHERE id = 10")).scalar_one() is None
    assert [(v.id, v.name, v.phone) for v in logic.list_members(
        RECEPTIONIST, MemberQuery(paging=PageRequest())
    ).items] == [
        (10, "Alicia", None), (11, "Bob 50%_\\", None), (12, "Carol 50xy", None),
        (13, "Alice Chen", None), (14, "Eve", None),
    ]

    # 非法输入在写库前被拒绝，旧值保持不变（MEM-03 验收）。
    with pytest.raises(InvalidInputError):
        logic.update_member(RECEPTIONIST, 10, MemberInput(name="Broken", phone=""))
    kept = logic.get_member(RECEPTIONIST, 10)
    assert (kept.name, kept.phone) == ("Alicia", None)

    with pytest.raises(NotFoundError):
        logic.update_member(RECEPTIONIST, 999, MemberInput(name="Nobody", phone=None))
    with pytest.raises(PermissionDenied):
        logic.update_member(MEMBER, 10, MemberInput(name="Self edit", phone=None))

    # 管理员同样可以改资料。
    edited = logic.update_member(ADMIN, 13, MemberInput(name="Admin edited", phone=None))
    assert (edited.id, edited.name) == (13, "Admin edited")


def test_create_member_writes_utc_timestamps(initialized_mysql_database):
    engine = initialized_mysql_database
    _seed(engine)
    logic = _logic(engine)
    before = datetime.now(timezone.utc).replace(tzinfo=None)

    view = logic.create_member(RECEPTIONIST, MemberInput(name="Fresh member", phone=None), REQUEST_ID)

    after = datetime.now(timezone.utc).replace(tzinfo=None)
    created_at = view.created_at.replace(tzinfo=None)
    assert view.created_at.tzinfo == timezone.utc and before <= created_at <= after
    assert view.status == "active" and view.archived_at is None
    with Session(engine) as session:
        row = session.execute(text(
            "SELECT name,created_at,updated_at FROM members WHERE id = :member_id"
        ), {"member_id": view.id}).mappings().one()
    # 视图里的时间戳就是库内 DATETIME(6) 列的值；按 UTC 写入由上面的区间断言证明。
    assert row["name"] == "Fresh member"
    assert row["created_at"] == created_at
    assert row["updated_at"] == created_at == view.updated_at.replace(tzinfo=None)
