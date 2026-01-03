-- ============================================================================
-- 참조 데이터 테이블 스키마 (Excel → Database 마이그레이션)
-- ============================================================================

-- waypoints 테이블: enroute.xlsx 데이터
-- 항로상의 경유지점(FIX) 정보를 저장
CREATE TABLE IF NOT EXISTS waypoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enr_nm TEXT,           -- 항로명
    seq INTEGER,           -- 순서
    fixpnt TEXT NOT NULL,  -- 경유지점명 (FIX)
    lat REAL NOT NULL,     -- 위도
    lon REAL NOT NULL,     -- 경도
    stat TEXT,             -- 상태
    sector TEXT            -- 소속 섹터
);

-- 빠른 조회를 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_waypoints_fixpnt ON waypoints(fixpnt);
CREATE INDEX IF NOT EXISTS idx_waypoints_sector ON waypoints(sector);
CREATE INDEX IF NOT EXISTS idx_waypoints_enr_nm ON waypoints(enr_nm);

-- sector_boundaries 테이블: sector1.xlsx 데이터
-- 섹터의 경계를 정의하는 폴리곤 좌표
CREATE TABLE IF NOT EXISTS sector_boundaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_id TEXT NOT NULL,  -- 섹터 ID (예: JH, GH, KL 등)
    seq INTEGER,              -- 폴리곤 순서
    lat REAL NOT NULL,        -- 위도
    lon REAL NOT NULL,        -- 경도
    alt INTEGER DEFAULT 0,    -- 최저 고도 (FL)
    alt2 INTEGER DEFAULT 99999 -- 최고 고도 (FL)
);

-- 섹터별 빠른 조회를 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_sector_boundaries_sector ON sector_boundaries(sector_id);
CREATE INDEX IF NOT EXISTS idx_sector_boundaries_seq ON sector_boundaries(sector_id, seq);
