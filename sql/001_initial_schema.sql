-- v3 初始结构脚本。数据库天生即 v3；按外键依赖顺序建表，版本记录由初始化命令写入。


-- ==================== 版本记录 ====================


CREATE TABLE schema_versions (
    version INT PRIMARY KEY,
    applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE schema_versions COMMENT='数据库结构版本记录：防止重复初始化';
ALTER TABLE schema_versions MODIFY COLUMN version INT COMMENT '结构版本号：由初始化命令写入，不要手动修改';
ALTER TABLE schema_versions MODIFY COLUMN applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '应用时刻';


-- ==================== 账号与档案 ====================


CREATE TABLE accounts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) COLLATE utf8mb4_bin NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CHECK (username REGEXP '^[a-z0-9_]{3,50}$'),
    CHECK (role IN ('member', 'coach', 'receptionist', 'admin')),
    CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE accounts COMMENT='账号表：登录凭据与角色，支持会员、教练、前台和管理员';
ALTER TABLE accounts MODIFY COLUMN username VARCHAR(50) COLLATE utf8mb4_bin NOT NULL UNIQUE COMMENT '用户名：规范化后的小写用户名，3~50位字母数字下划线，二进制排序保证大小写敏感';
ALTER TABLE accounts MODIFY COLUMN password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希：使用 Argon2 等成熟算法的哈希值，不存储明文密码';
ALTER TABLE accounts MODIFY COLUMN role VARCHAR(16) NOT NULL COMMENT '角色：member=会员, coach=教练, receptionist=前台, admin=管理员';
ALTER TABLE accounts MODIFY COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '启用状态：停用账号 (FALSE) 保留记录但无法登录';


CREATE TABLE members (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(32) NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    archived_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT ck_members_name
        CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_members_phone
        CHECK (phone IS NULL OR CHAR_LENGTH(TRIM(phone)) BETWEEN 1 AND 32),
    CONSTRAINT ck_members_status
        CHECK (status IN ('active', 'archived')),
    CONSTRAINT ck_members_archive_state
        CHECK (
            (status = 'active' AND archived_at IS NULL)
            OR
            (status = 'archived' AND archived_at IS NOT NULL)
        ),
    KEY ix_member_profile_status_id (status, id),
    KEY ix_member_profile_name_id (name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE members COMMENT='会员档案表：v3 账号关联移至 member_account_links';


CREATE TABLE coaches (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(32) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT ck_coaches_name
        CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_coaches_phone
        CHECK (phone IS NULL OR CHAR_LENGTH(TRIM(phone)) BETWEEN 1 AND 32),
    CONSTRAINT ck_coaches_active
        CHECK (is_active IN (0, 1)),
    KEY ix_coach_active_name_id (is_active, name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE coaches COMMENT='教练档案表：v3 账号关联移至 coach_account_links';


-- ==================== 账号-档案关联 ====================


CREATE TABLE member_account_links (
    account_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    linked_at DATETIME(6) NOT NULL COMMENT '关联时间',
    linked_by BIGINT NOT NULL COMMENT '操作人ID',
    CONSTRAINT uq_member_account_links_member UNIQUE (member_id),
    CONSTRAINT fk_member_account_links_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    CONSTRAINT fk_member_account_links_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT fk_member_account_links_linked_by FOREIGN KEY (linked_by) REFERENCES accounts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员账号关联';


CREATE TABLE coach_account_links (
    account_id BIGINT PRIMARY KEY,
    coach_id BIGINT NOT NULL COMMENT '教练ID',
    linked_at DATETIME(6) NOT NULL COMMENT '关联时间',
    linked_by BIGINT NOT NULL COMMENT '操作人ID',
    CONSTRAINT uq_coach_account_links_coach UNIQUE (coach_id),
    CONSTRAINT fk_coach_account_links_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    CONSTRAINT fk_coach_account_links_coach FOREIGN KEY (coach_id) REFERENCES coaches(id),
    CONSTRAINT fk_coach_account_links_linked_by FOREIGN KEY (linked_by) REFERENCES accounts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教练账号关联';


-- ==================== 课程、场地与课次 ====================


CREATE TABLE courses (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(1000) NULL,
    kind VARCHAR(16) NOT NULL DEFAULT 'private',
    duration_minutes INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT ck_courses_name
        CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_courses_description
        CHECK (
            description IS NULL
            OR CHAR_LENGTH(description) BETWEEN 1 AND 1000
        ),
    CONSTRAINT ck_courses_kind
        CHECK (kind = 'private'),
    CONSTRAINT ck_courses_duration
        CHECK (duration_minutes BETWEEN 1 AND 150),
    CONSTRAINT ck_courses_active
        CHECK (is_active IN (0, 1)),
    KEY ix_course_active_kind_name_id (is_active, kind, name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE courses COMMENT='课程模板表：定义课程类型和时长，当前只支持私教课';


CREATE TABLE rooms (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT ck_rooms_name
        CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_rooms_location
        CHECK (
            location IS NULL
            OR CHAR_LENGTH(location) BETWEEN 1 AND 200
        ),
    CONSTRAINT ck_rooms_active
        CHECK (is_active IN (0, 1)),
    KEY ix_room_active_name_id (is_active, name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE rooms COMMENT='场地表：v3 用 location 替代 capacity（私教容量固定为1）';


CREATE TABLE course_sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id BIGINT NOT NULL,
    coach_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    starts_at DATETIME(6) NOT NULL,
    ends_at DATETIME(6) NOT NULL,
    capacity INT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'scheduled',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (coach_id) REFERENCES coaches(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    KEY ix_session_coach (coach_id, starts_at, id),
    KEY ix_session_room (room_id, starts_at, id),
    CHECK (starts_at < ends_at AND ends_at <= DATE_ADD(starts_at, INTERVAL 150 MINUTE)),
    CHECK (CHAR_LENGTH(TRIM(course_name)) > 0),
    CHECK (kind = 'private'),
    CHECK (capacity = 1),
    CHECK (status IN ('scheduled', 'completed', 'cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE course_sessions COMMENT='课节表：教练排课，快照课程名称和类型，当前私教课容量固定为1';
ALTER TABLE course_sessions MODIFY COLUMN course_name VARCHAR(100) NOT NULL COMMENT '课程名称快照：记录排课时的课程名称，避免课程模板修改影响历史记录';
ALTER TABLE course_sessions MODIFY COLUMN kind VARCHAR(16) NOT NULL COMMENT '课程类型快照：记录排课时的类型，当前固定为 private';
ALTER TABLE course_sessions MODIFY COLUMN capacity INT NOT NULL COMMENT '容量：当前私教课固定为1';
ALTER TABLE course_sessions MODIFY COLUMN status VARCHAR(16) NOT NULL DEFAULT 'scheduled' COMMENT '状态：scheduled=已排课, completed=已完成, cancelled=已取消';


-- ==================== 器械、维修、体测（本次重构范围外）====================
-- 归属：equipment / maintenance_records 由 Tuao SONG 负责（EQ-01~EQ-07）；
--       body_measurements 由 Tuao SONG、Mingjin LI 负责（MEASURE-01~03）。
-- 本次「课程与会员卡」契约重构未改动这三张表，保留完整结构供各负责人填充实现。


CREATE TABLE equipment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    asset_code VARCHAR(50) COLLATE utf8mb4_bin NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'available',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CHECK (CHAR_LENGTH(TRIM(asset_code)) > 0 AND CHAR_LENGTH(TRIM(name)) > 0),
    CHECK (status IN ('available', 'maintenance', 'retired'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE equipment COMMENT='器械表：健身房器械资产，记录位置和状态';
ALTER TABLE equipment MODIFY COLUMN asset_code VARCHAR(50) COLLATE utf8mb4_bin NOT NULL UNIQUE COMMENT '资产编码：器械唯一标识，二进制排序保证大小写敏感';
ALTER TABLE equipment MODIFY COLUMN location VARCHAR(100) NOT NULL COMMENT '位置：器械摆放位置';
ALTER TABLE equipment MODIFY COLUMN status VARCHAR(16) NOT NULL DEFAULT 'available' COMMENT '状态：available=可用, maintenance=维修中, retired=已报废';


CREATE TABLE maintenance_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    equipment_id BIGINT NOT NULL,
    description VARCHAR(1000) NOT NULL,
    reported_at DATETIME(6) NOT NULL,
    resolved_at DATETIME(6) NULL,
    operator_id BIGINT NOT NULL,
    resolved_by BIGINT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id),
    FOREIGN KEY (operator_id) REFERENCES accounts(id),
    FOREIGN KEY (resolved_by) REFERENCES accounts(id),
    CHECK (CHAR_LENGTH(TRIM(description)) > 0),
    CHECK ((resolved_at IS NULL AND resolved_by IS NULL)
        OR (resolved_at IS NOT NULL AND resolved_by IS NOT NULL AND resolved_at >= reported_at))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE maintenance_records COMMENT='维护记录表：器械维修保养记录，记录报告和解决时间';
ALTER TABLE maintenance_records MODIFY COLUMN reported_at DATETIME(6) NOT NULL COMMENT '报告时刻：发现问题的时间';
ALTER TABLE maintenance_records MODIFY COLUMN resolved_at DATETIME(6) NULL COMMENT '解决时刻：问题解决的时间，未解决为NULL';
ALTER TABLE maintenance_records MODIFY COLUMN operator_id BIGINT NOT NULL COMMENT '报告人ID：提交报修的账号';
ALTER TABLE maintenance_records MODIFY COLUMN resolved_by BIGINT NULL COMMENT '解决人ID：解决问题的员工，未解决为NULL';


CREATE TABLE body_measurements (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    coach_id BIGINT NOT NULL,
    measured_at DATETIME(6) NOT NULL,
    height_cm DECIMAL(6,2) NOT NULL,
    weight_kg DECIMAL(6,2) NOT NULL,
    body_fat_pct DECIMAL(5,2) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (coach_id) REFERENCES coaches(id),
    KEY ix_measurement_member_time (member_id, measured_at, id),
    KEY ix_measurement_member_created (member_id, created_at, id),
    CHECK (height_cm BETWEEN 100.00 AND 250.00 AND weight_kg BETWEEN 30.00 AND 150.00),
    CHECK (body_fat_pct IS NULL OR body_fat_pct BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE body_measurements COMMENT='体测记录表：教练为会员测量身体数据，支持趋势对比';
ALTER TABLE body_measurements MODIFY COLUMN measured_at DATETIME(6) NOT NULL COMMENT '测量时刻：实际测量时间';
ALTER TABLE body_measurements MODIFY COLUMN height_cm DECIMAL(6,2) NOT NULL COMMENT '身高（厘米）：100.00~250.00';
ALTER TABLE body_measurements MODIFY COLUMN weight_kg DECIMAL(6,2) NOT NULL COMMENT '体重（千克）：30.00~150.00';
ALTER TABLE body_measurements MODIFY COLUMN body_fat_pct DECIMAL(5,2) NULL COMMENT '体脂率（%）：0~100，可选';


-- ==================== 幂等操作记录（核心基础设施）====================


CREATE TABLE operation_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    request_id CHAR(36)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    actor_id BIGINT NOT NULL,
    operation VARCHAR(50)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    payload_hash CHAR(64)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    result_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_operation_request UNIQUE (request_id),
    CONSTRAINT fk_operation_records_actor
        FOREIGN KEY (actor_id) REFERENCES accounts(id),
    CONSTRAINT ck_operation_records_operation
        CHECK (
            operation IN (
                'create_member',
                'sell_gym_card',
                'sell_lesson_package',
                'create_session',
                'cancel_session',
                'book',
                'cancel_booking',
                'register_entry'
            )
        ),
    CONSTRAINT ck_operation_records_payload_hash
        CHECK (payload_hash REGEXP '^[0-9a-f]{64}$'),
    KEY ix_operation_actor_time (actor_id, created_at, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE operation_records COMMENT='操作记录表：幂等与审计，按 request_id 去重';


-- ==================== 健身房卡产品 ====================


CREATE TABLE gym_card_products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    kind VARCHAR(16) NOT NULL COMMENT '卡类型：duration（期限卡）、visit（次卡）',
    name VARCHAR(100) NOT NULL COMMENT '产品名称',
    price DECIMAL(10,2) NOT NULL COMMENT '价格',
    is_sale_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否可销售',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_gym_card_product_kind UNIQUE (id, kind),
    CONSTRAINT ck_gym_card_products_kind CHECK (kind IN ('duration', 'visit')),
    CONSTRAINT ck_gym_card_products_name CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_gym_card_products_price CHECK (price BETWEEN 0.01 AND 99999999.99),
    CONSTRAINT ck_gym_card_products_sale_enabled CHECK (is_sale_enabled IN (0, 1)),
    KEY ix_gym_card_product_sale_kind_name_id (is_sale_enabled, kind, name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='健身房卡产品';


CREATE TABLE duration_gym_card_products (
    product_id BIGINT PRIMARY KEY,
    kind VARCHAR(16) NOT NULL DEFAULT 'duration',
    valid_days INT NOT NULL COMMENT '有效天数',
    start_policy VARCHAR(16) NOT NULL COMMENT '生效策略：immediate（立即生效）、append（接续）',
    is_gift_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否可赠送',
    CONSTRAINT uq_duration_product_identity UNIQUE (product_id, kind),
    CONSTRAINT fk_duration_product_root FOREIGN KEY (product_id, kind) REFERENCES gym_card_products(id, kind),
    CONSTRAINT ck_duration_product_kind CHECK (kind = 'duration'),
    CONSTRAINT ck_duration_product_valid_days CHECK (valid_days > 0),
    CONSTRAINT ck_duration_product_start_policy CHECK (start_policy IN ('immediate', 'append')),
    CONSTRAINT ck_duration_product_gift_enabled CHECK (is_gift_enabled IN (0, 1)),
    KEY ix_duration_product_gift (is_gift_enabled, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='期限卡产品';


CREATE TABLE visit_gym_card_products (
    product_id BIGINT PRIMARY KEY,
    kind VARCHAR(16) NOT NULL DEFAULT 'visit',
    total_entries INT NOT NULL COMMENT '总入场次数',
    CONSTRAINT uq_visit_product_identity UNIQUE (product_id, kind),
    CONSTRAINT fk_visit_product_root FOREIGN KEY (product_id, kind) REFERENCES gym_card_products(id, kind),
    CONSTRAINT ck_visit_product_kind CHECK (kind = 'visit'),
    CONSTRAINT ck_visit_product_total_entries CHECK (total_entries > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='次卡产品';


-- ==================== 私教课包产品与赠卡规则 ====================


CREATE TABLE lesson_package_products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '产品名称',
    price DECIMAL(10,2) NOT NULL COMMENT '价格',
    lesson_credits INT NOT NULL COMMENT '课节数',
    valid_days INT NULL COMMENT '有效天数（NULL表示无期限）',
    is_sale_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否可销售',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT ck_lesson_package_products_name CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_lesson_package_products_price CHECK (price BETWEEN 0.01 AND 99999999.99),
    CONSTRAINT ck_lesson_package_products_credits CHECK (lesson_credits > 0),
    CONSTRAINT ck_lesson_package_products_valid_days CHECK (valid_days IS NULL OR valid_days > 0),
    CONSTRAINT ck_lesson_package_products_sale_enabled CHECK (is_sale_enabled IN (0, 1)),
    KEY ix_lesson_product_sale_name_id (is_sale_enabled, name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='私教课包产品';


CREATE TABLE lesson_package_gift_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    trigger_product_id BIGINT NOT NULL COMMENT '触发产品ID（课包产品）',
    reward_gym_card_product_id BIGINT NOT NULL COMMENT '奖励产品ID（期限卡产品）',
    reward_quantity INT NOT NULL DEFAULT 1 COMMENT '奖励数量',
    activation_policy VARCHAR(16) NOT NULL COMMENT '激活策略：immediate、append',
    version INT NOT NULL COMMENT '规则版本',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    active_trigger_product_id BIGINT GENERATED ALWAYS AS (CASE WHEN is_active = TRUE THEN trigger_product_id ELSE NULL END) STORED,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_gift_rule_trigger_version UNIQUE (trigger_product_id, version),
    CONSTRAINT uq_gift_rule_active_trigger UNIQUE (active_trigger_product_id),
    CONSTRAINT uq_gift_rule_identity UNIQUE (id, trigger_product_id, reward_gym_card_product_id, version),
    CONSTRAINT fk_gift_rule_trigger_product FOREIGN KEY (trigger_product_id) REFERENCES lesson_package_products(id),
    CONSTRAINT fk_gift_rule_reward_duration_product FOREIGN KEY (reward_gym_card_product_id) REFERENCES duration_gym_card_products(product_id),
    CONSTRAINT ck_gift_rule_quantity CHECK (reward_quantity > 0),
    CONSTRAINT ck_gift_rule_activation_policy CHECK (activation_policy IN ('immediate', 'append')),
    CONSTRAINT ck_gift_rule_immediate_quantity CHECK (activation_policy <> 'immediate' OR reward_quantity = 1),
    CONSTRAINT ck_gift_rule_version CHECK (version > 0),
    CONSTRAINT ck_gift_rule_active CHECK (is_active IN (0, 1)),
    KEY ix_gift_rule_trigger_active_id (trigger_product_id, is_active, id),
    KEY ix_gift_rule_reward_product (reward_gym_card_product_id, is_active, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赠卡规则';


-- ==================== 销售订单、项目与付款 ====================


CREATE TABLE sale_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    kind VARCHAR(24) NOT NULL COMMENT '订单类型：gym_card、lesson_package',
    total_amount DECIMAL(10,2) NOT NULL COMMENT '总金额',
    sold_at DATETIME(6) NOT NULL COMMENT '销售时间',
    operator_id BIGINT NOT NULL COMMENT '操作员ID',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_sale_order_owner UNIQUE (id, member_id),
    CONSTRAINT uq_sale_order_owner_kind UNIQUE (id, member_id, kind),
    CONSTRAINT fk_sale_orders_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT fk_sale_orders_operator FOREIGN KEY (operator_id) REFERENCES accounts(id),
    CONSTRAINT ck_sale_orders_kind CHECK (kind IN ('gym_card', 'lesson_package')),
    CONSTRAINT ck_sale_orders_total_amount CHECK (total_amount BETWEEN 0.01 AND 99999999.99),
    KEY ix_sale_order_member_time_id (member_id, sold_at, id),
    KEY ix_sale_order_time_id (sold_at, id),
    KEY ix_sale_order_operator_time (operator_id, sold_at, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售订单';


CREATE TABLE sale_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sale_order_id BIGINT NOT NULL COMMENT '销售订单ID',
    member_id BIGINT NOT NULL COMMENT '会员ID',
    kind VARCHAR(24) NOT NULL COMMENT '项目类型：gym_card、lesson_package',
    product_name VARCHAR(100) NOT NULL COMMENT '产品名称快照',
    quantity INT NOT NULL COMMENT '数量',
    unit_price DECIMAL(10,2) NOT NULL COMMENT '单价',
    line_amount DECIMAL(10,2) NOT NULL COMMENT '行金额',
    CONSTRAINT uq_sale_item_order_kind UNIQUE (sale_order_id, kind),
    CONSTRAINT uq_sale_item_order_owner UNIQUE (id, sale_order_id, member_id),
    CONSTRAINT uq_sale_item_owner_kind UNIQUE (id, member_id, kind),
    CONSTRAINT fk_sale_items_order_owner_kind FOREIGN KEY (sale_order_id, member_id, kind) REFERENCES sale_orders(id, member_id, kind),
    CONSTRAINT ck_sale_items_kind CHECK (kind IN ('gym_card', 'lesson_package')),
    CONSTRAINT ck_sale_items_product_name CHECK (CHAR_LENGTH(TRIM(product_name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_sale_items_quantity CHECK (quantity = 1),
    CONSTRAINT ck_sale_items_unit_price CHECK (unit_price BETWEEN 0.01 AND 99999999.99),
    CONSTRAINT ck_sale_items_line_amount CHECK (line_amount = unit_price),
    KEY ix_sale_item_order_id (sale_order_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售项目';


CREATE TABLE gym_card_sale_items (
    sale_item_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    kind VARCHAR(24) NOT NULL DEFAULT 'gym_card',
    gym_card_product_id BIGINT NOT NULL COMMENT '健身房卡产品ID',
    CONSTRAINT uq_gym_card_sale_origin UNIQUE (sale_item_id, member_id, gym_card_product_id),
    CONSTRAINT fk_gym_card_sale_item FOREIGN KEY (sale_item_id, member_id, kind) REFERENCES sale_items(id, member_id, kind),
    CONSTRAINT fk_gym_card_sale_product FOREIGN KEY (gym_card_product_id) REFERENCES gym_card_products(id),
    CONSTRAINT ck_gym_card_sale_item_kind CHECK (kind = 'gym_card'),
    KEY ix_gym_card_sale_product (gym_card_product_id, sale_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='健身房卡销售项目';


CREATE TABLE lesson_package_sale_items (
    sale_item_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    kind VARCHAR(24) NOT NULL DEFAULT 'lesson_package',
    lesson_package_product_id BIGINT NOT NULL COMMENT '私教课包产品ID',
    CONSTRAINT uq_lesson_sale_origin UNIQUE (sale_item_id, member_id, lesson_package_product_id),
    CONSTRAINT fk_lesson_package_sale_item FOREIGN KEY (sale_item_id, member_id, kind) REFERENCES sale_items(id, member_id, kind),
    CONSTRAINT fk_lesson_package_sale_product FOREIGN KEY (lesson_package_product_id) REFERENCES lesson_package_products(id),
    CONSTRAINT ck_lesson_package_sale_item_kind CHECK (kind = 'lesson_package'),
    KEY ix_lesson_sale_product (lesson_package_product_id, sale_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='私教课包销售项目';


CREATE TABLE payments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sale_order_id BIGINT NOT NULL COMMENT '销售订单ID',
    member_id BIGINT NOT NULL COMMENT '会员ID',
    amount DECIMAL(10,2) NOT NULL COMMENT '金额',
    method VARCHAR(16) NOT NULL COMMENT '付款方式：cash、card、transfer',
    paid_at DATETIME(6) NOT NULL COMMENT '付款时间',
    operator_id BIGINT NOT NULL COMMENT '操作员ID',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_payments_sale_order UNIQUE (sale_order_id),
    CONSTRAINT fk_payments_order_owner FOREIGN KEY (sale_order_id, member_id) REFERENCES sale_orders(id, member_id),
    CONSTRAINT fk_payments_operator FOREIGN KEY (operator_id) REFERENCES accounts(id),
    CONSTRAINT ck_payments_amount CHECK (amount BETWEEN 0.01 AND 99999999.99),
    CONSTRAINT ck_payments_method CHECK (method IN ('cash', 'card', 'transfer')),
    KEY ix_payment_time_id (paid_at, id),
    KEY ix_payment_method_time_id (method, paid_at, id),
    KEY ix_payment_operator_time (operator_id, paid_at, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='付款记录';


CREATE TABLE gift_grants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    trigger_sale_item_id BIGINT NOT NULL COMMENT '触发销售项目ID',
    trigger_product_id BIGINT NOT NULL COMMENT '触发产品ID',
    gift_rule_id BIGINT NOT NULL COMMENT '赠卡规则ID',
    member_id BIGINT NOT NULL COMMENT '会员ID',
    reward_gym_card_product_id BIGINT NOT NULL COMMENT '奖励产品ID',
    gift_rule_version INT NOT NULL COMMENT '规则版本',
    activation_policy VARCHAR(16) NOT NULL COMMENT '激活策略',
    reward_product_name VARCHAR(100) NOT NULL COMMENT '奖励产品名称',
    reward_valid_days INT NOT NULL COMMENT '奖励有效天数',
    sequence INT NOT NULL COMMENT '序号',
    granted_at DATETIME(6) NOT NULL COMMENT '赠送时间',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_gift_grant_sequence UNIQUE (trigger_sale_item_id, gift_rule_id, sequence),
    CONSTRAINT uq_gift_grant_card_origin UNIQUE (id, member_id, reward_gym_card_product_id),
    CONSTRAINT fk_gift_grant_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT ck_gift_grant_version CHECK (gift_rule_version > 0),
    CONSTRAINT ck_gift_grant_activation_policy CHECK (activation_policy IN ('immediate', 'append')),
    CONSTRAINT ck_gift_grant_product_name CHECK (CHAR_LENGTH(TRIM(reward_product_name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_gift_grant_valid_days CHECK (reward_valid_days > 0),
    CONSTRAINT ck_gift_grant_sequence CHECK (sequence > 0),
    KEY ix_gift_grant_member_time (member_id, granted_at, id),
    KEY ix_gift_grant_rule (gift_rule_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赠送记录';


-- ==================== 健身房卡与课包实例 ====================


CREATE TABLE gym_cards (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    product_id BIGINT NOT NULL COMMENT '产品ID',
    kind VARCHAR(16) NOT NULL COMMENT '卡类型：duration、visit',
    purchase_sale_item_id BIGINT NULL COMMENT '购买销售项目ID',
    gift_grant_id BIGINT NULL COMMENT '赠送记录ID',
    name VARCHAR(100) NOT NULL COMMENT '卡名称快照',
    status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态：active、void',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_gym_cards_purchase_sale_item UNIQUE (purchase_sale_item_id),
    CONSTRAINT uq_gym_cards_gift_grant UNIQUE (gift_grant_id),
    CONSTRAINT uq_gym_card_owner UNIQUE (id, member_id),
    CONSTRAINT uq_gym_card_owner_kind UNIQUE (id, member_id, kind),
    CONSTRAINT fk_gym_cards_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT fk_gym_cards_product_kind FOREIGN KEY (product_id, kind) REFERENCES gym_card_products(id, kind),
    CONSTRAINT fk_gym_cards_gift_origin FOREIGN KEY (gift_grant_id, member_id, product_id) REFERENCES gift_grants(id, member_id, reward_gym_card_product_id),
    CONSTRAINT ck_gym_cards_kind CHECK (kind IN ('duration', 'visit')),
    CONSTRAINT ck_gym_cards_name CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_gym_cards_status CHECK (status IN ('active', 'void')),
    CONSTRAINT ck_gym_cards_origin_xor CHECK ((purchase_sale_item_id IS NOT NULL) <> (gift_grant_id IS NOT NULL)),
    CONSTRAINT ck_gym_cards_visit_purchase_only CHECK (kind = 'duration' OR gift_grant_id IS NULL),
    KEY ix_gym_card_member_kind_status (member_id, kind, status, id),
    KEY ix_gym_card_product (product_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='健身房卡';


CREATE TABLE duration_gym_cards (
    gym_card_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    kind VARCHAR(16) NOT NULL DEFAULT 'duration',
    valid_days INT NOT NULL COMMENT '有效天数',
    start_policy VARCHAR(16) NOT NULL COMMENT '生效策略',
    valid_from DATE NOT NULL COMMENT '生效日期',
    valid_until DATE NOT NULL COMMENT '失效日期（不含）',
    CONSTRAINT uq_duration_card_owner UNIQUE (gym_card_id, member_id),
    CONSTRAINT fk_duration_card_root FOREIGN KEY (gym_card_id, member_id, kind) REFERENCES gym_cards(id, member_id, kind),
    CONSTRAINT ck_duration_card_kind CHECK (kind = 'duration'),
    CONSTRAINT ck_duration_card_valid_days CHECK (valid_days > 0),
    CONSTRAINT ck_duration_card_start_policy CHECK (start_policy IN ('immediate', 'append')),
    CONSTRAINT ck_duration_card_dates CHECK (valid_from < valid_until AND DATEDIFF(valid_until, valid_from) = valid_days),
    KEY ix_duration_card_member_end (member_id, valid_until, gym_card_id),
    KEY ix_duration_card_member_range (member_id, valid_from, valid_until, gym_card_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='期限卡';


CREATE TABLE visit_gym_cards (
    gym_card_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    kind VARCHAR(16) NOT NULL DEFAULT 'visit',
    total_entries INT NOT NULL COMMENT '总次数',
    remaining_entries INT NOT NULL COMMENT '剩余次数',
    CONSTRAINT uq_visit_card_owner UNIQUE (gym_card_id, member_id),
    CONSTRAINT fk_visit_card_root FOREIGN KEY (gym_card_id, member_id, kind) REFERENCES gym_cards(id, member_id, kind),
    CONSTRAINT ck_visit_card_kind CHECK (kind = 'visit'),
    CONSTRAINT ck_visit_card_total_entries CHECK (total_entries > 0),
    CONSTRAINT ck_visit_card_remaining_entries CHECK (remaining_entries BETWEEN 0 AND total_entries),
    KEY ix_visit_card_member_remaining (member_id, remaining_entries, gym_card_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='次卡';


CREATE TABLE lesson_packages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    product_id BIGINT NOT NULL COMMENT '产品ID',
    purchase_sale_item_id BIGINT NOT NULL COMMENT '购买销售项目ID',
    name VARCHAR(100) NOT NULL COMMENT '课包名称快照',
    total_lessons INT NOT NULL COMMENT '总课节数',
    remaining_lessons INT NOT NULL COMMENT '剩余课节',
    reserved_lessons INT NOT NULL COMMENT '已预约课节',
    available_lessons INT GENERATED ALWAYS AS (remaining_lessons - reserved_lessons) STORED COMMENT '可用课节',
    valid_from DATE NOT NULL COMMENT '生效日期',
    valid_until DATE NULL COMMENT '失效日期（不含，NULL表示无期限）',
    status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态：active、void',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT uq_lesson_packages_purchase_sale_item UNIQUE (purchase_sale_item_id),
    CONSTRAINT uq_lesson_package_owner UNIQUE (id, member_id),
    CONSTRAINT fk_lesson_packages_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT fk_lesson_packages_product FOREIGN KEY (product_id) REFERENCES lesson_package_products(id),
    CONSTRAINT ck_lesson_packages_name CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_lesson_packages_total CHECK (total_lessons > 0),
    CONSTRAINT ck_lesson_packages_balances CHECK (reserved_lessons >= 0 AND reserved_lessons <= remaining_lessons AND remaining_lessons <= total_lessons),
    CONSTRAINT ck_lesson_packages_dates CHECK (valid_until IS NULL OR valid_from < valid_until),
    CONSTRAINT ck_lesson_packages_status CHECK (status IN ('active', 'void')),
    KEY ix_lesson_package_member_status_end_id (member_id, status, valid_until, id),
    KEY ix_lesson_package_member_available (member_id, status, available_lessons, id),
    KEY ix_lesson_package_product (product_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='私教课包';


-- ==================== 预约与入场（核心）====================


CREATE TABLE bookings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    lesson_package_id BIGINT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'reserved',
    booked_at DATETIME(6) NOT NULL,
    checked_in_at DATETIME(6) NULL,
    closed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (session_id) REFERENCES course_sessions(id),
    FOREIGN KEY (lesson_package_id, member_id) REFERENCES lesson_packages(id, member_id),
    UNIQUE KEY uq_booking_owner (id, member_id),
    UNIQUE KEY uq_booking_member_session (member_id, session_id),
    UNIQUE KEY uq_booking_package (id, lesson_package_id),
    KEY ix_booking_session_status (session_id, status, id),
    CHECK (status IN ('reserved', 'cancelled', 'checked_in', 'completed', 'no_show')),
    CHECK ((status = 'reserved' AND checked_in_at IS NULL AND closed_at IS NULL)
        OR (status = 'checked_in' AND checked_in_at IS NOT NULL AND closed_at IS NULL)
        OR (status = 'completed' AND checked_in_at IS NOT NULL AND closed_at IS NOT NULL)
        OR (status IN ('cancelled', 'no_show') AND checked_in_at IS NULL AND closed_at IS NOT NULL)),
    CHECK (checked_in_at IS NULL OR checked_in_at >= booked_at),
    CHECK (closed_at IS NULL OR closed_at >= booked_at),
    CHECK (checked_in_at IS NULL OR closed_at IS NULL OR closed_at >= checked_in_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE bookings COMMENT='预约表：会员预约课节，记录状态流转时间';
ALTER TABLE bookings MODIFY COLUMN status VARCHAR(16) NOT NULL DEFAULT 'reserved' COMMENT '状态：reserved=已预约, checked_in=已签到, completed=已完成, cancelled=已取消, no_show=缺席';
ALTER TABLE bookings MODIFY COLUMN booked_at DATETIME(6) NOT NULL COMMENT '预约时刻';
ALTER TABLE bookings MODIFY COLUMN checked_in_at DATETIME(6) NULL COMMENT '签到时刻：只有 checked_in 和 completed 状态才有值';
ALTER TABLE bookings MODIFY COLUMN closed_at DATETIME(6) NULL COMMENT '结束时刻：cancelled/no_show/completed 状态的结束时间';


CREATE TABLE gym_entries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL COMMENT '会员ID',
    source_kind VARCHAR(24) NOT NULL COMMENT '来源类型：duration_gym_card、visit_gym_card、booking',
    duration_gym_card_id BIGINT NULL COMMENT '期限卡ID',
    visit_gym_card_id BIGINT NULL COMMENT '次卡ID',
    booking_id BIGINT NULL COMMENT '预约ID',
    business_date DATE NOT NULL COMMENT '业务日期',
    entered_at DATETIME(6) NOT NULL COMMENT '入场时间',
    operator_id BIGINT NOT NULL COMMENT '操作员ID',
    CONSTRAINT uq_entry_owner UNIQUE (id, member_id),
    CONSTRAINT uq_entry_member_day UNIQUE (member_id, business_date),
    CONSTRAINT uq_entry_booking UNIQUE (booking_id),
    CONSTRAINT fk_gym_entries_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT fk_gym_entries_operator FOREIGN KEY (operator_id) REFERENCES accounts(id),
    CONSTRAINT fk_gym_entries_duration_card_owner FOREIGN KEY (duration_gym_card_id, member_id) REFERENCES duration_gym_cards(gym_card_id, member_id),
    CONSTRAINT fk_gym_entries_visit_card_owner FOREIGN KEY (visit_gym_card_id, member_id) REFERENCES visit_gym_cards(gym_card_id, member_id),
    CONSTRAINT fk_gym_entries_booking_owner FOREIGN KEY (booking_id, member_id) REFERENCES bookings(id, member_id),
    CONSTRAINT ck_gym_entries_source_kind CHECK (source_kind IN ('duration_gym_card', 'visit_gym_card', 'booking')),
    CONSTRAINT ck_gym_entries_source_xor CHECK (
        (source_kind = 'duration_gym_card' AND duration_gym_card_id IS NOT NULL AND visit_gym_card_id IS NULL AND booking_id IS NULL)
        OR (source_kind = 'visit_gym_card' AND visit_gym_card_id IS NOT NULL AND duration_gym_card_id IS NULL AND booking_id IS NULL)
        OR (source_kind = 'booking' AND booking_id IS NOT NULL AND duration_gym_card_id IS NULL AND visit_gym_card_id IS NULL)
    ),
    KEY ix_entry_business_date_id (business_date, id),
    KEY ix_entry_operator_time (operator_id, entered_at, id),
    KEY ix_entry_duration_card (duration_gym_card_id, id),
    KEY ix_entry_visit_card (visit_gym_card_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='门禁入场记录';


-- ==================== 评价（本次重构范围外）====================
-- 归属：reviews 由 Yihao QIAN 负责（REVIEW-01、REVIEW-02）。
-- 本次「课程与会员卡」契约重构未改动此表，保留完整结构供负责人填充实现。


CREATE TABLE reviews (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    booking_id BIGINT NOT NULL UNIQUE,
    rating INT NOT NULL,
    comment VARCHAR(1000) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (booking_id) REFERENCES bookings(id),
    CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE reviews COMMENT='评价表：会员评价课节，一对一关联预约';
ALTER TABLE reviews MODIFY COLUMN booking_id BIGINT NOT NULL UNIQUE COMMENT '预约ID：与预约一对一，保证每个预约只评价一次';
ALTER TABLE reviews MODIFY COLUMN rating INT NOT NULL COMMENT '评分：1~5星';
