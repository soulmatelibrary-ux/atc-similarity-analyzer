-- 유사호출 감시 시뮬레이션 시스템 SQLite 스키마
-- Version 1.0

-- ============================================================================
-- 1. 기본 데이터 테이블 (비행 계획 원본 데이터)
-- ============================================================================

CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    callsign TEXT NOT NULL,
    dept_airport_cd TEXT,
    dest_airport_cd TEXT,
    aircraft_type TEXT,
    spd TEXT,
    alt TEXT,
    enr TEXT,
    info_cn TEXT,
    eet TEXT,
    eobd DATE NOT NULL,
    eobt TIME NOT NULL,
    raw_sector_times TEXT,  -- 원본 섹터 진입진출시간

    -- 고도 상승 계산 관련 컬럼
    calculated_speed_kmh INTEGER,  -- 실제 사용된 속도 (기종 fallback 포함)
    speed_source TEXT,  -- 'csv' | 'aircraft_profile' | 'default'
    climb_rate_fpm INTEGER,  -- 기종별 상승률
    cruise_flight_level INTEGER,  -- CFL (ALT에서 파싱한 고도, feet)
    is_climbing BOOLEAN DEFAULT 0,  -- RK 출발 여부 (상승 계산 필요 여부)

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(callsign, eobd, eobt)
);

CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign);
CREATE INDEX IF NOT EXISTS idx_flights_eobd ON flights(eobd);
CREATE INDEX IF NOT EXISTS idx_flights_dept_dest ON flights(dept_airport_cd, dest_airport_cd);


-- ============================================================================
-- 2. 지점별 통과시간 계산 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS waypoint_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id INTEGER NOT NULL,
    waypoint_name TEXT NOT NULL,
    waypoint_sequence INTEGER,
    estimated_time TIME,
    actual_time TIME,

    -- 고도 상승 계산 관련 컬럼
    altitude_ft INTEGER,  -- 해당 지점에서의 고도
    is_climbing BOOLEAN DEFAULT 0,  -- 상승 중 여부
    time_method TEXT,  -- 'simple_linear' | 'eet_backtrack' | NULL

    FOREIGN KEY(flight_id) REFERENCES flights(id) ON DELETE CASCADE,
    UNIQUE(flight_id, waypoint_name)
);

CREATE INDEX IF NOT EXISTS idx_waypoint_times_flight_id ON waypoint_times(flight_id);
CREATE INDEX IF NOT EXISTS idx_waypoint_times_waypoint ON waypoint_times(waypoint_name);


-- ============================================================================
-- 3. 섹터 진입진출 시간 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS sector_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id INTEGER NOT NULL,
    sector_name TEXT NOT NULL,
    entry_time TIME NOT NULL,
    exit_time TIME NOT NULL,

    FOREIGN KEY(flight_id) REFERENCES flights(id) ON DELETE CASCADE,
    UNIQUE(flight_id, sector_name)
);

CREATE INDEX IF NOT EXISTS idx_sector_times_flight_id ON sector_times(flight_id);
CREATE INDEX IF NOT EXISTS idx_sector_times_sector ON sector_times(sector_name);
CREATE INDEX IF NOT EXISTS idx_sector_times_times ON sector_times(entry_time, exit_time);


-- ============================================================================
-- 3.5 고도 상승 계산 비교 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS climb_calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id INTEGER NOT NULL,
    waypoint_name TEXT NOT NULL,
    waypoint_sequence INTEGER,

    -- 방법 A: 단순 선형 상승
    simple_linear_time TIME,
    simple_linear_altitude_ft INTEGER,
    simple_linear_distance_km REAL,

    -- 방법 B: EET 역계산
    eet_backtrack_time TIME,
    eet_backtrack_altitude_ft INTEGER,
    eet_backtrack_distance_km REAL,

    -- 비교 지표
    time_difference_seconds INTEGER,
    altitude_difference_ft INTEGER,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(flight_id) REFERENCES flights(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_climb_calculations_flight_id ON climb_calculations(flight_id);
CREATE INDEX IF NOT EXISTS idx_climb_calculations_waypoint ON climb_calculations(waypoint_name);
CREATE INDEX IF NOT EXISTS idx_climb_calculations_sequence ON climb_calculations(waypoint_sequence);


-- ============================================================================
-- 4. 유사호출 감지 결과 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS similarities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id_1 INTEGER NOT NULL,
    flight_id_2 INTEGER NOT NULL,
    callsign_1 TEXT NOT NULL,
    callsign_2 TEXT NOT NULL,
    similarity_level TEXT NOT NULL,  -- LEVEL_3-4, LEVEL_4-1 등
    similarity_score REAL,

    -- 섹터 겹침 정보
    has_sector_overlap BOOLEAN DEFAULT 0,
    total_overlap_minutes INTEGER DEFAULT 0,
    overlap_count INTEGER DEFAULT 0,  -- 겹치는 섹터 개수

    -- 메타데이터
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(flight_id_1) REFERENCES flights(id) ON DELETE CASCADE,
    FOREIGN KEY(flight_id_2) REFERENCES flights(id) ON DELETE CASCADE,
    UNIQUE(flight_id_1, flight_id_2)
);

CREATE INDEX IF NOT EXISTS idx_similarities_flight_1 ON similarities(flight_id_1);
CREATE INDEX IF NOT EXISTS idx_similarities_flight_2 ON similarities(flight_id_2);
CREATE INDEX IF NOT EXISTS idx_similarities_level ON similarities(similarity_level);
CREATE INDEX IF NOT EXISTS idx_similarities_overlap ON similarities(has_sector_overlap);


-- ============================================================================
-- 5. 섹터 겹침 상세 정보 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS sector_overlaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    similarity_id INTEGER NOT NULL,
    sector_name TEXT NOT NULL,

    -- 항공편 1 시간
    flight1_entry TIME NOT NULL,
    flight1_exit TIME NOT NULL,

    -- 항공편 2 시간
    flight2_entry TIME NOT NULL,
    flight2_exit TIME NOT NULL,

    -- 겹침 시간
    overlap_start TIME NOT NULL,
    overlap_end TIME NOT NULL,
    overlap_minutes INTEGER NOT NULL,

    FOREIGN KEY(similarity_id) REFERENCES similarities(id) ON DELETE CASCADE,
    UNIQUE(similarity_id, sector_name)
);

CREATE INDEX IF NOT EXISTS idx_sector_overlaps_similarity ON sector_overlaps(similarity_id);
CREATE INDEX IF NOT EXISTS idx_sector_overlaps_sector ON sector_overlaps(sector_name);
CREATE INDEX IF NOT EXISTS idx_sector_overlaps_minutes ON sector_overlaps(overlap_minutes);


-- ============================================================================
-- 6. 통계 캐시 테이블 (대시보드 성능 최적화)
-- ============================================================================

CREATE TABLE IF NOT EXISTS statistics_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,  -- 'total_similarities', 'level_distribution' 등
    cache_value TEXT,  -- JSON 형식
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_statistics_cache_key ON statistics_cache(cache_key);


-- ============================================================================
-- 7. 업로드 이력 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS upload_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    record_count INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed',  -- 'pending', 'completed', 'failed'
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_upload_history_date ON upload_history(uploaded_at);

-- ============================================================================
-- 8. 항공기 기종 프로필 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS aircraft_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    icao_code TEXT NOT NULL UNIQUE,
    iata_code TEXT,
    manufacturer TEXT,
    model TEXT,
    type_description TEXT,
    default_speed_kmh INTEGER,
    default_speed_knots INTEGER,
    default_climb_fpm INTEGER,
    default_ceiling_fl INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aircraft_profiles_icao ON aircraft_profiles(icao_code);
CREATE INDEX IF NOT EXISTS idx_aircraft_profiles_manufacturer ON aircraft_profiles(manufacturer);
CREATE INDEX IF NOT EXISTS idx_aircraft_profiles_model ON aircraft_profiles(model);

INSERT OR IGNORE INTO aircraft_profiles (
    icao_code, iata_code, manufacturer, model, type_description,
    default_speed_kmh, default_speed_knots, default_climb_fpm, default_ceiling_fl, notes
) VALUES
('B77L', '77L', 'Boeing', '777-200LRF', 'Long-range cargo freighter', 905, 489, 2000, 430, 'Seed data'),
('B744', '744', 'Boeing', '747-400', 'Heavy cargo/passenger', 920, 497, 1800, 410, 'Seed data'),
('A333', '333', 'Airbus', 'A330-300', 'Wide-body passenger', 880, 475, 1700, 410, 'Seed data');


-- ============================================================================
-- 9. 시스템 설정 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 설정 값 삽입
INSERT OR IGNORE INTO system_settings (key, value, description) VALUES
('min_overlap_minutes', '2', '최소 공존시간 (분)'),
('max_flights_per_upload', '50000', '한 번에 업로드 가능한 최대 항공편 수'),
('cache_ttl_minutes', '60', '통계 캐시 유효 시간 (분)'),
('db_version', '1.0', '데이터베이스 스키마 버전');


-- ============================================================================
-- 10. 관리자 계정 테이블 (인증용)
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    allowed_tabs TEXT NOT NULL DEFAULT '["*"]',
    is_active BOOLEAN DEFAULT 1,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);

INSERT OR IGNORE INTO admin_users (username, email, password_hash, role, allowed_tabs, is_active)
VALUES (
    'admin',
    'admin@system.local',
    'pbkdf2:sha256:600000$I3SyXih4aupMjb6n$9fd1e457d9b27b9b51e3f1ea752b8e42f1cc01b733eb368e2e03c30fa29a77c0',
    'admin',
    '["*"]',
    1
);

INSERT OR IGNORE INTO admin_users (username, email, password_hash, role, allowed_tabs, is_active)
VALUES (
    'parkeungi21',
    'parkeungi21@korea.kr',
    'pbkdf2:sha256:600000$uiWpD9I83Wo77Ipu$543872c7ae62f395945c804303c91d3a0715f53dfdab62d37e3fcb9c3eabfcda',
    'user',
    '["*"]',
    1
);
