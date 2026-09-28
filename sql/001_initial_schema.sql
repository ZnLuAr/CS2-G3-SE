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
    request_id CHAR(36)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    actor_id BIGINT NOT NULL,
    operation VARCHAR(50)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    payload_version VARCHAR(16)
        CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'v3',
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
    CONSTRAINT ck_operation_records_payload_version
        CHECK (payload_version IN ('v3', 'legacy-v2')),
    CONSTRAINT ck_operation_records_payload_hash
        CHECK (payload_hash REGEXP '^[0-9a-f]{64}$'),
    KEY ix_operation_actor_time (actor_id, created_at, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE operation_records COMMENT='操作记录表：v3 幂等与审计，payload_version 区分 v3/legacy-v2';
