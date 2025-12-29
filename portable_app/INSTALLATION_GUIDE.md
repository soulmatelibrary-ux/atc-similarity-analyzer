# 유사호출 감시 시뮬레이션 시스템 - 설치 및 실행 가이드

## 📋 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [설치 단계](#설치-단계)
3. [실행 방법](#실행-방법)
4. [테스트](#테스트)
5. [트러블슈팅](#트러블슈팅)

---

## 🖥️ 시스템 요구사항

### **최소 사양**
```
OS:           Windows 10+, macOS 10.14+, Ubuntu 18.04+
Python:       3.7 이상
메모리:       2GB 이상
저장공간:     1GB (database + logs)
포트:         8000, 8888 (사용 가능)
브라우저:     Chrome, Firefox, Safari, Edge (최신)
```

### **추천 사양**
```
OS:           Windows 11, macOS 13+, Ubuntu 22.04+
Python:       3.10 이상
메모리:       8GB 이상
저장공간:     SSD 2GB 이상
GPU:          선택사항 (처리 시간 개선)
```

---

## 📦 설치 단계

### **Step 1: Python 설치**

#### **Windows**
```bash
# 1. 공식 웹사이트에서 다운로드
https://www.python.org/downloads/

# 2. 설치 시 "Add Python to PATH" 체크 필수
# 3. 설치 경로: C:\Python310 (기본값)

# 4. 설치 확인
python --version
pip --version
```

#### **macOS**
```bash
# 1. Homebrew로 설치 (권장)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Python 설치
brew install python@3.10

# 3. 설치 확인
python3 --version
pip3 --version
```

#### **Linux (Ubuntu)**
```bash
# 1. 패키지 매니저로 설치
sudo apt update
sudo apt install python3.10 python3-pip

# 2. 설치 확인
python3 --version
pip3 --version
```

---

### **Step 2: 프로젝트 준비**

#### **프로젝트 폴더 생성**
```bash
# 프로젝트 디렉토리로 이동
cd /Users/sein/Desktop/iccs/similarity_detector

# 또는 새로 생성하는 경우
mkdir -p /path/to/similarity_detector
cd /path/to/similarity_detector
```

#### **파일 구조 확인**
```
similarity_detector/
├── backend/
│   ├── app.py
│   ├── __init__.py
│   └── __pycache__/
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js
│       ├── ui.js
│       └── charts.js
├── core/
│   ├── flight_processor.py
│   ├── flight_service.py
│   ├── similarity_engine.py
│   └── route_converter.py
├── database/
│   ├── db_manager.py
│   └── similarity_detector.db
├── utils/
│   ├── constants.py
│   ├── file_validator.py
│   ├── logger.py
│   └── sector_parser.py
├── t_flightplan1.csv        ← 샘플 데이터
└── USER_GUIDE.md            ← 사용자 가이드
```

---

### **Step 3: Python 가상 환경 설정** (권장)

#### **가상 환경 생성**
```bash
# Windows
python -m venv venv

# macOS / Linux
python3 -m venv venv
```

#### **가상 환경 활성화**
```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 확인 (프롬프트에 (venv) 표시)
(venv) $
```

---

### **Step 4: 필수 라이브러리 설치**

#### **requirements.txt 생성** (필요시)

프로젝트 루트에 다음 파일 생성:

```bash
# requirements.txt
Flask==2.3.2
flask-cors==4.0.0
pandas==2.0.3
numpy==1.24.3
openpyxl==3.1.2
Werkzeug==2.3.6
```

#### **라이브러리 설치**

```bash
# Windows
pip install -r requirements.txt

# 또는 개별 설치
pip install Flask flask-cors pandas numpy openpyxl

# macOS / Linux
pip3 install Flask flask-cors pandas numpy openpyxl
```

#### **설치 확인**

```bash
python -c "import pandas; import flask; print('OK')"
# 또는
python -c "from core.flight_processor import *; print('OK')"
```

---

### **Step 5: 데이터베이스 초기화**

```bash
# 백엔드 실행 시 자동으로 DB 생성됨
# 또는 수동으로:

python
>>> from database.db_manager import DatabaseManager
>>> db = DatabaseManager()
>>> print("Database initialized")
>>> exit()
```

---

## 🚀 실행 방법

### **터미널 1: 백엔드 서버 실행**

```bash
# 1. 프로젝트 디렉토리로 이동
cd similarity_detector

# 2. 가상 환경 활성화 (선택사항)
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# 3. Flask 서버 실행
python backend/app.py

# 성공 메시지
# * Running on http://127.0.0.1:8888
# * Debug mode: on

# Flask 로그 확인
# 1. 서버가 http://127.0.0.1:8888 에서 실행 중
# 2. API 요청이 들어올 때마다 로그 출력
```

### **터미널 2: 프론트엔드 서버 실행**

```bash
# 1. 새 터미널 열기 (첫 번째 백엔드 실행 상태 유지)

# 2. frontend 디렉토리로 이동
cd similarity_detector/frontend

# 3. 웹 서버 실행
python -m http.server 8000

# 성공 메시지
# Serving HTTP on 0.0.0.0 port 8000
# (http://localhost:8000/ or http://127.0.0.1:8000/)
```

### **브라우저에서 접속**

```
http://localhost:8000
또는
http://127.0.0.1:8000
```

---

## 🧪 테스트

### **시스템 상태 확인**

#### **1. 백엔드 API 테스트**

```bash
# 터미널에서 테스트 (백엔드 실행 중)
curl http://localhost:8888/api/health

# 응답 예시
{
  "status": "ok",
  "message": "System healthy"
}
```

#### **2. 통계 조회 테스트**

```bash
curl http://localhost:8888/api/statistics/summary

# 응답 예시
{
  "status": "success",
  "data": {
    "total_flights": 0,
    "total_similarities": 0,
    ...
  }
}
```

#### **3. 프론트엔드 테스트**

```
1. 브라우저에서 http://localhost:8000 접속
2. 좌측 사이드바 5개 섹션 표시 확인
3. "데이터 로딩 중..." 메시지 확인
4. 새로고침 후 업데이트 확인
```

### **샘플 데이터로 기능 테스트**

#### **1. CSV 업로드 테스트**

```
Step 1: 프론트엔드 브라우저에서
  └─ "1. 유사호출 잠지 시뮬레이션" 섹션

Step 2: 파일 선택
  ├─ 파일: t_flightplan1.csv
  └─ 또는 드래그&드롭

Step 3: "적용" 버튼 클릭
  ├─ 프로그레스 바 표시
  └─ "XXX개 유사호출 감지 완료" 메시지 확인

Step 4: 결과 확인
  ├─ 메인 대시보드 업데이트
  ├─ 통계 카드 표시
  └─ 테이블에 데이터 표시
```

#### **2. 날짜 조회 테스트**

```
Step 1: "2. 단순 결과 조회" 섹션
Step 2: 날짜 선택 (예: 2025-12-20)
Step 3: "조회" 버튼 클릭
Step 4: 해당 날짜의 항공편 표시 확인
```

#### **3. 통계 확인 테스트**

```
Step 1: 대시보드 우측
Step 2: "4. 위험도 분포" 확인
  └─ level-HIGH, level-MEDIUM, level-LOW 표시

Step 3: "5. 항공사별 유사호출" 확인
  └─ Top 5 항공사 표시
```

### **성능 테스트**

#### **처리 시간 측정**

```bash
# CSV 파일 처리 시간 기록
1. 파일 선택 전: 시간 기록
2. "적용" 버튼 클릭
3. "완료" 메시지 표시: 시간 기록
4. 소요 시간 = 완료 시간 - 시작 시간

예상 시간:
- 100개: 2~3초
- 1,000개: 10~20초
- 1,500개: 30~60초
```

#### **메모리 사용량 확인**

```bash
# Windows - 작업 관리자에서 확인
# macOS - Activity Monitor에서 확인
# Linux - top 또는 htop 명령어로 확인

# 정상 범위
- 백엔드 프로세스: 200~500MB
- 프론트엔드: 50~100MB
- 총 메모리 사용: 500MB 이상
```

---

## 🔧 트러블슈팅

### **백엔드 실행 에러**

#### **Error: "Port 8888 already in use"**

```bash
# 원인: 다른 프로그램이 포트 8888 사용 중

# 해결 방법 1: 포트 확인 (Windows)
netstat -ano | findstr :8888

# 해결 방법 2: 포트 확인 (macOS/Linux)
lsof -i :8888

# 해결 방법 3: 프로세스 강제 종료 (Windows)
taskkill /PID <PID> /F

# 해결 방법 4: 프로세스 강제 종료 (macOS/Linux)
kill -9 <PID>

# 해결 방법 5: 다른 포트로 실행
# backend/app.py 수정:
# app.run(port=8889)  # 8888 → 8889
```

#### **Error: "ModuleNotFoundError: No module named 'pandas'"**

```bash
# 원인: 필요한 라이브러리 미설치

# 해결 방법 1: 라이브러리 설치
pip install pandas numpy flask flask-cors openpyxl

# 해결 방법 2: requirements.txt로 설치
pip install -r requirements.txt

# 해결 방법 3: 가상 환경 재활성화
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
```

#### **Error: "ImportError: cannot import name 'db_manager'"**

```bash
# 원인: Python path 설정 문제

# 해결 방법: 프로젝트 루트에서 실행
cd similarity_detector
python backend/app.py

# 아니면 PYTHONPATH 설정
export PYTHONPATH=/path/to/similarity_detector:$PYTHONPATH
```

#### **Error: "Database locked" or "database.db is corrupted"**

```bash
# 해결 방법: DB 파일 제거 후 재생성
cd similarity_detector/database

# DB 파일 삭제
rm similarity_detector.db
# 또는 (Windows)
del similarity_detector.db

# 시스템 재실행하면 자동으로 새 DB 생성됨
```

---

### **프론트엔드 실행 에러**

#### **Error: "Port 8000 already in use"**

```bash
# 다른 포트로 실행
python -m http.server 8001

# 브라우저에서 접속
http://localhost:8001
```

#### **Error: "Connection refused" or "Failed to connect to server"**

```bash
# 원인: 백엔드 서버가 실행되지 않음

# 확인 방법:
1. 백엔드 터미널 확인 (http://127.0.0.1:8888 실행 중?)
2. 포트 8888 사용 가능?
3. 방화벽이 포트 차단하지 않음?

# 해결 방법:
1. 백엔드 서버 재실행
2. 포트 변경
3. 방화벽 규칙 확인
```

#### **Error: "API request failed"**

```bash
# 브라우저 개발자 도구 열기 (F12)
1. Network 탭 확인
2. 실패한 요청 클릭
3. Status 코드 확인
   - 404: API 엔드포인트 없음
   - 500: 백엔드 오류
   - 503: 백엔드 서버 다운

# 해결: 백엔드 로그 확인 및 재실행
```

---

### **데이터 처리 에러**

#### **Error: "File format not supported"**

```bash
# 확인 사항:
1. 파일 확장자: .csv 맞는가?
2. 인코딩: CP949 또는 UTF-8인가?
3. 파일 형식: Excel → CSV로 저장했는가?

# 해결 방법:
# Excel에서 다시 저장
1. 파일 → 다른 이름으로 저장
2. 파일 형식: CSV (쉼표로 구분)
3. 인코딩: UTF-8 선택
4. 저장
```

#### **Error: "Invalid column name"**

```bash
# 원인: 필수 컬럼이 없거나 이름이 다름

# 필수 컬럼 확인:
- CALLSIGN (대소문자 정확히)
- DEPT_AIRPORT_CD
- DEST_AIRPORT_CD
- AIRCRAFT_TYPE
- SPD, ALT, ENR
- EOBD, EOBT

# 해결: CSV 헤더 수정 후 재업로드
```

#### **Error: "Processing timeout"**

```bash
# 원인: 파일이 너무 크거나 시스템 과부하

# 해결 방법:
1. 파일을 더 작은 단위로 분할
   - 5,000개 단위로 나누기
   - 각각 CSV로 저장
   - 순서대로 업로드

2. 시스템 상태 확인
   - 다른 프로그램 종료
   - 메모리 확인
   - 디스크 용량 확인 (1GB 이상 필요)

3. 타임아웃 시간 증가
   # backend/app.py 수정:
   # timeout_seconds=2700 → 더 큰 값으로 변경
```

---

### **성능 관련 이슈**

#### **시스템이 느림**

```bash
# 원인 진단:
1. CPU 사용률 확인 (Task Manager / Activity Monitor)
2. 메모리 사용률 확인
3. 디스크 I/O 확인

# 해결 방법:
1. 다른 프로그램 종료
2. 브라우저 캐시 삭제 (Ctrl+Shift+Delete)
3. DB 최적화
   # 명령어 (Python):
   python -c "from database.db_manager import DatabaseManager; \
              db = DatabaseManager(); db.optimize_database()"

4. 파일 크기 확인
   - 10,000개 이상인 경우 분할 처리
```

#### **메모리 누수**

```bash
# 증상: 시간이 지날수록 메모리 사용량 증가

# 해결 방법:
1. 주기적으로 시스템 재실행
   - 8시간마다 1회 권장

2. DB 청소
   # 오래된 데이터 삭제:
   - "3. 일자별 DB 초기화" 사용
   - 필요 없는 날짜 데이터 삭제

3. 브라우저 재실행
   - Chrome, Firefox 등 메모리 누수 가능
```

---

## 📝 로그 파일 확인

### **백엔드 로그**

```bash
# 위치: similarity_detector/backend/logs/
# 파일: app.log, similarity_engine.log 등

# 실시간 로그 확인:
tail -f backend/logs/app.log  # macOS/Linux
type backend\logs\app.log     # Windows (마지막 출력)
```

### **로그 레벨**

```
INFO:    정상 작동 메시지
WARNING: 경고 (처리 가능한 에러)
ERROR:   에러 (처리 중단)
DEBUG:   상세 디버깅 정보
```

### **에러 로그 분석**

```bash
# 에러 메시지 검색:
grep "ERROR" backend/logs/app.log

# 특정 시간 범위 로그:
grep "2025-12-20" backend/logs/app.log

# 에러 개수 세기:
grep -c "ERROR" backend/logs/app.log
```

---

## ✅ 체크리스트

### **초기 설정 완료 확인**

```
☐ Python 3.7+ 설치
☐ 필수 라이브러리 설치 (Flask, pandas, numpy, openpyxl)
☐ 프로젝트 파일 다운로드/준비
☐ 가상 환경 생성 (선택사항)
☐ 데이터베이스 초기화
☐ 백엔드 서버 실행 (포트 8888)
☐ 프론트엔드 서버 실행 (포트 8000)
☐ 브라우저에서 http://localhost:8000 접속 확인
☐ API 테스트 (curl 또는 브라우저)
☐ 샘플 CSV 파일 처리 테스트
☐ 결과 데이터 확인
```

### **운영 체크리스트**

```
☐ 일일 1회 데이터 백업 (DB 파일)
☐ 주 1회 로그 파일 검토
☐ 월 1회 성능 분석
☐ 필요시 데이터 정리 (old data 삭제)
☐ 보안 업데이트 확인
```

---

## 🆘 기술 지원

### **로그 정보 수집**

문제 발생 시 다음 정보 수집:

```
1. 시스템 정보:
   - OS 및 버전
   - Python 버전 (python --version)
   - 설치된 라이브러리 (pip list)

2. 에러 정보:
   - 정확한 에러 메시지
   - 에러 발생 시간
   - 수행한 작업

3. 로그 파일:
   - backend/logs/app.log (마지막 100줄)
   - 브라우저 콘솔 메시지 (F12)
   - 네트워크 에러 (F12 → Network)

4. 파일 정보:
   - CSV 파일 행 수
   - CSV 파일 인코딩
   - 파일 크기
```

---

**버전:** 1.0.0
**최종 업데이트:** 2025-12-20
**작성자:** 개발팀
