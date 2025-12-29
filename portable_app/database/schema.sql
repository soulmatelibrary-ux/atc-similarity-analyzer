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
-- 8. 시스템 설정 테이블
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
