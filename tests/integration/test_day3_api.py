#!/usr/bin/env python3
"""
Day 3 API 테스트 스크립트

새로 추가된 API 엔드포인트를 테스트합니다:
- /api/aircraft-profiles (CRUD)
- /api/flights/<id>/climb-comparison
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:8888"

class APITester:
    """API 테스트 클래스"""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def log(self, level, message):
        """로그 출력"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def test(self, test_name, method, endpoint, expected_status=200, **kwargs):
        """API 테스트 실행"""
        url = f"{self.base_url}{endpoint}"
        self.log("INFO", f"테스트: {test_name}")
        self.log("INFO", f"  {method} {endpoint}")

        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, **kwargs)
            elif method.upper() == "PUT":
                response = self.session.put(url, **kwargs)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                self.log("ERROR", f"Unknown method: {method}")
                return False

            success = response.status_code == expected_status
            status_str = "✓" if success else "✗"

            self.log("INFO", f"  {status_str} Status: {response.status_code} (expected {expected_status})")

            # 응답 본문 출력
            try:
                data = response.json()
                self.log("INFO", f"  응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except:
                self.log("INFO", f"  응답: {response.text[:100]}")

            self.test_results.append({
                'test_name': test_name,
                'success': success,
                'status_code': response.status_code,
                'expected': expected_status
            })

            return success

        except requests.exceptions.ConnectionError:
            self.log("ERROR", f"연결 실패: {self.base_url}")
            self.test_results.append({
                'test_name': test_name,
                'success': False,
                'error': 'Connection failed'
            })
            return False
        except Exception as e:
            self.log("ERROR", f"테스트 실패: {str(e)}")
            self.test_results.append({
                'test_name': test_name,
                'success': False,
                'error': str(e)
            })
            return False

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*80)
        print("Day 3 API 엔드포인트 테스트 시작")
        print("="*80 + "\n")

        # ====================================================================
        # 1. Aircraft Profiles - 조회
        # ====================================================================
        print("\n[1] 항공기 기종 프로필 - 조회\n")

        self.test(
            "모든 기종 프로필 조회",
            "GET",
            "/api/aircraft-profiles",
            expected_status=200
        )

        self.test(
            "특정 기종 프로필 조회 (B77L)",
            "GET",
            "/api/aircraft-profiles/B77L",
            expected_status=200
        )

        self.test(
            "존재하지 않는 기종 프로필 조회 (ERROR)",
            "GET",
            "/api/aircraft-profiles/XXXX",
            expected_status=404
        )

        # ====================================================================
        # 2. Aircraft Profiles - 생성
        # ====================================================================
        print("\n[2] 항공기 기종 프로필 - 생성\n")

        test_profile = {
            "icao_code": "TEST",
            "iata_code": "TST",
            "manufacturer": "Test Manufacturer",
            "model": "Test Model",
            "type_description": "Test aircraft",
            "default_speed_kmh": 800,
            "default_speed_knots": 432,
            "default_climb_fpm": 2000,
            "default_ceiling_fl": 430,
            "notes": "Test profile for Day 3 API"
        }

        self.test(
            "새 기종 프로필 생성 (TEST)",
            "POST",
            "/api/aircraft-profiles",
            expected_status=201,
            json=test_profile
        )

        self.test(
            "필수 필드 누락 - 생성 실패",
            "POST",
            "/api/aircraft-profiles",
            expected_status=400,
            json={"icao_code": "TEST2"}
        )

        # ====================================================================
        # 3. Aircraft Profiles - 업데이트
        # ====================================================================
        print("\n[3] 항공기 기종 프로필 - 업데이트\n")

        update_data = {
            "default_speed_kmh": 810,
            "default_climb_fpm": 2100,
            "notes": "Updated by Day 3 test"
        }

        self.test(
            "기종 프로필 업데이트 (TEST)",
            "PUT",
            "/api/aircraft-profiles/TEST",
            expected_status=200,
            json=update_data
        )

        self.test(
            "존재하지 않는 기종 업데이트 - 실패",
            "PUT",
            "/api/aircraft-profiles/XXXX",
            expected_status=404,
            json={"default_speed_kmh": 850}
        )

        # ====================================================================
        # 4. Aircraft Profiles - 삭제
        # ====================================================================
        print("\n[4] 항공기 기종 프로필 - 삭제\n")

        self.test(
            "기종 프로필 삭제 (TEST)",
            "DELETE",
            "/api/aircraft-profiles/TEST",
            expected_status=200
        )

        self.test(
            "삭제된 기종 다시 삭제 - 실패",
            "DELETE",
            "/api/aircraft-profiles/TEST",
            expected_status=404
        )

        # ====================================================================
        # 5. Climb Comparison - 조회
        # ====================================================================
        print("\n[5] 고도 상승 계산 비교 - 조회\n")

        self.test(
            "항공편 1의 고도 상승 계산 비교 조회",
            "GET",
            "/api/flights/1/climb-comparison",
            expected_status=200
        )

        self.test(
            "존재하지 않는 항공편 - 실패",
            "GET",
            "/api/flights/99999/climb-comparison",
            expected_status=404
        )

        # ====================================================================
        # 테스트 결과 요약
        # ====================================================================
        self.print_summary()

    def print_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "="*80)
        print("테스트 결과 요약")
        print("="*80)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.get('success', False))
        failed = total - passed

        print(f"\n총 테스트: {total}")
        print(f"성공: {passed} ✓")
        print(f"실패: {failed} ✗")
        print(f"성공률: {(passed/total)*100:.1f}%")

        if failed > 0:
            print("\n실패한 테스트:")
            for result in self.test_results:
                if not result.get('success', False):
                    print(f"  - {result['test_name']}")
                    if 'error' in result:
                        print(f"    에러: {result['error']}")

        print("\n" + "="*80 + "\n")

        return failed == 0


def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("Day 3 API 엔드포인트 테스트")
    print("="*80)
    print(f"\nAPI 서버: {BASE_URL}")
    print("테스트 항목:")
    print("  1. Aircraft Profiles CRUD (생성, 조회, 업데이트, 삭제)")
    print("  2. Climb Comparison (고도 상승 계산 비교 조회)")
    print("\n테스트를 시작하려면 Enter를 누르세요...")
    input()

    tester = APITester(BASE_URL)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
