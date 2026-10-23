-- 课程与预约模块表结构（MySQL 8.0.16+）。
-- 依赖账号、会员和会员卡表：accounts、members、memberships。
-- 合并到 sql/001_initial_schema.sql 时保持本文件中的建表顺序，
-- 并保留字段名、可空性、CHECK 和索引名称，避免与 SQLAlchemy Core
-- 定义（src/db/tables.py）及契约测试出现漂移。

CREATE TABLE coaches (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    account_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    specialty VARCHAR(200) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_coaches_account (account_id),
    CONSTRAINT fk_coaches_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    CONSTRAINT ck_coaches_name CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CONSTRAINT ck_coaches_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE courses (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    kind VARCHAR(16) NOT NULL DEFAULT 'private',
    duration_minutes INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT ck_courses_name CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CONSTRAINT ck_courses_kind CHECK (kind = 'private'),
    CONSTRAINT ck_courses_duration CHECK (duration_minutes BETWEEN 1 AND 150),
    CONSTRAINT ck_courses_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rooms (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    capacity INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT ck_rooms_name CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    CONSTRAINT ck_rooms_capacity CHECK (capacity > 0),
    CONSTRAINT ck_rooms_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE course_sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id BIGINT NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    kind VARCHAR(16) NOT NULL,
    coach_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    starts_at DATETIME(6) NOT NULL,
    ends_at DATETIME(6) NOT NULL,
    capacity INT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'scheduled',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_sessions_course FOREIGN KEY (course_id) REFERENCES courses(id),
    CONSTRAINT fk_sessions_coach FOREIGN KEY (coach_id) REFERENCES coaches(id),
    CONSTRAINT fk_sessions_room FOREIGN KEY (room_id) REFERENCES rooms(id),
    CONSTRAINT ck_sessions_kind CHECK (kind = 'private'),
    CONSTRAINT ck_sessions_time CHECK (ends_at > starts_at),
    CONSTRAINT ck_sessions_capacity CHECK (capacity > 0),
    CONSTRAINT ck_sessions_status CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    KEY ix_course_sessions_coach_start (coach_id, starts_at, id),
    KEY ix_course_sessions_room_start (room_id, starts_at, id),
    KEY ix_course_sessions_start (starts_at, id)
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
    CONSTRAINT fk_bookings_member FOREIGN KEY (member_id) REFERENCES members(id),
    CONSTRAINT fk_bookings_session FOREIGN KEY (session_id) REFERENCES course_sessions(id),
    CONSTRAINT fk_bookings_membership FOREIGN KEY (membership_id) REFERENCES memberships(id),
    CONSTRAINT uq_bookings_member_session UNIQUE (member_id, session_id),
    CONSTRAINT ck_bookings_status CHECK (status IN ('reserved', 'cancelled', 'checked_in', 'completed', 'no_show')),
    KEY ix_bookings_session_status (session_id, status, id),
    KEY ix_bookings_member_status (member_id, status, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE operation_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    request_id VARCHAR(64) NOT NULL,
    actor_id BIGINT NOT NULL,
    operation VARCHAR(32) NOT NULL,
    payload_hash CHAR(64) NOT NULL,
    result_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_operation_actor FOREIGN KEY (actor_id) REFERENCES accounts(id),
    CONSTRAINT uq_operation_request UNIQUE (request_id),
    CONSTRAINT ck_operation_name CHECK (operation IN (
        'sell_product', 'create_session', 'cancel_session',
        'book', 'cancel_booking', 'register_entry'
    ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
