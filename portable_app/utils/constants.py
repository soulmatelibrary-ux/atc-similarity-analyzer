"""
상수 정의
"""

# 유사도 레벨 정의
SIMILARITY_LEVELS = {
    'LEVEL_2-1': {'risk': 'HIGH', 'score': 100, 'description': '같은 prefix + 시각적 유사'},
    'LEVEL_2-2': {'risk': 'MEDIUM', 'score': 75, 'description': '다른 prefix + 시각적 유사'},
    'LEVEL_3-1': {'risk': 'MEDIUM', 'score': 70, 'description': '마지막 2자리 동일'},
    'LEVEL_3-3': {'risk': 'LOW', 'score': 40, 'description': '연속된 숫자 블록 동일'},
    'LEVEL_3-4': {'risk': 'MEDIUM', 'score': 65, 'description': 'Prefix 동일 + 숫자 2자리 이상 같음'},
    'LEVEL_3-8': {'risk': 'HIGH', 'score': 90, 'description': 'Prefix 동일 + 숫자 3자리 연속 같음'},
    'LEVEL_3-5': {'risk': 'LOW', 'score': 35, 'description': 'Prefix 동일 + 숫자 부분 일치'},
    'LEVEL_3-6': {'risk': 'LOW', 'score': 30, 'description': '마지막 2자리 같음'},
    'LEVEL_3-7': {'risk': 'LOW', 'score': 25, 'description': '마지막 글자 동일'},
    'LEVEL_4-1': {'risk': 'HIGH', 'score': 85, 'description': '다른 prefix + 숫자 완전 동일'},
    'LEVEL_4-2': {'risk': 'MEDIUM', 'score': 60, 'description': 'Prefix 동일 + 4자리 중 3자리 같음'},
    'LEVEL_5-1': {'risk': 'LOW', 'score': 20, 'description': '같은 prefix + Leading Zero'},
    'LEVEL_5-2': {'risk': 'MEDIUM', 'score': 55, 'description': '다른 prefix + Leading Zero'},
}

# 위험도 색상 매핑
RISK_COLORS = {
    'HIGH': '#ff6b6b',
    'MEDIUM': '#ffd43b',
    'LOW': '#51cf66',
}

# 섹터 목록
SECTORS = ['JH', 'JN', 'KH', 'GH', 'ES1', 'ES2', 'SS', 'WH', 'WL', 'PH', 'GL', 'DG', 'HH', 'HL']

# 시간대 슬롯 (15분 단위)
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 15)]

# 파일 포맷
ALLOWED_FILE_TYPES = ['xlsx', 'xls', 'csv']
MAX_FILE_SIZE_MB = 50

# 필수 컬럼
REQUIRED_COLUMNS = ['CALLSIGN', 'DEPT_AIRPORT_CD', 'DEST_AIRPORT_CD', 'SPD', 'EOBD', 'EOBT', 'ENR']

# 선택 컬럼
OPTIONAL_COLUMNS = ['AIRCRAFT_TYPE', 'ALT', 'INFO_CN', 'EET']

# 기본 필터값
DEFAULT_FILTERS = {
    'min_coexist_minutes': 0,
    'max_coexist_minutes': None,
    'similarity_levels': ['LEVEL_2-1', 'LEVEL_2-2', 'LEVEL_3-1', 'LEVEL_3-8'],
    'risk_levels': ['HIGH', 'MEDIUM', 'LOW'],
    'sectors': None,
    'time_range': ['00:00', '23:59'],
}

# 충돌 위험 기준
SEPARATION_STANDARDS = {
    'min_horizontal_separation_km': 3.0,  # 최소 수평 분리 거리
    'min_vertical_separation_feet': 1000,  # 최소 수직 분리 거리
    'high_risk_threshold': 3.0,
    'medium_risk_threshold': 5.0,
}

# 데이터베이스
DATABASE_PATH = 'similarity_detector.db'
DATABASE_URL = 'sqlite:///similarity_detector.db'

# 로깅
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/app.log'

# 서버 포트 설정
API_PORT = 8888  # Flask 백엔드 포트
FRONTEND_PORT = 8000  # 프론트엔드 포트

# API 설정
API_BASE_URL = f'http://localhost:{API_PORT}'

# Debug Mode (environment variable로 제어)
import os
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# 애플리케이션
APP_NAME = '유사호출 감시 시뮬레이션 시스템'
APP_VERSION = '1.0.0'
