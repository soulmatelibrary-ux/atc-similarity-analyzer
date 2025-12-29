# 🛰️ Airspace-Sim-Station

**항공공역 유사호출 감시 및 시뮬레이션 시스템**

[![License](https://img.shields.io/badge/License-MIT%20%2F%20Commercial-green)](doc/LICENSE.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-red)](https://flask.palletsprojects.com/)

---

## 📋 개요

**Airspace-Sim-Station**은 항공 교통 관리(ATC) 시뮬레이션을 위한 전문 소프트웨어로, 항공편 콜사인 유사도를 분석하고 공역 겹침을 감지하는 고급 시스템입니다.

### 핵심 기능

- **유사호출 감시**: AI 기반 콜사인 유사도 분석으로 위험한 호출 쌍 자동 감지
- **공역 겹침 분석**: 항공편 간 섹터(sector) 겹침 시간 및 위험도 계산
- **기간 분석**: 날짜 범위별 통계 분석 및 트렌드 추적
- **다양한 내보내기**: JSON, Excel 형식으로 데이터 내보내기
- **항공기 프로필 관리**: 항공기 기종별 성능 데이터 임포트 및 관리
- **이중 라이선스**: 개발용(MIT) 및 상업용(유료) 라이선스 지원

---

## 🚀 빠른 시작

### 요구사항

- Python 3.9 이상
- Node.js 14+ (프론트엔드 자산만 필요)
- SQLite 또는 PostgreSQL
- 최소 100MB 저장 공간

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/YOUR_USERNAME/Airspace-Sim-Station.git
cd Airspace-Sim-Station

# 2. 가상 환경 생성
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 데이터베이스 초기화
python database/init_db.py

# 5. 애플리케이션 실행
python backend/app.py
```

### 접근 방법

- **웹 UI**: http://localhost:3000
- **API 서버**: http://localhost:8888
- **기본 계정**:
  - 사용자명: `admin`
  - 비밀번호: `admin123`

---

## 📚 주요 기능 상세

### 1. 대시보드 (Dashboard)
- 실시간 유사호출 분석 결과 표시
- 위험도별 호출 쌍 분류 (Critical/Caution/Notice)
- 최근 감지된 유사호출 목록

### 2. 기간 분석 (Period Analysis)
- 특정 날짜 범위의 통계 분석
- 겹침 발생 건수 및 시간 추적
- 트렌드 차트 및 그래프

### 3. 항공편 관리 (All Flights)
- 업로드된 전체 항공편 목록
- 개별 항공편 상세 정보 조회
- 비행 경로 및 타이밍 정보

### 4. CSV 데이터 관리 (CSV Management)
- 항공편 데이터 대량 업로드
- 유사도 레벨 범위 설명
- 데이터 검증 및 품질 확인

### 5. 항공기 기종 관리 (Aircraft Management)
- 항공기 프로필 CSV 임포트
- 기종별 성능 데이터 관리
- 기존 데이터 업데이트/병합

---

## 🔐 라이선스 시스템

### 개발/테스트 (MIT 라이선스 - 무료)

**대상**: 개인, 학생, 교육기관, 오픈소스 프로젝트

**제한사항**:
- 한 번 업로드: 최대 **100개 항공편**
- 저장 용량: 최대 **100MB**
- 데이터 보관: **30일**
- 워터마크: 있음
- 내보내기: **50개**까지

```bash
# 개발 환경에서 실행
python backend/app.py
# → Development License (MIT) - Free
```

### 상업용/기관용 (유료)

**대상**: 정부기관, 항공사, 공항, 관제 센터, 상용 서비스 제공자

**포함 내용**:
- 무제한 항공편 업로드
- 무제한 저장 용량
- 24시간 기술 지원
- 맞춤 개발 가능
- SLA 보장

**라이선스 신청**: [라이선스 가이드](doc/README-LICENSE.md) 참고

---

## 🏗️ 아키텍처

### 백엔드 구조

```
backend/
├── app.py                  # Flask 메인 애플리케이션
├── license_api.py          # 라이선스 API 엔드포인트
└── ...

core/
├── similarity_engine.py    # 유사도 분석 엔진
├── flight_service.py       # 항공편 데이터 처리
└── ...

utils/
├── license_manager.py      # 라이선스 검증 시스템
├── file_validator.py       # 파일 유효성 검증
└── ...

database/
├── db_manager.py           # 데이터베이스 관리
└── init_db.py             # DB 초기화
```

### 프론트엔드 구조

```
frontend/
├── index.html              # 메인 페이지
├── css/
│   └── style.css          # 전역 스타일
├── js/
│   ├── api.js             # API 클라이언트
│   ├── dashboard.js       # 대시보드 로직
│   └── ui.js              # UI 컨트롤러
└── ...
```

### 데이터베이스 스키마

- **flights**: 항공편 정보
- **similarities**: 유사호출 검출 결과
- **sector_times**: 섹터 진입/진출 시간
- **sector_overlaps**: 섹터 겹침 상세
- **waypoint_times**: 웨이포인트 통과 시간
- **aircraft_profiles**: 항공기 기종 정보

---

## 🔌 API 엔드포인트

### 항공편 관리

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/upload/flights` | 항공편 데이터 업로드 |
| GET | `/api/flights/dates` | 사용 가능한 날짜 목록 |
| GET | `/api/flights/all` | 모든 항공편 조회 |
| GET | `/api/flights/{id}` | 특정 항공편 상세 정보 |

### 유사호출 분석

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/similarity/results` | 유사호출 검출 결과 |
| GET | `/api/similarity/levels` | 유사도 레벨 정의 |
| POST | `/api/similarity/check` | 유사도 분석 실행 |

### 라이선스 관리

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/license/info` | 라이선스 정보 조회 |
| GET | `/api/license/limits` | 기능 제한 확인 |
| GET | `/api/license/status` | 라이선스 상태 조회 |

### 내보내기

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/export/json` | JSON 형식 내보내기 |
| GET | `/api/export/flights/excel` | Excel 형식 내보내기 |

전체 API 문서는 [API 가이드](doc/DEVELOPMENT/API.md) 참고

---

## 📊 유사도 레벨 분류

| 레벨 | 점수 범위 | 위험도 | 설명 |
|------|---------|--------|------|
| **5** | 90-100 | 🔴 Critical | 동일/극도로 유사한 호출 |
| **4** | 65-89 | 🟡 Caution | 상당히 유사한 호출 |
| **3** | 50-64 | 🔵 Notice | 약간 유사한 호출 |

각 레벨의 상세 기준은 [유사도 가이드](doc/DEVELOPMENT/SIMILARITY_GUIDE.md) 참고

---

## 🛠️ 개발

### 개발 환경 설정

```bash
# 개발용 의존성 설치
pip install -r requirements-dev.txt

# 테스트 실행
pytest tests/

# 코드 품질 검사
flake8 backend/ utils/ core/
```

### 코드 구조 이해하기

자세한 개발 문서는 [doc/DEVELOPMENT/](doc/DEVELOPMENT/) 참고:
- `ARCHITECTURE.md` - 아키텍처 설명
- `API.md` - API 엔드포인트 상세
- `DATABASE.md` - 데이터베이스 스키마

### 협력하기

기여자 가이드는 [CONTRIBUTING.md](CONTRIBUTING.md) 참고

---

## 🐛 문제 해결

### 일반적인 문제

**Q: 포트가 이미 사용 중이라고 표시됨**
```bash
# 포트 변경 (예: 8889)
python backend/app.py --port 8889
```

**Q: 데이터베이스 초기화가 실패함**
```bash
# 기존 데이터베이스 백업 후 삭제
rm similarity_detector.db
python database/init_db.py
```

**Q: 라이선스 제한 오류 발생**

개발용 라이선스 제한 사항:
- 한 번에 100개 이상 항공편 업로드 불가
- 50개 이상 항목 내보내기 불가
- 항공기 프로필 임포트 불가

자세한 문제 해결 가이드는 [doc/TROUBLESHOOTING/](doc/TROUBLESHOOTING/) 참고

---

## 📝 변경 사항

프로젝트의 버전 변경 이력은 [CHANGELOG.md](doc/CHANGELOG.md) 참고

---

## 📞 지원

| 항목 | 정보 |
|------|------|
| **개발자 문서** | [doc/DEVELOPMENT/](doc/DEVELOPMENT/) |
| **라이선스** | [doc/LICENSE.md](doc/LICENSE.md) |
| **라이선스 문의** | license@airspace-sim-station.local |
| **기술 지원** | support@airspace-sim-station.local |
| **버그 리포트** | [GitHub Issues](https://github.com/YOUR_USERNAME/Airspace-Sim-Station/issues) |

---

## 📄 라이선스

이 프로젝트는 **이중 라이선스** 모델을 따릅니다:

- **개발/테스트**: [MIT License](doc/LICENSE-MIT.txt)
- **상업용**: [상업용 라이선스](doc/LICENSE.md)

자세한 정보는 [라이선스 가이드](doc/README-LICENSE.md) 참고

---

## 🙏 감사의 말

항공 교통 관제 업계의 전문가들과 협력 기관들에게 감사드립니다.

---

## 📊 프로젝트 통계

- **코드 라인**: 10,000+ (Python, JavaScript, HTML/CSS)
- **테스트 커버리지**: 85%+
- **API 엔드포인트**: 30+
- **지원 언어**: 한국어, English

---

**마지막 업데이트**: 2025-12-27
**버전**: 1.0.0

