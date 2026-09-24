-- 初始结构脚本。执行顺序按外键依赖排列；版本记录由初始化命令写入。

CREATE TABLE schema_versions (
    version INT PRIMARY KEY,
    applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE schema_versions COMMENT='数据库结构版本记录：防止重复初始化或跳过必需的迁移脚本';
ALTER TABLE schema_versions MODIFY COLUMN version INT COMMENT '结构版本号：由初始化命令写入，不要手动修改';
ALTER TABLE schema_versions MODIFY COLUMN applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '应用时刻';


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
    account_id BIGINT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(32) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE members COMMENT='会员档案表：存储会员基本信息，可选关联账号';
ALTER TABLE members MODIFY COLUMN account_id BIGINT NULL UNIQUE COMMENT '账号ID：可为NULL，前台代办卡时会员可能尚未创建账号';
ALTER TABLE members MODIFY COLUMN phone VARCHAR(32) NULL COMMENT '手机号：联系方式，CLI显示时脱敏';


CREATE TABLE coaches (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    account_id BIGINT NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    specialty VARCHAR(200) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE coaches COMMENT='教练档案表：存储教练基本信息，必须关联账号';
ALTER TABLE coaches MODIFY COLUMN account_id BIGINT NOT NULL UNIQUE COMMENT '账号ID：必须关联账号，一对一关系';
ALTER TABLE coaches MODIFY COLUMN specialty VARCHAR(200) NOT NULL COMMENT '专长：教练的特长领域描述';


CREATE TABLE card_products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    private_lesson_credits INT NOT NULL,
    access_uses INT NULL,
    valid_days INT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CHECK (price > 0 AND CHAR_LENGTH(TRIM(name)) > 0),
    CHECK (is_active IN (0, 1)),
    CHECK (private_lesson_credits >= 0),
    CHECK (access_uses IS NULL OR access_uses > 0),
    CHECK (
        (kind = 'monthly' AND valid_days IS NOT NULL AND valid_days = 30 AND private_lesson_credits = 20 AND access_uses IS NULL)
        OR (kind = 'quarterly' AND valid_days IS NOT NULL AND valid_days = 90 AND private_lesson_credits = 64 AND access_uses IS NULL)
        OR (kind = 'yearly' AND valid_days IS NOT NULL AND valid_days = 365 AND private_lesson_credits = 256 AND access_uses IS NULL)
        OR (kind = 'count' AND valid_days IS NULL AND access_uses IS NOT NULL AND access_uses = 10 AND private_lesson_credits = 0)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE card_products COMMENT='产品表：私教课产品（月/季/年）和入场次卡，固定配置';
ALTER TABLE card_products MODIFY COLUMN kind VARCHAR(16) NOT NULL COMMENT '产品类型：monthly=月卡(30天20节课), quarterly=季卡(90天64节课), yearly=年卡(365天256节课), count=次卡(10次入场0节课)';
ALTER TABLE card_products MODIFY COLUMN private_lesson_credits INT NOT NULL COMMENT '私教课节数：购买私教课产品的课节数，单独购买的次卡为0';
ALTER TABLE card_products MODIFY COLUMN access_uses INT NULL COMMENT '入场次数：次卡专用，私教课产品为NULL（附赠无限次门禁）';
ALTER TABLE card_products MODIFY COLUMN valid_days INT NULL COMMENT '有效天数：私教课产品的门禁天数，次卡为NULL';


CREATE TABLE memberships (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    private_lesson_credits INT NOT NULL,
    access_uses INT NULL,
    valid_days INT NULL,
    valid_from DATE NOT NULL,
    valid_until DATE NULL,
    remaining_accesses INT NULL,
    remaining_private_lessons INT NOT NULL,
    reserved_private_lessons INT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (product_id) REFERENCES card_products(id),
    UNIQUE KEY uq_membership_owner (id, member_id),
    KEY ix_membership_member (member_id, id),
    CHECK (valid_until IS NULL OR valid_from < valid_until),
    CHECK (status IN ('active', 'void')),
    CHECK (price > 0 AND CHAR_LENGTH(TRIM(name)) > 0),
    CHECK (private_lesson_credits >= 0),
    CHECK ((access_uses IS NULL AND remaining_accesses IS NULL)
        OR (access_uses IS NOT NULL AND remaining_accesses IS NOT NULL
            AND 0 <= remaining_accesses AND remaining_accesses <= access_uses)),
    CHECK (0 <= reserved_private_lessons AND reserved_private_lessons <= remaining_private_lessons
        AND remaining_private_lessons <= private_lesson_credits),
    CHECK (
        (kind = 'monthly' AND valid_days IS NOT NULL AND valid_days = 30 AND private_lesson_credits = 20 AND access_uses IS NULL)
        OR (kind = 'quarterly' AND valid_days IS NOT NULL AND valid_days = 90 AND private_lesson_credits = 64 AND access_uses IS NULL)
        OR (kind = 'yearly' AND valid_days IS NOT NULL AND valid_days = 365 AND private_lesson_credits = 256 AND access_uses IS NULL)
        OR (kind = 'count' AND valid_days IS NULL AND access_uses IS NOT NULL AND access_uses = 10 AND private_lesson_credits = 0)
    ),
    CHECK ((kind IN ('monthly', 'quarterly', 'yearly') AND valid_until IS NOT NULL
            AND DATEDIFF(valid_until, valid_from) = valid_days)
        OR (kind = 'count' AND valid_until IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE memberships COMMENT='会员卡表：会员购买的产品实例，记录剩余次数和课节，支持作废';
ALTER TABLE memberships MODIFY COLUMN valid_from DATE NOT NULL COMMENT '生效日期：门禁权限起始日（含当日）';
ALTER TABLE memberships MODIFY COLUMN valid_until DATE NULL COMMENT '失效日期：门禁权限截止日（不含当日），次卡为NULL';
ALTER TABLE memberships MODIFY COLUMN remaining_accesses INT NULL COMMENT '剩余入场次数：次卡专用，私教课产品为NULL';
ALTER TABLE memberships MODIFY COLUMN remaining_private_lessons INT NOT NULL COMMENT '账面剩余课节：尚未消课的课节数，包含已被预约占用的课节';
ALTER TABLE memberships MODIFY COLUMN reserved_private_lessons INT NOT NULL COMMENT '预约占用课节：已预约但未消课的课节数';
ALTER TABLE memberships MODIFY COLUMN status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态：active=可用, void=已作废（退卡或管理员作废）';


CREATE TABLE payments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    membership_id BIGINT NOT NULL UNIQUE,
    member_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    method VARCHAR(16) NOT NULL,
    paid_at DATETIME(6) NOT NULL,
    operator_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (membership_id, member_id) REFERENCES memberships(id, member_id),
    FOREIGN KEY (operator_id) REFERENCES accounts(id),
    KEY ix_payment_time (paid_at, id),
    CHECK (amount > 0),
    CHECK (method IN ('cash', 'card', 'transfer'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE payments COMMENT='收款记录表：办卡收款，一对一关联会员卡';
ALTER TABLE payments MODIFY COLUMN membership_id BIGINT NOT NULL UNIQUE COMMENT '会员卡ID：与会员卡一对一，保证每张卡只有一条收款记录';
ALTER TABLE payments MODIFY COLUMN method VARCHAR(16) NOT NULL COMMENT '支付方式：cash=现金, card=刷卡, transfer=转账';
ALTER TABLE payments MODIFY COLUMN paid_at DATETIME(6) NOT NULL COMMENT '收款时刻：业务时间，可能早于记录创建时间';
ALTER TABLE payments MODIFY COLUMN operator_id BIGINT NOT NULL COMMENT '操作员ID：收款的前台或管理员账号';


CREATE TABLE gym_entries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    membership_id BIGINT NOT NULL,
    business_date DATE NOT NULL,
    entered_at DATETIME(6) NOT NULL,
    accesses_used INT NOT NULL,
    operator_id BIGINT NOT NULL,
    FOREIGN KEY (membership_id, member_id) REFERENCES memberships(id, member_id),
    FOREIGN KEY (operator_id) REFERENCES accounts(id),
    UNIQUE KEY uq_entry_member_day (member_id, business_date),
    CHECK (accesses_used IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE gym_entries COMMENT='门禁入场记录表：记录会员入场，每人每自然日只记录一次';
ALTER TABLE gym_entries MODIFY COLUMN business_date DATE NOT NULL COMMENT '业务日期：入场的自然日，用于去重和报表';
ALTER TABLE gym_entries MODIFY COLUMN entered_at DATETIME(6) NOT NULL COMMENT '入场时刻：实际刷卡时间';
ALTER TABLE gym_entries MODIFY COLUMN accesses_used INT NOT NULL COMMENT '扣除次数：次卡扣1次，私教课产品扣0次';


CREATE TABLE courses (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    duration_minutes INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CHECK (CHAR_LENGTH(TRIM(name)) > 0 AND duration_minutes BETWEEN 1 AND 150),
    CHECK (kind = 'private'),
    CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE courses COMMENT='课程模板表：定义课程类型和时长，当前只支持私教课';
ALTER TABLE courses MODIFY COLUMN kind VARCHAR(16) NOT NULL COMMENT '课程类型：当前只支持 private=私教课';
ALTER TABLE courses MODIFY COLUMN duration_minutes INT NOT NULL COMMENT '时长（分钟）：1~150分钟';


CREATE TABLE rooms (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    capacity INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CHECK (CHAR_LENGTH(TRIM(name)) > 0 AND capacity > 0),
    CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE rooms COMMENT='教室表：课程场地，记录容量';
ALTER TABLE rooms MODIFY COLUMN capacity INT NOT NULL COMMENT '容量：可同时容纳的人数';


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


CREATE TABLE bookings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    member_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    membership_id BIGINT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'reserved',
    booked_at DATETIME(6) NOT NULL,
    checked_in_at DATETIME(6) NULL,
    closed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (session_id) REFERENCES course_sessions(id),
    FOREIGN KEY (membership_id, member_id) REFERENCES memberships(id, member_id),
    UNIQUE KEY uq_booking_member_session (member_id, session_id),
    UNIQUE KEY uq_booking_card (id, membership_id),
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


CREATE TABLE consumptions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    booking_id BIGINT NOT NULL UNIQUE,
    membership_id BIGINT NOT NULL,
    lessons_used INT NOT NULL,
    completed_at DATETIME(6) NOT NULL,
    operator_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (booking_id, membership_id) REFERENCES bookings(id, membership_id),
    FOREIGN KEY (operator_id) REFERENCES accounts(id),
    CHECK (lessons_used = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE consumptions COMMENT='消课记录表：课节完成后扣减课节数，一对一关联预约';
ALTER TABLE consumptions MODIFY COLUMN booking_id BIGINT NOT NULL UNIQUE COMMENT '预约ID：与预约一对一，保证每个预约只消课一次';
ALTER TABLE consumptions MODIFY COLUMN lessons_used INT NOT NULL COMMENT '消课节数：当前固定为1';
ALTER TABLE consumptions MODIFY COLUMN completed_at DATETIME(6) NOT NULL COMMENT '完成时刻：业务时间';


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


CREATE TABLE operation_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    request_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    actor_id BIGINT NOT NULL,
    operation VARCHAR(50) NOT NULL,
    payload_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    result_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (actor_id) REFERENCES accounts(id),
    CHECK (operation IN ('sell_product', 'create_session', 'cancel_session', 'book', 'cancel_booking', 'register_entry'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE operation_records COMMENT='操作记录表：幂等性检查和审计日志，记录关键业务操作';
ALTER TABLE operation_records MODIFY COLUMN request_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE COMMENT '请求ID：UUID，用于幂等性检查，防止重复提交';
ALTER TABLE operation_records MODIFY COLUMN actor_id BIGINT NOT NULL COMMENT '操作者ID：执行操作的账号';
ALTER TABLE operation_records MODIFY COLUMN operation VARCHAR(50) NOT NULL COMMENT '操作类型：sell_product=销售产品, create_session=排课, cancel_session=取消课次, book=预约, cancel_booking=取消预约, register_entry=门禁登记';
ALTER TABLE operation_records MODIFY COLUMN payload_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL COMMENT '请求哈希：SHA-256，用于检测相同请求ID的内容是否一致';
ALTER TABLE operation_records MODIFY COLUMN result_id BIGINT NOT NULL COMMENT '结果ID：关联的业务记录ID（如会员卡ID、课节ID等）';
