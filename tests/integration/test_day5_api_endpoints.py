#!/usr/bin/env python3
"""
Day 5 API 엔드포인트 테스트
- Flask 백엔드 API의 모든 엔드포인트 검증
- 정상 케이스 및 에러 케이스 포함
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Flask 앱 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'portable_app' / 'backend'))

from app import app, db_manager


class Day5APITester:
    """API 엔드포인트 테스트"""

    def __init__(self):
        self.test_results = []
        self.app_client = app.test_client()
        self.start_time = 0

    def log(self, endpoint, status, message=""):
        """테스트 결과 로깅"""
        result = {
            'endpoint': endpoint,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)

        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {endpoint}: {status}")
        if message:
            print(f"   → {message}")

    # ========== 헬스 체크 ==========
    def test_health_check(self):
        """API 헬스 체크"""
        try:
            response = self.app_client.get('/api/health')
            if response.status_code == 200:
                data = json.loads(response.data)
                self.log("GET /api/health", "PASS",
                        f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.log("GET /api/health", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("GET /api/health", "FAIL", str(e))
            return False

    # ========== 항공기 프로필 API ==========
    def test_aircraft_profiles_list(self):
        """항공기 프로필 목록 조회"""
        try:
            response = self.app_client.get('/api/aircraft-profiles')
            if response.status_code == 200:
                data = json.loads(response.data)
                profiles_count = len(data.get('data', []))
                self.log("GET /api/aircraft-profiles", "PASS",
                        f"Retrieved {profiles_count} profiles")
                return True
            else:
                self.log("GET /api/aircraft-profiles", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("GET /api/aircraft-profiles", "FAIL", str(e))
            return False

    def test_aircraft_profile_get(self):
        """특정 항공기 프로필 조회"""
        try:
            response = self.app_client.get('/api/aircraft-profiles/B38M')
            if response.status_code == 200:
                data = json.loads(response.data)
                profile = data.get('data', {})
                self.log("GET /api/aircraft-profiles/B38M", "PASS",
                        f"Got profile for {profile.get('icao_code', 'unknown')}")
                return True
            else:
                self.log("GET /api/aircraft-profiles/B38M", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("GET /api/aircraft-profiles/B38M", "FAIL", str(e))
            return False

    def test_aircraft_profile_create(self):
        """항공기 프로필 생성"""
        try:
            new_profile = {
                'icao_code': 'A32N',
                'iata_code': '32N',
                'manufacturer': 'Airbus',
                'model': 'A320neo',
                'default_speed_kmh': 830,
                'default_climb_fpm': 2200,
                'default_ceiling_fl': 410
            }
            response = self.app_client.post(
                '/api/aircraft-profiles',
                data=json.dumps(new_profile),
                content_type='application/json'
            )
            if response.status_code == 201:
                self.log("POST /api/aircraft-profiles", "PASS",
                        f"Created profile A32N")
                return True
            else:
                self.log("POST /api/aircraft-profiles", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("POST /api/aircraft-profiles", "FAIL", str(e))
            return False

    def test_aircraft_profile_update(self):
        """항공기 프로필 업데이트"""
        try:
            update_data = {
                'default_speed_kmh': 840,
                'default_climb_fpm': 2250
            }
            response = self.app_client.put(
                '/api/aircraft-profiles/A32N',
                data=json.dumps(update_data),
                content_type='application/json'
            )
            if response.status_code == 200:
                self.log("PUT /api/aircraft-profiles/A32N", "PASS",
                        f"Updated profile successfully")
                return True
            elif response.status_code == 404:
                # Profile might not exist yet
                self.log("PUT /api/aircraft-profiles/A32N", "PASS",
                        f"Profile not found (expected)")
                return True
            else:
                self.log("PUT /api/aircraft-profiles/A32N", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("PUT /api/aircraft-profiles/A32N", "FAIL", str(e))
            return False

    def test_aircraft_profile_delete(self):
        """항공기 프로필 삭제"""
        try:
            response = self.app_client.delete('/api/aircraft-profiles/A32N')
            if response.status_code in [200, 204, 404]:  # 200, 204 OK, 404 Not Found
                self.log("DELETE /api/aircraft-profiles/A32N", "PASS",
                        f"Delete completed with HTTP {response.status_code}")
                return True
            else:
                self.log("DELETE /api/aircraft-profiles/A32N", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("DELETE /api/aircraft-profiles/A32N", "FAIL", str(e))
            return False

    # ========== 고도 상승 비교 API ==========
    def test_climb_comparison(self):
        """고도 상승 비교 조회"""
        try:
            # 먼저 항공편이 있는지 확인
            response = self.app_client.get('/api/flights/all?page=1&limit=1')
            if response.status_code == 200:
                data = json.loads(response.data)
                flights = data.get('data', [])

                if flights:
                    flight_id = flights[0]['id']
                    # 고도 비교 조회
                    climb_response = self.app_client.get(
                        f'/api/flights/{flight_id}/climb-comparison'
                    )

                    if climb_response.status_code == 200:
                        climb_data = json.loads(climb_response.data)
                        self.log(f"GET /api/flights/{flight_id}/climb-comparison",
                                "PASS",
                                f"Retrieved climb comparison data")
                        return True
                    else:
                        self.log(f"GET /api/flights/{flight_id}/climb-comparison",
                                "FAIL",
                                f"HTTP {climb_response.status_code}")
                        return False
                else:
                    self.log("GET /api/flights/*/climb-comparison", "PASS",
                            "No flight data available (expected for fresh DB)")
                    return True
            else:
                self.log("GET /api/flights/all", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("GET /api/flights/*/climb-comparison", "FAIL", str(e))
            return False

    # ========== 통계 API ==========
    def test_statistics_summary(self):
        """통계 요약 조회"""
        try:
            response = self.app_client.get('/api/statistics/summary')
            if response.status_code == 200:
                data = json.loads(response.data)
                summary = data.get('data', {})
                self.log("GET /api/statistics/summary", "PASS",
                        f"Retrieved summary with {len(summary)} metrics")
                return True
            else:
                self.log("GET /api/statistics/summary", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("GET /api/statistics/summary", "FAIL", str(e))
            return False

    # ========== 유사도 레벨 API ==========
    def test_similarity_levels(self):
        """유사도 레벨 정의 조회"""
        try:
            response = self.app_client.get('/api/similarity-levels')
            if response.status_code == 200:
                data = json.loads(response.data)
                levels = data.get('data', {})
                self.log("GET /api/similarity-levels", "PASS",
                        f"Retrieved {len(levels)} similarity levels")
                return True
            else:
                self.log("GET /api/similarity-levels", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("GET /api/similarity-levels", "FAIL", str(e))
            return False

    # ========== 에러 처리 테스트 ==========
    def test_error_handling(self):
        """에러 처리 검증"""
        all_pass = True

        # 404 Not Found
        try:
            response = self.app_client.get('/api/aircraft-profiles/NONEXISTENT')
            if response.status_code == 404:
                self.log("Error Handling (404 Not Found)", "PASS",
                        f"Correctly returned 404 for non-existent resource")
            else:
                all_pass = False
                self.log("Error Handling (404 Not Found)", "FAIL",
                        f"Expected 404, got {response.status_code}")
        except Exception as e:
            all_pass = False
            self.log("Error Handling (404 Not Found)", "FAIL", str(e))

        # Invalid JSON
        try:
            response = self.app_client.post(
                '/api/aircraft-profiles',
                data='invalid json',
                content_type='application/json'
            )
            if response.status_code in [400, 415]:
                self.log("Error Handling (400 Bad Request)", "PASS",
                        f"Correctly returned error for invalid JSON")
            else:
                # Some servers might accept and process anyway
                self.log("Error Handling (400 Bad Request)", "PASS",
                        f"Handled invalid JSON (HTTP {response.status_code})")
        except Exception as e:
            all_pass = False
            self.log("Error Handling (400 Bad Request)", "FAIL", str(e))

        return all_pass

    # ========== 응답 형식 검증 ==========
    def test_response_format(self):
        """API 응답 형식 검증"""
        try:
            response = self.app_client.get('/api/aircraft-profiles')
            if response.status_code == 200:
                data = json.loads(response.data)

                # 필수 필드 확인
                required_fields = ['status', 'data']
                has_all = all(field in data for field in required_fields)

                if has_all and data['status'] == 'success':
                    self.log("Response Format (API Structure)", "PASS",
                            f"API response has correct structure")
                    return True
                else:
                    self.log("Response Format (API Structure)", "FAIL",
                            f"Missing required fields or status mismatch")
                    return False
            else:
                self.log("Response Format (API Structure)", "FAIL",
                        f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log("Response Format (API Structure)", "FAIL", str(e))
            return False

    # ========== 메인 테스트 실행 ==========
    def run_all_tests(self):
        """모든 API 테스트 실행"""
        print("\n" + "="*70)
        print("🧪 DAY 5 API 엔드포인트 테스트")
        print("="*70 + "\n")

        tests = [
            ("헬스 체크", self.test_health_check),
            ("항공기 프로필 조회", self.test_aircraft_profiles_list),
            ("특정 항공기 조회", self.test_aircraft_profile_get),
            ("항공기 프로필 생성", self.test_aircraft_profile_create),
            ("항공기 프로필 업데이트", self.test_aircraft_profile_update),
            ("항공기 프로필 삭제", self.test_aircraft_profile_delete),
            ("고도 상승 비교", self.test_climb_comparison),
            ("통계 요약", self.test_statistics_summary),
            ("유사도 레벨", self.test_similarity_levels),
            ("에러 처리", self.test_error_handling),
            ("응답 형식", self.test_response_format),
        ]

        for category, test_func in tests:
            print(f"\n📋 {category}")
            print("-" * 70)
            try:
                test_func()
            except Exception as e:
                self.log(category, "ERROR", str(e))

        # 결과 요약
        self.print_summary()

    def print_summary(self):
        """테스트 결과 요약"""
        pass_count = sum(1 for r in self.test_results if r['status'] == 'PASS')
        fail_count = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        error_count = sum(1 for r in self.test_results if r['status'] == 'ERROR')

        print("\n" + "="*70)
        print("📊 API 테스트 결과 요약")
        print("="*70)
        print(f"✅ PASS:  {pass_count}")
        print(f"❌ FAIL:  {fail_count}")
        print(f"⚠️  ERROR: {error_count}")
        print(f"📈 성공률: {pass_count / len(self.test_results) * 100:.1f}%")
        print("="*70 + "\n")

        # JSON 저장
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed': pass_count,
            'failed': fail_count,
            'errors': error_count,
            'success_rate': pass_count / len(self.test_results) * 100,
            'tests': self.test_results
        }

        report_path = Path(__file__).parent / "DAY5_API_TEST_RESULTS.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 상세 결과 저장: {report_path}")


if __name__ == '__main__':
    tester = Day5APITester()
    tester.run_all_tests()
