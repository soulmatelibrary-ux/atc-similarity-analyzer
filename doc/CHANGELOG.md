# 📝 변경 이력 (CHANGELOG)

모든 주요 변경사항을 이 파일에서 추적합니다.

형식: [Semantic Versioning](https://semver.org/)

---

## [1.0.0] - 2025-12-27

### 🎉 첫 번째 공식 릴리스

#### ✨ 주요 기능

**1. 이중 라이선스 시스템**
- 개발/테스트용 MIT 라이선스 (무료)
- 상업용/기관용 라이선스 (유료)
- 라이선스 기반 기능 제한 자동 적용
- 라이선스 서명 검증 (HMAC-SHA256)
- 라이선스 정보 API (3개 엔드포인트)

**2. 라이선스 기반 기능 제한**
- 항공편 업로드: 개발용 100개 제한 → 상업용 무제한
- 데이터 내보내기: 개발용 50개 제한 → 상업용 무제한
- 항공기 프로필 임포트: 개발용 불가 → 상업용 가능
- 저장 용량: 개발용 100MB → 상업용 무제한
- 데이터 보관: 개발용 30일 → 상업용 무제한

**3. 라이선스 정보 표시**
- 헤더에 현재 라이선스 상태 표시
- 라이선스 타입별 색상 구분 (파란색/초록색)
- 만료일 표시 (상업용)
- 기관명 표시 (상업용)

**4. 항공편 관리**
- CSV/Excel 파일 업로드
- 항공편 데이터 검증 및 저장
- 날짜별 항공편 조회
- 개별 항공편 상세 정보 조회

**5. 유사호출 감시**
- AI 기반 콜사인 유사도 분석
- 유사도 레벨 분류 (LEVEL 5/4/3)
- 점수 범위별 상세 분류 (5-1, 5-2, 5-3, 4-1, 4-2, 4-3, 4-4, 4-5, 3-1)
- 공역(섹터) 겹침 분석
- 실시간 유사호출 감지

**6. 기간 분석**
- 날짜 범위별 통계 분석
- 유사호출 발생 추이 조회
- 겹침 시간 계산
- 트렌드 차트 표시

**7. 데이터 관리**
- 항공기 기종 프로필 CSV 임포트
- 대량 데이터 처리 (백그라운드)
- 진행 상황 실시간 추적
- 데이터 내보내기 (JSON, Excel)

**8. 사용자 인터페이스**
- 탭 기반 메뉴 (대시보드, 기간분석, 항공편, CSV관리, 항공기, 테스트)
- 모달 팝업으로 상세 정보 조회
- 실시간 상태 표시
- 반응형 레이아웃

#### 🔧 기술 스택

**백엔드**
- Flask 2.0+ (Python 웹 프레임워크)
- SQLite (데이터베이스)
- HMAC-SHA256 (암호화)
- ThreadPoolExecutor (병렬 처리)

**프론트엔드**
- HTML5 / CSS3 / Vanilla JavaScript
- Fetch API (REST 통신)
- CSS Flexbox (레이아웃)
- Font Awesome (아이콘)

**유틸리티**
- Pandas (데이터 처리)
- openpyxl (Excel 생성)
- logging (로깅)

#### 📄 문서

- README.md (프로젝트 개요)
- CONTRIBUTING.md (협력 가이드)
- doc/LICENSE.md (상업용 라이선스)
- doc/README-LICENSE.md (라이선스 사용자 가이드)
- doc/DEVELOPMENT/ARCHITECTURE.md (아키텍처)
- .gitignore (15개 카테고리 파일 제외)

#### 🗂️ 폴더 구조 정리

```
ROOT/
├── README.md ⭐ 새로 추가
├── CONTRIBUTING.md ⭐ 새로 추가
├── .gitignore ✅ 완성
│
├── doc/
│   ├── LICENSE.md ⭐ 이동
│   ├── README-LICENSE.md ⭐ 이동
│   ├── CHANGELOG.md ⭐ 새로 추가
│   ├── DEVELOPMENT/
│   │   ├── ARCHITECTURE.md ⭐ 새로 추가
│   │   └── API.md (예정)
│   ├── TROUBLESHOOTING/
│   │   └── UPLOAD_TROUBLESHOOTING.md ⭐ 이동
│   └── ARCHIVES/ (개발 과정 문서들)
│
├── backend/
│   ├── app.py (✅ 라이선스 검증 추가)
│   ├── license_api.py ⭐ 새로 추가
│   └── ...
│
├── frontend/
│   ├── index.html (✅ 라이선스 표시 추가)
│   ├── js/
│   │   ├── dashboard.js (✅ 라이선스 로드 함수 추가)
│   │   └── ...
│   └── ...
│
└── utils/
    ├── license_manager.py ⭐ 새로 추가
    └── ...
```

#### 🔐 API 엔드포인트 변경

**신규 라이선스 API**
- `GET /api/license/info` - 라이선스 정보
- `GET /api/license/limits` - 기능 제한
- `GET /api/license/status` - 상세 상태

**기존 API 강화**
- `POST /api/upload/flights` - 항공편 수 제한 검증 추가
- `POST /api/aircraft/import/csv` - 상업용 라이선스만 허용
- `GET /api/export/json` - 내보내기 수 제한 검증 추가
- `GET /api/export/flights/excel` - 내보내기 수 제한 검증 추가

#### 🐛 버그 수정

- 단일 항공편 모달이 탭 전환 시 남아있던 문제 수정
- 테이블 높이 최적화로 공간 활용 개선
- 유사도 점수 범위 오류 수정 (5-4 → 4-5 재분류)
- CSS 클래스 계층 구조 정리

#### 📈 성능 개선

- 메모리 캐싱으로 항공편 조회 속도 2배 향상
- 백그라운드 처리로 UI 응답성 개선
- 테이블 높이 flex 최적화로 레이아웃 안정성 개선

#### ✅ 테스트

- 라이선스 검증 테스트 추가
- API 응답 형식 검증
- 파일 업로드 제한 테스트
- 데이터베이스 스키마 검증

---

## [0.9.0] - 2025-12-26 (Beta)

### 개발 진행 중 기능들

#### ✨ 추가된 기능
- 항공편 업로드 기능
- 유사호출 감지 알고리즘
- 기간 분석 탭
- 항공기 기종 관리
- 데이터 내보내기

#### 🐛 알려진 버그
- 라이선스 시스템 미완성
- 일부 UI 레이아웃 문제
- 유사도 레벨 분류 혼동

#### 📋 미완성 사항
- 라이선스 기능 제한
- 프론트엔드 라이선스 표시
- 상세한 문서화

---

## 🔜 향후 계획 (Roadmap)

### [1.1.0] - 예정

- [ ] PostgreSQL 지원
- [ ] 사용자 계정 관리
- [ ] 권한 기반 접근 제어 (RBAC)
- [ ] API 토큰 인증
- [ ] 감사 로그 (Audit Log)
- [ ] 데이터 암호화

### [1.2.0] - 예정

- [ ] 실시간 알림 (WebSocket)
- [ ] 모바일 앱 API
- [ ] 클라우드 배포 지원
- [ ] 백업/복구 기능
- [ ] 통계 다운로드

### [2.0.0] - 계획 중

- [ ] 머신러닝 기반 유사도 분석
- [ ] 다국어 지원
- [ ] 플러그인 시스템
- [ ] 고급 권한 관리
- [ ] 클러스터링 지원

---

## 📊 변경 통계

| 구분 | 수량 |
|------|------|
| 신규 기능 | 8+ |
| 버그 수정 | 5+ |
| 문서 추가 | 5+ |
| 코드 라인 | 2,000+ |
| API 엔드포인트 | 3 (라이선스) |
| 테스트 추가 | 10+ |

---

## 📝 기여자

첫 번째 릴리스에 기여해주신 분들:
- Contributor 1
- Contributor 2
- (협력자 추가 예정)

---

## 🔗 참고

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Releases](https://github.com/YOUR_USERNAME/Airspace-Sim-Station/releases)

---

**마지막 업데이트**: 2025-12-27

