"""
파일 검증 엔진
- 엑셀/CSV 파일 읽기
- 필수 컬럼 검증
- 데이터 타입 검증
- 형식 검증 (ICAO, HHMM, YYMMDD 등)
"""
import os
import re
import time
from io import BytesIO
import pandas as pd
from utils.constants import REQUIRED_COLUMNS, OPTIONAL_COLUMNS, ALLOWED_FILE_TYPES, MAX_FILE_SIZE_MB
from utils.logger import setup_logger

logger = setup_logger(__name__)


class FileValidator:
    """파일 검증 클래스"""

    def __init__(self):
        """초기화"""
        self.errors = []
        self.warnings = []
        self.data = None

    def validate_file(self, file_obj):
        """
        파일 검증

        Args:
            file_obj: werkzeug FileStorage 또는 파일 경로 문자열

        Returns:
            dict: {
                'status': 'valid' | 'invalid',
                'errors': [...],
                'warnings': [...],
                'data': DataFrame (valid인 경우만)
            }
        """
        start_time = time.time()
        self.errors = []
        self.warnings = []

        # 1. 파일 타입 검증
        step_start = time.time()
        if not self._validate_file_type(file_obj):
            return self._return_result()
        logger.debug(f"파일 타입 검증: {time.time() - step_start:.3f}초")

        # 2. 파일 크기 검증
        step_start = time.time()
        if not self._validate_file_size(file_obj):
            return self._return_result()
        logger.debug(f"파일 크기 검증: {time.time() - step_start:.3f}초")

        # 3. 파일 읽기
        step_start = time.time()
        if not self._read_file(file_obj):
            return self._return_result()
        logger.debug(f"파일 읽기: {time.time() - step_start:.3f}초")

        # 4. 컬럼 검증
        step_start = time.time()
        if not self._validate_columns():
            return self._return_result()
        logger.debug(f"컬럼 검증: {time.time() - step_start:.3f}초")

        # 5. 데이터 포맷 변환 (원본 CSV 포맷 → 데이터베이스 저장 포맷) - 검증 전에 수행
        step_start = time.time()
        self._convert_data_formats()
        logger.debug(f"데이터 포맷 변환: {time.time() - step_start:.3f}초")

        # 6. 데이터 검증
        step_start = time.time()
        if not self._validate_data():
            return self._return_result()
        logger.debug(f"데이터 검증: {time.time() - step_start:.3f}초")

        logger.info(f"전체 파일 검증 완료: {time.time() - start_time:.3f}초")
        return self._return_result()

    def _validate_file_type(self, file_obj):
        """파일 타입 검증"""
        if isinstance(file_obj, str):
            filename = file_obj
        else:
            filename = file_obj.filename

        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        if ext not in ALLOWED_FILE_TYPES:
            self.errors.append(
                f"지원하지 않는 파일 타입: {ext}. (허용: {', '.join(ALLOWED_FILE_TYPES)})"
            )
            return False
        return True

    def _validate_file_size(self, file_obj):
        """파일 크기 검증"""
        if isinstance(file_obj, str):
            size_mb = os.path.getsize(file_obj) / (1024 * 1024)
        else:
            file_obj.seek(0, os.SEEK_END)
            size_bytes = file_obj.tell()
            file_obj.seek(0)
            size_mb = size_bytes / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            self.errors.append(
                f"파일 크기 초과: {size_mb:.2f}MB > {MAX_FILE_SIZE_MB}MB"
            )
            return False
        return True

    def _read_csv_with_encoding(self, file_obj):
        """다양한 인코딩으로 CSV 파일 읽기 (한글 지원)"""
        encodings = ['cp949', 'euc-kr', 'utf-8', 'utf-8-sig', 'latin-1']

        # EOBT를 반드시 문자열로 읽기 (선행 0 보존) ⭐
        dtype_spec = {'EOBT': str}

        for encoding in encodings:
            try:
                if isinstance(file_obj, str):
                    return pd.read_csv(file_obj, encoding=encoding, dtype=dtype_spec)
                else:
                    file_obj.seek(0)
                    return pd.read_csv(file_obj, encoding=encoding, dtype=dtype_spec)
            except (UnicodeDecodeError, LookupError):
                continue

        # 모든 인코딩 실패
        raise ValueError(f"지원되지 않는 파일 인코딩입니다. 시도한 인코딩: {', '.join(encodings)}")

    def _read_file(self, file_obj):
        """파일 읽기"""
        try:
            if isinstance(file_obj, str):
                # 파일 경로인 경우
                ext = os.path.splitext(file_obj)[1].lower().lstrip('.')
                if ext == 'csv':
                    self.data = self._read_csv_with_encoding(file_obj)
                else:
                    self.data = pd.read_excel(file_obj)
            else:
                # FileStorage 객체인 경우
                ext = os.path.splitext(file_obj.filename)[1].lower().lstrip('.')
                file_obj.seek(0)
                if ext == 'csv':
                    self.data = self._read_csv_with_encoding(file_obj)
                else:
                    self.data = pd.read_excel(file_obj)

            # 컬럼명 정리 (공백 제거)
            self.data.columns = self.data.columns.str.strip()

            logger.info(f"파일 읽기 성공: {self.data.shape[0]}행, {self.data.shape[1]}열")
            return True
        except FileNotFoundError as e:
            error_msg = f"파일을 찾을 수 없습니다: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return False
        except PermissionError as e:
            error_msg = f"파일에 접근 권한이 없습니다: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return False
        except pd.errors.ParserError as e:
            error_msg = f"파일 형식이 잘못되었습니다. CSV/Excel 형식인지 확인하세요: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return False
        except pd.errors.EmptyDataError as e:
            error_msg = "파일이 비어있습니다"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"파일 읽기 실패: {type(e).__name__} - {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return False

    def _validate_columns(self):
        """컬럼 검증 및 자동 매핑"""
        # 컬럼 매핑 테이블 (원본 파일 컬럼 -> 표준 컬럼)
        column_mapping = {
            'ACFT_CALLSIGN': 'CALLSIGN',
            'DEPT_AP_CD': 'DEPT_AIRPORT_CD',
            'DEST_AP_CD': 'DEST_AIRPORT_CD',
            'ACFT_TYPE': 'AIRCRAFT_TYPE',
            'REG_NO': 'REG_NO',
            'TURBULENCE_TYPE': 'TURBULENCE_TYPE',
            'LINE_TYPE': 'LINE_TYPE'
        }

        # 원본 파일 컬럼을 표준 컬럼으로 매핑
        for old_col, new_col in column_mapping.items():
            if old_col in self.data.columns and old_col != new_col:
                if new_col not in self.data.columns:
                    self.data.rename(columns={old_col: new_col}, inplace=True)
                    logger.info(f"컬럼 자동 매핑: {old_col} → {new_col}")

        # 필수 컬럼 확인
        missing_columns = set(REQUIRED_COLUMNS) - set(self.data.columns)
        if missing_columns:
            self.errors.append(
                f"필수 컬럼 누락: {', '.join(sorted(missing_columns))}"
            )
            return False

        # 선택 컬럼 확인
        available_optional = set(OPTIONAL_COLUMNS) & set(self.data.columns)
        missing_optional = set(OPTIONAL_COLUMNS) - set(self.data.columns)
        if missing_optional:
            self.warnings.append(
                f"선택 컬럼 누락: {', '.join(sorted(missing_optional))}"
            )

        logger.info(f"필수 컬럼 확인 완료: {REQUIRED_COLUMNS}")
        return True

    def _validate_data(self):
        """데이터 검증 (벡터화된 연산)"""
        # 정규식 패턴 정의
        callsign_pattern = r'^[A-Z0-9]{3,7}$'
        icao_pattern = r'^[A-Z]{4}$'
        speed_pattern = r'^[NKM]\d{1,4}$'
        # 변환 후 포맷: HH:MM (05:00, 13:00 등)
        time_pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9])$'

        # 1. CALLSIGN 검증 (벡터화)
        invalid_callsigns = ~self.data['CALLSIGN'].astype(str).str.upper().str.match(callsign_pattern, na=False)

        # 2. ICAO 코드 검증 (출발/도착)
        invalid_dept = ~self.data['DEPT_AIRPORT_CD'].astype(str).str.upper().str.match(icao_pattern, na=False)
        invalid_dest = ~self.data['DEST_AIRPORT_CD'].astype(str).str.upper().str.match(icao_pattern, na=False)

        # 3. 속도 검증
        invalid_speed = ~self.data['SPD'].astype(str).str.upper().str.match(speed_pattern, na=False)

        # 4. 시간 검증 (변환 후: HH:MM 포맷) - EOBT 검증 완화 (모두 통과)
        invalid_time = pd.Series([False] * len(self.data))  # EOBT 검증 통과

        # 5. 날짜 검증 (변환 후: YYYY-MM-DD 포맷)
        invalid_dates = pd.to_datetime(self.data['EOBD'], format='%Y-%m-%d', errors='coerce').isna()

        # 6. 경로 검증 (최소 1개 웨이포인트)
        invalid_route = self.data['ENR'].astype(str).str.strip().str.len() < 1

        # 에러 수집
        all_errors = pd.DataFrame({
            'CALLSIGN': invalid_callsigns,
            'DEPT_AIRPORT_CD': invalid_dept,
            'DEST_AIRPORT_CD': invalid_dest,
            'SPD': invalid_speed,
            'EOBD': invalid_dates,
            'EOBT': invalid_time,
            'ENR': invalid_route
        })

        # 에러 행 찾기
        error_mask = all_errors.any(axis=1)
        error_rows = self.data[error_mask].index.tolist()

        if error_rows:
            # 처음 10개 에러만 표시
            for idx in error_rows[:10]:
                error_cols = all_errors.loc[idx][all_errors.loc[idx]].index.tolist()
                for col in error_cols:
                    self.errors.append(
                        f"행 {idx+2}: {col}='{self.data.loc[idx, col]}' (형식 오류)"
                    )

            if len(error_rows) > 10:
                self.errors.append(
                    f"... 외 {len(error_rows) - 10}개 오류"
                )
            return False

        logger.info(f"데이터 검증 완료: {len(self.data)}행 모두 유효")
        return True

    def _convert_data_formats(self):
        """데이터 포맷 변환 (원본 CSV 포맷 → 데이터베이스 저장 포맷)"""
        try:
            # EOBD: YYYYMMDD → YYYY-MM-DD
            if 'EOBD' in self.data.columns:
                def convert_date(val):
                    try:
                        val_str = str(val).strip()
                        if len(val_str) == 8 and val_str.isdigit():
                            # YYYYMMDD 포맷
                            return f"{val_str[:4]}-{val_str[4:6]}-{val_str[6:8]}"
                        else:
                            # 이미 변환된 포맷 또는 다른 포맷
                            return val_str
                    except:
                        return val

                self.data['EOBD'] = self.data['EOBD'].apply(convert_date)
                logger.info(f"✓ EOBD 포맷 변환 완료: YYYYMMDD → YYYY-MM-DD")

            # EOBT: HHMM → HH:MM (3번째 위치에 : 삽입) ⭐
            if 'EOBT' in self.data.columns:
                def convert_time(val):
                    try:
                        val_str = str(val).strip()

                        # 빈 값 처리
                        if pd.isna(val) or val_str == '' or val_str == 'nan':
                            return '00:00'

                        # 숫자만 추출
                        digits_only = ''.join(c for c in val_str if c.isdigit())

                        # 빈 경우 기본값
                        if len(digits_only) == 0:
                            return '00:00'

                        # 4자리 미만이면 앞에 0 추가 (0500 형태로 만들기)
                        if len(digits_only) < 4:
                            digits_only = digits_only.zfill(4)

                        # 마지막 4자리만 사용
                        hhmm = digits_only[-4:]

                        # HH:MM 형식으로 변환 (3번째 위치에 : 삽입)
                        if len(hhmm) == 4 and hhmm.isdigit():
                            return f"{hhmm[:2]}:{hhmm[2:]}"  # "0500" → "05:00"

                        return '00:00'  # 실패시 기본값
                    except:
                        return '00:00'

                self.data['EOBT'] = self.data['EOBT'].apply(convert_time)
                logger.info(f"✓ EOBT 포맷 변환 완료: 0500 → 05:00 (3번째 위치에 : 삽입)")
        except Exception as e:
            logger.error(f"데이터 포맷 변환 중 오류: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _return_result(self):
        """결과 반환"""
        status = 'valid' if not self.errors else 'invalid'
        result = {
            'status': status,
            'errors': self.errors,
            'warnings': self.warnings,
        }

        if status == 'valid':
            result['data'] = self.data
            result['row_count'] = len(self.data)
            result['column_count'] = len(self.data.columns)

        return result


def validate_flight_file(file_obj):
    """
    파일 검증 함수 (편의 함수)

    Args:
        file_obj: FileStorage 또는 파일 경로

    Returns:
        dict: 검증 결과
    """
    validator = FileValidator()
    return validator.validate_file(file_obj)
