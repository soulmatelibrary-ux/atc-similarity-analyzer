# 🏗️ 아키텍처 설명서

Airspace-Sim-Station의 시스템 아키텍처, 컴포넌트 구조, 데이터 흐름을 설명합니다.

## 📐 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│                      (localhost:3000)                            │
└────────────────────────────────────┬──────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │   HTTP / CORS                   │
                    ▼                                 ▼
        ┌─────────────────────────┐    ┌──────────────────────┐
        │   Frontend (Frontend)   │    │  API Server (Flask)  │
        │   - HTML/CSS/JS         │    │  (localhost:8888)    │
        │   - RESTful API Client  │    │  - Blueprint Routes  │
        │   - License Display     │    │  - License Checking  │
        └────────────┬────────────┘    └──────────┬───────────┘
                     │                            │
                     └────────────────┬───────────┘
                                      │
                    ┌─────────────────┴──────────────────┐
                    │                                    │
                    ▼                                    ▼
        ┌──────────────────────┐          ┌──────────────────────┐
        │   Core Services      │          │  License Manager     │
        │ - Flight Service     │          │  - Validation        │
        │ - Similarity Engine  │          │  - Limits Checking   │
        │ - File Validator     │          │  - Key Generation    │
        └──────────┬───────────┘          └──────────┬───────────┘
                   │                                 │
                   └─────────────────┬───────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │   SQLite Database      │
                        │ - flights              │
                        │ - similarities         │
                        │ - sector_times         │
                        │ - sector_overlaps      │
                        │ - aircraft_profiles    │
                        └────────────────────────┘
```

---

## 📁 폴더 구조

### 백엔드 구조

```
backend/
├── app.py                    # Flask 메인 애플리케이션
│   ├── 라이선스 초기화
│   ├── Blueprint 등록
│   └── 라우트 정의
│
└── license_api.py            # 라이선스 API 엔드포인트
    ├── GET /api/license/info
    ├── GET /api/license/limits
    └── GET /api/license/status

core/
├── similarity_engine.py      # 유사도 분석 엔진
│   ├── check_similarity()
│   ├── calculate_overlap()
│   └── get_risk_level()
│
├── flight_service.py         # 항공편 데이터 처리
│   ├── process_and_save_flights()
│   ├── validate_flight_data()
│   └── update_memory_cache()
│
├── flight_processor.py       # 비행 경로 계산
│   ├── parse_route()
│   ├── calculate_trajectory()
│   └── parse_time()
│
└── modeling_resources.py     # 모델링 리소스 관리

utils/
├── license_manager.py        # 라이선스 검증 시스템
│   ├── LicenseManager 클래스
│   ├── _load_license()
│   ├── _validate_commercial_license()
│   ├── get_limits()
│   └── generate_license_key()
│
├── file_validator.py         # 파일 유효성 검증
│   ├── FileValidator 클래스
│   └── validate_file()
│
├── constants.py              # 상수 정의
│   ├── SIMILARITY_LEVELS
│   ├── DEFAULT_FILTERS
│   └── DEVELOPMENT_LIMITS
│
├── logger.py                 # 로깅 시스템
├── sector_parser.py          # 섹터 파싱
└── similarity_optimizer.py   # 유사도 최적화

database/
├── db_manager.py             # 데이터베이스 관리
│   ├── DatabaseManager 클래스
│   ├── execute_query()
│   ├── get_statistics()
│   └── get_similarities()
│
└── init_db.py                # DB 초기화 스크립트
```

### 프론트엔드 구조

```
frontend/
├── index.html                # 메인 HTML
│   ├── 헤더 (라이선스 정보 표시)
│   ├── 탭 네비게이션
│   ├── 각 탭 콘텐츠
│   └── 모달 팝업
│
├── css/
│   ├── style.css             # 전역 스타일
│   │   ├── 레이아웃
│   │   ├── 테이블 스타일
│   │   ├── 모달 스타일
│   │   └── 라이선스 표시 스타일
│   └── ...
│
└── js/
    ├── api.js                # API 클라이언트
    │   ├── API_BASE_URL
    │   └── 요청/응답 처리
    │
    ├── dashboard.js          # 대시보드 로직
    │   ├── initializeEventListeners()
    │   ├── checkSystemHealth()
    │   ├── loadLicenseInfo()     ← 라이선스 로드
    │   ├── updateLicenseDisplay() ← 라이선스 표시
    │   └── loadDashboardData()
    │
    ├── ui.js                 # UI 컨트롤러
    │   ├── 탭 전환 처리
    │   ├── 모달 관리
    │   └── 데이터 표시
    │
    └── ...
```

---

## 🔄 데이터 흐름

### 1. 항공편 업로드 흐름

```
사용자가 CSV 파일 선택
    │
    ▼
Frontend: submitForm()
    │
    ▼
API: POST /api/upload/flights
    │
    ├─ 파일 검증 ✓
    ├─ 라이선스 체크 ✓ (max_flights_per_upload)
    │
    ▼
FileValidator: validate_file()
    │
    ▼
Core: process_and_save_flights() [백그라운드]
    │
    ├─ 데이터 파싱
    ├─ 유사도 계산
    ├─ 섹터 겹침 분석
    │
    ▼
Database: INSERT
    │
    ▼
Frontend: 진행 상황 표시 (poll /api/upload/progress)
```

### 2. 라이선스 검증 흐름

```
API 요청 수신
    │
    ▼
get_license_manager()
    │
    ├─ .license/license.json 파일 확인
    │  ├─ 있음 → 상업용 라이선스
    │  └─ 없음 → 개발용 라이선스
    │
    ▼
LicenseManager._validate_commercial_license()
    │
    ├─ 필수 필드 확인
    ├─ 만료일 검증
    ├─ HMAC 서명 검증
    │
    ▼
Features limits 적용
    │
    ├─ 업로드: max_flights_per_upload 체크
    ├─ 내보내기: export_limit 체크
    ├─ 항공기 임포트: is_commercial() 체크
    │
    ▼
기능 실행 또는 403 Forbidden 반환
```

### 3. 유사호출 분석 흐름

```
업로드된 항공편 데이터
    │
    ▼
Core: check_similarity() [모든 쌍에 대해]
    │
    ├─ Callsign 텍스트 유사도 계산
    ├─ Routing/Speed 유사도 계산
    ├─ Timing 유사도 계산
    │
    ▼
Similarity Score 산출
    │
    ├─ LEVEL 5: 90-100 (Critical)
    ├─ LEVEL 4: 65-89 (Caution)
    └─ LEVEL 3: 50-64 (Notice)
    │
    ▼
위험도가 높은 쌍만 저장
    │
    ▼
Database: INSERT INTO similarities
    │
    ▼
Frontend: 유사호출 목록 표시
```

---

## 🔐 라이선스 시스템 아키텍처

```
┌─────────────────────────────────────────┐
│      LicenseManager 싱글톤               │
├─────────────────────────────────────────┤
│                                         │
│  _load_license()                        │
│  ├─ .license/license.json 확인          │
│  ├─ 타입 결정 (dev/commercial)         │
│  └─ 검증 실행                           │
│                                         │
│  _validate_commercial_license()         │
│  ├─ 필드 확인                          │
│  ├─ 만료일 검증                        │
│  └─ HMAC 서명 검증                     │
│                                         │
│  get_limits()                           │
│  ├─ DEVELOPMENT_LIMITS 반환 (dev)      │
│  └─ COMMERCIAL_LIMITS 반환 (commercial)│
│                                         │
│  @commercial_only decorator             │
│  └─ 상업용 기능 보호                    │
│                                         │
└─────────────────────────────────────────┘
            ▲
            │ (의존)
            │
    ┌───────┴─────────┬────────────┐
    ▼                 ▼            ▼
API 엔드포인트    업로드 체크  내보내기 체크
/api/license/*   max_flights  export_limit
```

---

## 🗄️ 데이터베이스 스키마

### flights 테이블

```sql
CREATE TABLE flights (
    id INTEGER PRIMARY KEY,
    callsign TEXT,           -- 항공편 호출부호
    departure_airport TEXT,  -- 출발공항
    arrival_airport TEXT,    -- 도착공항
    aircraft_type TEXT,      -- 항공기 기종
    speed_kmh REAL,          -- 속도 (km/h)
    altitude_fl INTEGER,     -- 고도 (FL)
    route TEXT,              -- 비행 경로
    eobt TEXT,               -- 추정 이륙 시간
    eobd TEXT,               -- 추정 이륙 날짜
    created_at TIMESTAMP     -- 생성 시간
);
```

### similarities 테이블

```sql
CREATE TABLE similarities (
    id INTEGER PRIMARY KEY,
    callsign_1 TEXT,
    callsign_2 TEXT,
    flight_id_1 INTEGER,
    flight_id_2 INTEGER,
    similarity_score REAL,
    similarity_level TEXT,
    has_sector_overlap BOOLEAN,
    total_overlap_minutes REAL,
    overlap_count INTEGER,
    detected_at TIMESTAMP
);
```

### sector_times 테이블

```sql
CREATE TABLE sector_times (
    id INTEGER PRIMARY KEY,
    flight_id INTEGER,
    sector_name TEXT,
    entry_time TEXT,         -- 섹터 진입 시간
    exit_time TEXT,          -- 섹터 진출 시간
    FOREIGN KEY (flight_id) REFERENCES flights(id)
);
```

### aircraft_profiles 테이블

```sql
CREATE TABLE aircraft_profiles (
    id INTEGER PRIMARY KEY,
    icao_code TEXT UNIQUE,   -- ICAO 코드
    iata_code TEXT,
    manufacturer TEXT,
    model TEXT,
    type_description TEXT,
    default_speed_kmh INTEGER,
    default_speed_knots INTEGER,
    default_climb_fpm INTEGER,
    default_ceiling_fl INTEGER,
    notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## 🔌 API 계층

### 엔드포인트 분류

```
항공편 관리
├── POST /api/upload/flights
├── GET /api/flights/dates
├── GET /api/flights/all
└── GET /api/flights/{id}

유사호출 분석
├── GET /api/similarity/results
├── GET /api/similarity/levels
└── POST /api/similarity/check

라이선스 관리 ⭐
├── GET /api/license/info
├── GET /api/license/limits
└── GET /api/license/status

통계 분석
├── GET /api/statistics/summary
├── GET /api/statistics/detailed
└── GET /api/statistics/period-analysis

내보내기
├── GET /api/export/json
└── GET /api/export/flights/excel
```

### 요청/응답 형식

**성공 응답**:
```json
{
  "status": "success",
  "data": { /* 데이터 */ }
}
```

**오류 응답**:
```json
{
  "status": "error",
  "message": "오류 메시지",
  "data": { /* 추가 정보 */ }
}
```

**라이선스 제한 오류 (403)**:
```json
{
  "status": "error",
  "message": "라이선스 제한: ...",
  "data": {
    "license_type": "development",
    "current": 150,
    "limit": 100
  }
}
```

---

## 🎯 컴포넌트 책임

### Frontend

- **UI 렌더링**: HTML, CSS로 사용자 인터페이스 표시
- **사용자 입력 처리**: 파일 업로드, 필터 설정
- **API 통신**: fetch를 통한 REST API 호출
- **라이선스 정보 표시**: 헤더에 현재 라이선스 상태 표시
- **상태 관리**: 간단한 전역 변수로 상태 관리

### Backend (API Server)

- **요청 라우팅**: Flask로 HTTP 요청 처리
- **라이선스 검증**: 모든 API 요청에 대한 라이선스 체크
- **비즈니스 로직**: 항공편 분석, 유사도 계산
- **데이터베이스**: CRUD 작업 수행
- **에러 처리**: 적절한 HTTP 상태 코드 반환

### Core Services

- **유사도 계산**: 알고리즘으로 콜사인 유사도 계산
- **데이터 검증**: 파일 형식, 데이터 무결성 확인
- **비행 경로 분석**: 웨이포인트, 섹터 겹침 계산

### License Manager

- **라이선스 로드**: .license/license.json 파일 읽기
- **검증**: 서명, 만료일 확인
- **제한 적용**: 기능별 제한사항 반환
- **키 생성**: 상업용 라이선스 키 생성 (관리자 용)

---

## 🔄 요청 처리 파이프라인

```
1. HTTP 요청 수신
   ↓
2. 요청 파싱 (메소드, 경로, 본문)
   ↓
3. 인증/권한 확인 (필요 시)
   ↓
4. 라이선스 검증 ← ⭐ 핵심!
   ├─ 라이선스 타입 확인
   ├─ 기능 제한 확인
   └─ 초과 시 403 반환
   ↓
5. 입력 데이터 검증
   ↓
6. 비즈니스 로직 실행
   ├─ 파일 처리
   ├─ DB 쿼리
   ├─ 계산 실행
   └─ 캐시 업데이트
   ↓
7. 응답 생성
   ├─ 데이터 직렬화
   ├─ 메타데이터 추가
   └─ JSON 형식화
   ↓
8. 응답 전송
```

---

## 📊 상태 관리

### Frontend 상태

```javascript
// 전역 상태 변수들
app_state = {
    flights: [],              // 메모리 캐시
    current_flights: [],      // 현재 표시 중인 항공편
    selected_date: null,      // 선택된 날짜
    filters: {}               // 활성 필터
};

// 라이선스 정보
license_info = {
    type: 'development',      // development | commercial
    is_valid: true,
    message: '라이선스 정보',
    expiry_date: 'N/A'
};
```

### Backend 상태

```python
# Flask 앱 상태
app_state = {
    'flights': []             # 메모리 캐시
}

# 라이선스 상태 (싱글톤)
_license_manager = LicenseManager()
```

---

## 🔒 보안 고려사항

### 1. 파일 업로드

```
위험 ❌          →    보안 ✓
파일 받기        →    확장자 검증
저장하기         →    MIME 타입 검증
처리하기         →    파일 크기 제한
                 →    경로 정규화 (secure_filename)
```

### 2. SQL 주입 방지

```python
# ❌ Bad
query = f"SELECT * FROM flights WHERE id = {user_input}"

# ✅ Good
query = "SELECT * FROM flights WHERE id = ?"
db.execute(query, (user_input,))
```

### 3. 라이선스 서명

```python
# HMAC-SHA256로 라이선스 서명 검증
signature = hmac.new(
    master_key.encode(),
    data_to_sign.encode(),
    hashlib.sha256
).hexdigest()

# 시간 공격 방지
hmac.compare_digest(signature, expected_signature)
```

---

## 🚀 성능 최적화

### 1. 메모리 캐싱

```python
# 항공편 데이터를 메모리에 캐싱
app_state['flights'] = flights_list
# 재업로드 시 clear + 새 데이터 로드
```

### 2. 데이터베이스 인덱싱

```sql
CREATE INDEX idx_flights_callsign ON flights(callsign);
CREATE INDEX idx_similarities_level ON similarities(similarity_level);
```

### 3. 백그라운드 처리

```python
# 시간이 오래 걸리는 작업은 스레드로 처리
bg_thread = threading.Thread(
    target=process_flights_background,
    daemon=True
)
bg_thread.start()
```

---

마지막 업데이트: 2025-12-27

