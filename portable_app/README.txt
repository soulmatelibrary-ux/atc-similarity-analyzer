========================================
  유사호출 감시 시뮬레이션 시스템 (Similarity Detector)
  포터블 앱 버전
========================================

📋 개요
--------
이 프로그램은 항공편 데이터를 분석하여 유사한 항공 경로를 감지하고,
섹터별 겹침, 충돌 위험도 등을 시각화하는 시스템입니다.

패쇄망 환경에서도 인터넷 연결 없이 사용할 수 있습니다.


🚀 설치 방법 (처음 한 번만!)
----------------------------

1단계: Python 임베디드 버전 다운로드
   - 웹 브라우저에서 다음 링크로 이동:
     https://www.python.org/downloads/

   - "Windows embeddable package" 찾아서 다운로드
     (예: python-3.12.0-embed-amd64.zip 또는 python-3.13.0-embed-amd64.zip)

   - 시스템 사양에 맞춰 선택:
     * 64-bit PC: python-X.X.X-embed-amd64.zip
     * 32-bit PC: python-X.X.X-embed-win32.zip

2단계: Python 압축 해제
   - 다운로드한 zip 파일을 이 폴더에 압축 해제

3단계: 폴더 이름 변경
   - 압축 해제된 폴더 이름을 "python-embedded"로 변경

   예)
   python-3.12.0-embed-amd64 → python-embedded


4단계: setup.bat 실행
   - 이 폴더에서 setup.bat 파일을 더블 클릭
   - 또는 명령 프롬프트에서 실행:
     setup.bat

   - 검은 창이 나타나서 자동으로 설정을 진행합니다
   - "설정 완료!" 메시지가 나올 때까지 기다리세요


▶️ 실행 방법 (설치 후 매번)
---------------------------

1. run.bat 파일을 더블 클릭
   또는 명령 프롬프트에서:
     run.bat

2. 검은 창이 나타나고 서버가 시작됩니다

3. 웹 브라우저가 자동으로 열립니다
   (자동으로 안 열리면 주소창에 다음 입력: http://localhost:8888)

4. 대시보드에서 다음 기능 사용 가능:
   - 파일 업로드 (CSV 형식)
   - 유사호출 감지
   - 통계 및 분석
   - 데이터 내보내기


📁 폴더 구조
----------
similarity-detector-portable/
  ├── setup.bat              ← 처음 한 번 실행 (초기 설정)
  ├── run.bat                ← 매번 실행 (서버 시작)
  ├── stop.bat               ← 선택사항 (서버 종료)
  ├── README.txt             ← 이 파일
  ├── requirements.txt       ← Python 패키지 목록
  │
  ├── python-embedded/       ← Python 설치 위치 (직접 생성)
  ├── backend/               ← Flask 백엔드
  ├── frontend/              ← 웹 인터페이스
  ├── database/              ← 데이터베이스 관리
  ├── core/                  ← 핵심 로직
  ├── data/                  ← 데이터 저장
  └── utils/                 ← 유틸리티


📊 입력 파일 형식 (CSV)
---------------------
다음 열이 포함된 CSV 파일이 필요합니다:

필수 열:
  - CALLSIGN: 항공편 호출부호 (예: CES5044)
  - DEPT_AIRPORT_CD: 출발지 공항 코드 (예: ICN)
  - DEST_AIRPORT_CD: 도착지 공항 코드 (예: PUS)
  - AIRCRAFT_TYPE: 항공기 유형 (예: B789)
  - SPD: 속도 (예: 450)
  - ALT: 고도 (예: 350)
  - ENR: 비행 경로 (예: JEJU PUSAN)
  - EOBD: 비행 날짜 (예: 2025-12-20)
  - EOBT: 출발 시간 (예: 10:30)

예시 데이터:
  CALLSIGN,DEPT_AIRPORT_CD,DEST_AIRPORT_CD,AIRCRAFT_TYPE,SPD,ALT,ENR,EOBD,EOBT
  CES5044,ICN,PUS,B789,450,350,JEJU PUSAN,2025-12-20,10:30
  CES5053,ICN,PUS,B789,450,350,JEJU PUSAN,2025-12-20,10:35


🔧 포트 설정
-----------
기본 포트: 8888

다른 포트를 사용하려면 run.bat을 수정하세요:
  "--port=8888" → "--port=9999"


❓ 자주 묻는 질문
---------------

Q1. Python을 어디서 다운로드하나요?
A: https://www.python.org/downloads/
   "Windows embeddable package" 선택

Q2. setup.bat 실행 중 오류가 발생했어요
A: 다음을 확인하세요:
   - python-embedded 폴더가 올바르게 생성되었는지
   - 폴더 이름이 정확히 "python-embedded"인지
   - 인터넷 연결 상태 (첫 설치 시에만 필요)

Q3. 브라우저가 자동으로 열리지 않아요
A: 주소창에 직접 입력하세요: http://localhost:8888

Q4. 다른 PC에서도 사용할 수 있나요?
A: 네! 이 entire 폴더를 USB나 다른 위치에 복사하면 됩니다.
   같은 Windows PC라면 python-embedded는 그대로 사용 가능합니다.

Q5. 포트 8888이 이미 사용 중이라고 나와요
A: run.bat을 텍스트 에디터로 열어서 다음 줄을 수정하세요:
   --port=8888 → --port=9999


📞 지원
-------
문제가 발생하면 다음을 확인하세요:
1. README.txt (이 파일)
2. 브라우저 개발자도구 콘솔 (F12)
3. 명령 프롬프트 창의 오류 메시지


✅ 체크리스트
-----------
설치 전에 확인:
  ☐ Windows 7 이상 사용 중
  ☐ 디스크 여유공간 1GB 이상
  ☐ Python 임베디드 버전 다운로드 완료
  ☐ setup.bat 실행 완료

실행 전에 확인:
  ☐ python-embedded 폴더 존재
  ☐ requirements.txt 파일 존재
  ☐ 포트 8888 사용 가능


========================================
  버전: 1.0
  마지막 업데이트: 2025-12-20
========================================
