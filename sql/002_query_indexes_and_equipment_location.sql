-- 版本 2：补充业务查询索引与器械位置非空白约束。
-- 每条 ALTER TABLE 都会在 MySQL 中隐式提交；迁移命令会在执行前检查同名结构，以支持失败后重试。

-- 不是另一份完整建表脚本，而是把原先混入 001_initial_schema.sql 的
-- 7 个索引和 1 个 equipment.location 约束拆成增量迁移

-- 这样做的理由是：001 已代表数据库版本 1。若继续直接修改它，已有版本 1 数据库不会获得这些结构变更，
-- 而 init 又只接受空库，造成文档所称的“当前结构”和已有数据库实际结构不一致。

ALTER TABLE accounts
    ADD KEY ix_account_role_active (role, is_active, id);

ALTER TABLE memberships
    ADD KEY ix_membership_member_term (member_id, status, valid_until, id);

ALTER TABLE memberships
    ADD KEY ix_membership_status_expiry (status, valid_until, id);

ALTER TABLE payments
    ADD KEY ix_payment_member_time (member_id, paid_at, id);

ALTER TABLE course_sessions
    ADD KEY ix_session_time (starts_at, id);

ALTER TABLE bookings
    ADD KEY ix_booking_member_status (member_id, status, session_id);

ALTER TABLE maintenance_records
    ADD KEY ix_maintenance_equipment_time (equipment_id, reported_at, id);

ALTER TABLE equipment
    ADD CONSTRAINT ck_equipment_location_nonblank
    CHECK (CHAR_LENGTH(TRIM(location)) > 0);
