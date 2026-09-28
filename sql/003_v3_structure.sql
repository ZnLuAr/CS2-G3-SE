-- 003_v3_structure.sql
-- v3 架构迁移：从 v2 升级到 v3
--
-- 本迁移脚本实现以下变更：
-- 1. 分离会员档案（members）与权益（gym_card_entitlement, coaching_entitlement）
-- 2. 统一销售流程：sales_orders → payments → entitlements
-- 3. 课程与会员卡的职责边界明确化
--
-- 迁移策略：停机维护切换，建立影子表 → 回填数据 → 校验 → 原子切换表名
-- 详细步骤见 docs/architecture.md 第 15 章

-- ==================== 健身房卡产品 ====================

-- 健身房卡产品根表
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
    KEY ix_gym_card_product_sale_kind_name_id (is_sale_enabled, kind, name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='健身房卡产品';

-- 期限卡产品
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
    KEY ix_duration_product_gift (is_gift_enabled, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='期限卡产品';

-- 次卡产品
CREATE TABLE visit_gym_card_products (
    product_id BIGINT PRIMARY KEY,
    kind VARCHAR(16) NOT NULL DEFAULT 'visit',
    total_entries INT NOT NULL COMMENT '总入场次数',
    CONSTRAINT uq_visit_product_identity UNIQUE (product_id, kind),
    CONSTRAINT fk_visit_product_root FOREIGN KEY (product_id, kind) REFERENCES gym_card_products(id, kind),
    CONSTRAINT ck_visit_product_kind CHECK (kind = 'visit'),
    CONSTRAINT ck_visit_product_total_entries CHECK (total_entries > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='次卡产品';

-- ==================== 私教课包产品 ====================

-- 私教课包产品
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
    KEY ix_lesson_product_sale_name_id (is_sale_enabled, name, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='私教课包产品';

-- 赠卡规则
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
    KEY ix_gift_rule_trigger_active_id (trigger_product_id, is_active, id),
    KEY ix_gift_rule_reward_product (reward_gym_card_product_id, is_active, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赠卡规则';

-- ==================== 销售订单 ====================

-- 销售订单
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

-- 健身房卡销售项目子表
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

-- 私教课包销售项目子表
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

-- 销售项目
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

-- 付款记录
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

-- 赠送记录
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

-- ==================== 健身房卡实例 ====================

-- 健身房卡根表
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
    CONSTRAINT fk_gym_cards_gift_origin FOREIGN KEY (gift_grant_id, member_id, reward_gym_card_product_id) REFERENCES gift_grants(id, member_id, reward_gym_card_product_id),
    CONSTRAINT ck_gym_cards_kind CHECK (kind IN ('duration', 'visit')),
    CONSTRAINT ck_gym_cards_name CHECK (CHAR_LENGTH(TRIM(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_gym_cards_status CHECK (status IN ('active', 'void')),
    CONSTRAINT ck_gym_cards_origin_xor CHECK ((purchase_sale_item_id IS NOT NULL) <> (gift_grant_id IS NOT NULL)),
    CONSTRAINT ck_gym_cards_visit_purchase_only CHECK (kind = 'duration' OR gift_grant_id IS NULL),
    KEY ix_gym_card_member_kind_status (member_id, kind, status, id),
    KEY ix_gym_card_product (product_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='健身房卡';

-- 期限卡实例
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

-- 次卡实例
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

-- ==================== 私教课包实例 ====================

-- 私教课包
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

-- ==================== 账号关联 ====================

-- 会员账号关联
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

-- 教练账号关联
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

-- ==================== 迁移辅助表 ====================

-- 迁移运行记录
CREATE TABLE schema_migration_runs (
    target_version INT PRIMARY KEY,
    phase VARCHAR(16) NOT NULL,
    structure_fingerprint CHAR(64)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    started_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    CONSTRAINT ck_schema_migration_runs_target
        CHECK (target_version > 0),
    CONSTRAINT ck_schema_migration_runs_phase
        CHECK (phase IN ('prepared', 'validated', 'renamed', 'versioned')),
    CONSTRAINT ck_schema_migration_runs_fingerprint
        CHECK (structure_fingerprint REGEXP '^[0-9a-f]{64}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='迁移运行记录';

-- v3 权益映射表
CREATE TABLE v3_entitlement_map (
    old_membership_id BIGINT PRIMARY KEY,
    lesson_package_id BIGINT NULL,
    gift_grant_id BIGINT NULL,
    gym_card_id BIGINT NOT NULL,
    CONSTRAINT uq_v3_entitlement_map_lesson_package
        UNIQUE (lesson_package_id),
    CONSTRAINT uq_v3_entitlement_map_gift_grant
        UNIQUE (gift_grant_id),
    CONSTRAINT uq_v3_entitlement_map_gym_card
        UNIQUE (gym_card_id),
    CONSTRAINT ck_v3_entitlement_map_old_id
        CHECK (old_membership_id > 0),
    CONSTRAINT ck_v3_entitlement_map_card_id
        CHECK (gym_card_id > 0),
    CONSTRAINT ck_v3_entitlement_map_optional_ids
        CHECK (
            (lesson_package_id IS NULL OR lesson_package_id > 0)
            AND (gift_grant_id IS NULL OR gift_grant_id > 0)
        ),
    CONSTRAINT ck_v3_entitlement_map_shape
        CHECK (
            (
                lesson_package_id IS NULL
                AND gift_grant_id IS NULL
            )
            OR
            (
                lesson_package_id IS NOT NULL
                AND gift_grant_id IS NOT NULL
            )
        )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='v3权益映射';

-- v3 入场映射表
CREATE TABLE v3_entry_map (
    old_gym_entry_id BIGINT PRIMARY KEY,
    gym_entry_id BIGINT NOT NULL,
    CONSTRAINT uq_v3_entry_map_target UNIQUE (gym_entry_id),
    CONSTRAINT ck_v3_entry_map_old_id CHECK (old_gym_entry_id > 0),
    CONSTRAINT ck_v3_entry_map_target_id CHECK (gym_entry_id > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='v3入场映射';

-- v3 会员映射表
CREATE TABLE v3_member_map (
    old_member_id BIGINT PRIMARY KEY,
    member_id BIGINT NOT NULL,
    CONSTRAINT uq_v3_member_map_target UNIQUE (member_id),
    CONSTRAINT ck_v3_member_map_old_id CHECK (old_member_id > 0),
    CONSTRAINT ck_v3_member_map_target_id CHECK (member_id > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='v3会员映射';

-- v3 操作记录映射表
CREATE TABLE v3_operation_map (
    old_operation_record_id BIGINT PRIMARY KEY,
    operation_record_id BIGINT NOT NULL,
    legacy_operation VARCHAR(50) NOT NULL,
    target_operation VARCHAR(50) NOT NULL,
    target_result_type VARCHAR(50) NOT NULL,
    target_result_id BIGINT NOT NULL,
    legacy_payload_hash CHAR(64)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    payload_version VARCHAR(16) NOT NULL,
    migrated_at DATETIME(6) NOT NULL,
    CONSTRAINT uq_v3_operation_map_target
        UNIQUE (operation_record_id),
    CONSTRAINT ck_v3_operation_map_old_id
        CHECK (old_operation_record_id > 0),
    CONSTRAINT ck_v3_operation_map_target_id
        CHECK (operation_record_id > 0),
    CONSTRAINT ck_v3_operation_map_result_id
        CHECK (target_result_id > 0),
    CONSTRAINT ck_v3_operation_map_legacy_hash
        CHECK (legacy_payload_hash REGEXP '^[0-9a-f]{64}$'),
    CONSTRAINT ck_v3_operation_map_payload_version
        CHECK (payload_version IN ('v3', 'legacy-v2'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='v3操作记录映射';

-- v3 产品映射表
CREATE TABLE v3_product_map (
    old_product_id BIGINT PRIMARY KEY,
    gym_card_product_id BIGINT NULL,
    lesson_package_product_id BIGINT NULL,
    historical_gift_rule_id BIGINT NULL,
    CONSTRAINT uq_v3_product_map_gym_product
        UNIQUE (gym_card_product_id),
    CONSTRAINT uq_v3_product_map_lesson_product
        UNIQUE (lesson_package_product_id),
    CONSTRAINT uq_v3_product_map_gift_rule
        UNIQUE (historical_gift_rule_id),
    CONSTRAINT ck_v3_product_map_old_id
        CHECK (old_product_id > 0),
    CONSTRAINT ck_v3_product_map_target_ids
        CHECK (
            (gym_card_product_id IS NULL OR gym_card_product_id > 0)
            AND (
                lesson_package_product_id IS NULL
                OR lesson_package_product_id > 0
            )
            AND (
                historical_gift_rule_id IS NULL
                OR historical_gift_rule_id > 0
            )
        ),
    CONSTRAINT ck_v3_product_map_shape
        CHECK (
            (
                gym_card_product_id IS NOT NULL
                AND lesson_package_product_id IS NULL
                AND historical_gift_rule_id IS NULL
            )
            OR
            (
                gym_card_product_id IS NOT NULL
                AND lesson_package_product_id IS NOT NULL
                AND historical_gift_rule_id IS NOT NULL
            )
        )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='v3产品映射';

-- v3 销售映射表
CREATE TABLE v3_sale_map (
    old_membership_id BIGINT PRIMARY KEY,
    sale_order_id BIGINT NOT NULL,
    sale_item_id BIGINT NOT NULL,
    payment_id BIGINT NOT NULL,
    CONSTRAINT uq_v3_sale_map_order UNIQUE (sale_order_id),
    CONSTRAINT uq_v3_sale_map_item UNIQUE (sale_item_id),
    CONSTRAINT uq_v3_sale_map_payment UNIQUE (payment_id),
    CONSTRAINT ck_v3_sale_map_old_id CHECK (old_membership_id > 0),
    CONSTRAINT ck_v3_sale_map_order_id CHECK (sale_order_id > 0),
    CONSTRAINT ck_v3_sale_map_item_id CHECK (sale_item_id > 0),
    CONSTRAINT ck_v3_sale_map_payment_id CHECK (payment_id > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='v3销售映射';

-- ==================== 门禁入场 ====================

-- 门禁入场记录
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

-- 标记版本 3 已应用
INSERT INTO schema_versions (version) VALUES (3)
ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP(6);
