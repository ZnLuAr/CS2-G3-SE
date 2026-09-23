-- 初始结构脚本。执行顺序按外键依赖排列；版本记录由初始化命令写入。
CREATE TABLE schema_versions (
    version INT PRIMARY KEY,
    applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
        (kind = 'monthly' AND valid_days = 30 AND private_lesson_credits = 20 AND access_uses IS NULL)
        OR (kind = 'quarterly' AND valid_days = 90 AND private_lesson_credits = 64 AND access_uses IS NULL)
        OR (kind = 'yearly' AND valid_days = 365 AND private_lesson_credits = 256 AND access_uses IS NULL)
        OR (kind = 'count' AND valid_days IS NULL AND access_uses = 10 AND private_lesson_credits = 0)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
        (kind = 'monthly' AND valid_days = 30 AND private_lesson_credits = 20 AND access_uses IS NULL)
        OR (kind = 'quarterly' AND valid_days = 90 AND private_lesson_credits = 64 AND access_uses IS NULL)
        OR (kind = 'yearly' AND valid_days = 365 AND private_lesson_credits = 256 AND access_uses IS NULL)
        OR (kind = 'count' AND valid_days IS NULL AND access_uses = 10 AND private_lesson_credits = 0)
    ),
    CHECK ((kind IN ('monthly', 'quarterly', 'yearly') AND valid_until IS NOT NULL
            AND DATEDIFF(valid_until, valid_from) = valid_days)
        OR (kind = 'count' AND valid_until IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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

CREATE TABLE reviews (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    booking_id BIGINT NOT NULL UNIQUE,
    rating INT NOT NULL,
    comment VARCHAR(1000) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (booking_id) REFERENCES bookings(id),
    CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
