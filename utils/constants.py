# 유사도 레벨 정의 (v2.1) - 점수 범위 기반
SIMILARITY_LEVELS = {
    # LEVEL 5 (고위험 - Critical: 90~100점)
    "LEVEL_5-1": {
        'risk': "HIGH",
        'score_min': 97,
        'score_max': 100,
        'score_avg': 98,
        'description': "항공사 유사 + 숫자 동일 (Airline [전치/샌드위치] 유사 + 숫자 100% 동일)"
    },
    "LEVEL_5-2": {
        'risk': "HIGH",
        'score_min': 94,
        'score_max': 97,
        'score_avg': 95,
        'description': "동일 항공사 + Suffix 3 (같은 항공사 + 마지막 3자리 숫자 일치)"
    },
    "LEVEL_5-3": {
        'risk': "HIGH",
        'score_min': 91,
        'score_max': 94,
        'score_avg': 92,
        'description': "동일 항공사 + 시각 유사 (같은 항공사 + 숫자 전체가 시각적 혼동 패턴으로 구성)"
    },

    # LEVEL 4 (중위험 - Caution: 65~89점)
    "LEVEL_4-1": {
        'risk': "MEDIUM",
        'score_min': 85,
        'score_max': 89,
        'score_avg': 87,
        'description': "숫자 위치 바뀜 (숫자 구성은 같으나 순서가 하나만 바뀜)"
    },
    "LEVEL_4-2": {
        'risk': "MEDIUM",
        'score_min': 82,
        'score_max': 85,
        'score_avg': 83,
        'description': "양끝 일치 + 가운데 유사 (같은 항공사 + 첫/끝 숫자 동일 + 가운데 숫자가 시각적 유사)"
    },
    "LEVEL_4-3": {
        'risk': "MEDIUM",
        'score_min': 75,
        'score_max': 82,
        'score_avg': 78,
        'description': "한 자리 혼동 (숫자 한 자리만 다르되, 청각적/시각적 혼동 쌍)"
    },
    "LEVEL_4-4": {
        'risk': "MEDIUM",
        'score_min': 70,
        'score_max': 75,
        'score_avg': 72,
        'description': "항공사 유사 + 숫자 유사 (Airline 유사 + 숫자가 시각/청각적 혼동 패턴에 해당)"
    },
    "LEVEL_4-5": {
        'risk': "MEDIUM",
        'score_min': 65,
        'score_max': 72,
        'score_avg': 68,
        'description': "다른 항공사 + 숫자 동일 (항공사는 다르나 숫자 부분이 완전히 동일)"
    },

    # LEVEL 3 (저위험 - Notice: 50~64점)
    "LEVEL_3-1": {
        'risk': "LOW",
        'score_min': 50,
        'score_max': 64,
        'score_avg': 57,
        'description': "Leading Zero 차이 (수치적 값은 동일하나 표기만 다름)"
    }
}

# 시각적/청각적 혼동 패턴 정의 (사용자 지정 정밀 패턴)
CONFUSION_PAIRS = {
    'visual': [
        ('1', 'I', 'L'),
        ('0', 'O', '8'),
        ('5', 'S'),
        ('2', 'Z'),
        ('6', 'G')
    ],
    'auditory': [
        ('1', '9'),
        ('5', '9'),
        ('2', '3'),
        ('M', 'N'),
        ('S', 'F')
    ]
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
    'similarity_levels': ['LEVEL_5-1', 'LEVEL_5-2', 'LEVEL_5-3', 'LEVEL_4-1', 'LEVEL_4-2', 'LEVEL_4-3', 'LEVEL_4-4', 'LEVEL_4-5'],
    'risk_levels': ['HIGH', 'MEDIUM', 'LOW'],
    'sectors': None,
    'time_range': ['00:00', '23:59'],
}

# 충돌 위험 기준
SEPARATION_STANDARDS = {
    'min_horizontal_separation_km': 3.0,
    'min_vertical_separation_feet': 1000,
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
API_PORT = 8888
FRONTEND_PORT = 8000

# API 설정
API_BASE_URL = f'http://localhost:{API_PORT}'

# Debug Mode
import os
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# 애플리케이션
APP_NAME = '유사호출 감시 시뮬레이션 시스템'
APP_VERSION = '2.1.0'
