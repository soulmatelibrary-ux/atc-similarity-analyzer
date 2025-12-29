"""
라이선스 관리 시스템

개발용 (MIT): 무료
상업용: 유료 라이선스 키 필요

라이선스 검증 흐름:
1. 시작 시 라이선스 파일 확인
2. 라이선스 타입 확인 (development / commercial)
3. 상업용의 경우 라이선스 키 검증
4. 만료일 확인
5. 기능 제한 적용
"""

import os
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LicenseManager:
    """라이선스 관리 클래스"""

    # 라이선스 타입
    LICENSE_TYPE_DEVELOPMENT = "development"  # MIT 라이선스 (무료)
    LICENSE_TYPE_COMMERCIAL = "commercial"    # 상업 라이선스 (유료)

    # 라이선스 파일 경로
    LICENSE_FILE = ".license/license.json"
    LICENSE_CONFIG_FILE = ".license/config.json"

    # 기능 제한 (개발용)
    DEVELOPMENT_LIMITS = {
        'max_flights_per_upload': 100,  # 한 번에 100항공편까지만
        'max_storage_mb': 100,           # 100MB까지만
        'watermark': True,               # 워터마크 표시
        'export_limit': 50,              # 50개까지만 내보내기
        'data_retention_days': 30,       # 30일 데이터만 유지
    }

    # 기능 제한 없음 (상업용)
    COMMERCIAL_LIMITS = {
        'max_flights_per_upload': 999999,
        'max_storage_mb': 999999,
        'watermark': False,
        'export_limit': 999999,
        'data_retention_days': 9999,
    }

    def __init__(self):
        self.license_type = self.LICENSE_TYPE_DEVELOPMENT
        self.license_data = None
        self.is_valid = False
        self.message = ""
        self._load_license()

    def _load_license(self):
        """라이선스 파일 로드"""
        try:
            if os.path.exists(self.LICENSE_FILE):
                with open(self.LICENSE_FILE, 'r', encoding='utf-8') as f:
                    self.license_data = json.load(f)

                # 라이선스 타입 확인
                self.license_type = self.license_data.get('type', self.LICENSE_TYPE_DEVELOPMENT)

                # 상업용 라이선스 검증
                if self.license_type == self.LICENSE_TYPE_COMMERCIAL:
                    self.is_valid = self._validate_commercial_license()
                else:
                    self.is_valid = True
                    self.message = "Development License (MIT) - Free"
            else:
                # 라이선스 파일 없으면 개발용으로 기본 설정
                self.is_valid = True
                self.license_type = self.LICENSE_TYPE_DEVELOPMENT
                self.message = "Development License (MIT) - Free"
                logger.info("Using default development license")

        except Exception as e:
            logger.error(f"Failed to load license: {str(e)}")
            self.is_valid = False
            self.message = f"License Error: {str(e)}"

    def _validate_commercial_license(self) -> bool:
        """상업용 라이선스 검증"""
        try:
            if not self.license_data:
                self.message = "No license data found"
                return False

            # 필수 필드 확인
            required_fields = ['license_key', 'organization', 'expiry_date', 'signature']
            for field in required_fields:
                if field not in self.license_data:
                    self.message = f"Missing field: {field}"
                    return False

            # 만료일 확인
            expiry_date = datetime.fromisoformat(self.license_data['expiry_date'])
            if datetime.now() > expiry_date:
                self.message = f"License expired on {expiry_date.strftime('%Y-%m-%d')}"
                return False

            # 라이선스 키 검증 (HMAC 서명)
            if not self._verify_license_signature():
                self.message = "Invalid license signature"
                return False

            # 남은 일수 계산
            days_left = (expiry_date - datetime.now()).days
            self.message = f"Commercial License - Valid for {days_left} more days"

            # 30일 이내 만료 시 경고
            if days_left <= 30:
                logger.warning(f"License expires in {days_left} days!")

            return True

        except Exception as e:
            logger.error(f"License validation error: {str(e)}")
            self.message = f"Validation Error: {str(e)}"
            return False

    def _verify_license_signature(self) -> bool:
        """라이선스 서명 검증 (HMAC-SHA256)"""
        try:
            license_key = self.license_data.get('license_key')
            organization = self.license_data.get('organization')
            expiry_date = self.license_data.get('expiry_date')
            signature = self.license_data.get('signature')

            # 서명에 포함될 데이터
            data_to_sign = f"{license_key}:{organization}:{expiry_date}"

            # 마스터 키 (실제로는 환경변수에서 로드)
            master_key = os.getenv('LICENSE_MASTER_KEY', 'default-master-key-12345')

            # 서명 계산
            expected_signature = hmac.new(
                master_key.encode(),
                data_to_sign.encode(),
                hashlib.sha256
            ).hexdigest()

            # 서명 비교 (시간 공격 방지)
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False

    def get_limits(self) -> Dict:
        """현재 라이선스에 따른 기능 제한 반환"""
        if self.license_type == self.LICENSE_TYPE_COMMERCIAL:
            return self.COMMERCIAL_LIMITS.copy()
        else:
            return self.DEVELOPMENT_LIMITS.copy()

    def check_limit(self, limit_name: str, value: int) -> Tuple[bool, str]:
        """특정 제한 확인"""
        limits = self.get_limits()

        if limit_name not in limits:
            return True, "Unknown limit"

        max_value = limits[limit_name]
        if value > max_value:
            return False, f"Exceeded {limit_name}: {value} > {max_value}"

        return True, "OK"

    def is_development(self) -> bool:
        """개발용 라이선스 확인"""
        return self.license_type == self.LICENSE_TYPE_DEVELOPMENT

    def is_commercial(self) -> bool:
        """상업용 라이선스 확인"""
        return self.license_type == self.LICENSE_TYPE_COMMERCIAL

    def get_license_info(self) -> Dict:
        """라이선스 정보 조회"""
        info = {
            'type': self.license_type,
            'is_valid': self.is_valid,
            'message': self.message,
        }

        if self.license_data:
            info['organization'] = self.license_data.get('organization', 'Unknown')
            info['expiry_date'] = self.license_data.get('expiry_date', 'N/A')
            info['support_email'] = self.license_data.get('support_email', 'support@example.com')

        return info

    def generate_license_key(self, organization: str, days: int = 365) -> Dict:
        """
        라이선스 키 생성 (관리자용)

        Args:
            organization: 조직명
            days: 라이선스 유효 기간 (일)

        Returns:
            라이선스 데이터
        """
        license_key = hashlib.sha256(
            f"{organization}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:24].upper()

        expiry_date = datetime.now() + timedelta(days=days)

        # 서명 데이터
        data_to_sign = f"{license_key}:{organization}:{expiry_date.isoformat()}"
        master_key = os.getenv('LICENSE_MASTER_KEY', 'default-master-key-12345')
        signature = hmac.new(
            master_key.encode(),
            data_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()

        return {
            'type': self.LICENSE_TYPE_COMMERCIAL,
            'license_key': license_key,
            'organization': organization,
            'expiry_date': expiry_date.isoformat(),
            'signature': signature,
            'created_date': datetime.now().isoformat(),
            'support_email': f"support@callsign-detector.com",
        }

    def log_license_info(self):
        """라이선스 정보 로그"""
        info = self.get_license_info()
        logger.info(f"License Type: {info['type']}")
        logger.info(f"License Valid: {info['is_valid']}")
        logger.info(f"Message: {info['message']}")

        if 'organization' in info:
            logger.info(f"Organization: {info['organization']}")
            logger.info(f"Expiry Date: {info['expiry_date']}")


# 전역 라이선스 매니저 인스턴스
_license_manager = None


def get_license_manager() -> LicenseManager:
    """라이선스 매니저 인스턴스 반환"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def check_commercial_license(feature_name: str = None) -> Tuple[bool, str]:
    """상업용 라이선스 확인 (데코레이터용)"""
    manager = get_license_manager()

    if not manager.is_valid:
        return False, f"Invalid license: {manager.message}"

    if manager.is_development():
        return False, "This feature requires commercial license"

    return True, "OK"


# 데코레이터: 상업용 기능 보호
def commercial_only(func):
    """상업용 라이선스가 필요한 기능 표시"""
    def wrapper(*args, **kwargs):
        is_valid, message = check_commercial_license(func.__name__)
        if not is_valid:
            logger.warning(f"Attempted to use commercial feature without license: {func.__name__}")
            raise PermissionError(f"Commercial License Required: {message}")
        return func(*args, **kwargs)
    return wrapper
