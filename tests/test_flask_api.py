"""
Flask API 엔드포인트 테스트
"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app


class TestFlaskAPI:
    """Flask API 테스트 클래스"""

    def __init__(self):
        self.app = app
        self.client = app.test_client()
        self.passed = 0
        self.failed = 0

    def test(self, name, condition, expected=True):
        if condition == expected:
            print(f"✓ {name}")
            self.passed += 1
        else:
            print(f"✗ {name} (기대: {expected}, 실제: {condition})")
            self.failed += 1

    def test_health_check(self):
        """헬스체크 엔드포인트 테스트"""
        print("\n[Test 1] 헬스체크 엔드포인트")

        response = self.client.get('/api/health')
        self.test("상태 코드 200", response.status_code, 200)

        data = json.loads(response.data)
        self.test("응답 형식 correct", 'status' in data, True)
        self.test("상태: ok", data.get('status'), 'ok')
        self.test("버전 정보 포함", 'version' in data, True)
        self.test("타임스탬프 포함", 'timestamp' in data, True)

    def test_similarity_check(self):
        """유사호출 판정 엔드포인트 테스트"""
        print("\n[Test 2] 유사호출 판정 엔드포인트")

        # 정상 요청
        response = self.client.post(
            '/api/similarity/check',
            json={
                'callsign1': 'GIA1234',
                'callsign2': 'GIA1237'
            },
            content_type='application/json'
        )
        self.test("상태 코드 200", response.status_code, 200)

        data = json.loads(response.data)
        self.test("응답 상태: success", data.get('status'), 'success')
        self.test("유사도 레벨 포함", 'similarity_level' in data['data'], True)
        self.test("위험도 포함", 'risk_level' in data['data'], True)
        self.test("점수 포함", 'score' in data['data'], True)

        # 필수 파라미터 누락
        response = self.client.post(
            '/api/similarity/check',
            json={'callsign1': 'GIA1234'},
            content_type='application/json'
        )
        self.test("필수 파라미터 검증", response.status_code, 400)

    def test_simulation_without_data(self):
        """데이터 없이 시뮬레이션 실행 테스트"""
        print("\n[Test 3] 시뮬레이션 (데이터 없음)")

        response = self.client.post(
            '/api/simulation/run',
            json={},
            content_type='application/json'
        )

        # 데이터 없으므로 실패해야 함
        self.test("상태 코드 400", response.status_code, 400)

        data = json.loads(response.data)
        self.test("에러 상태", data.get('status'), 'error')

    def test_statistics_without_simulation(self):
        """시뮬레이션 없이 통계 조회 테스트"""
        print("\n[Test 4] 통계 조회 (시뮬레이션 없음)")

        response = self.client.get('/api/statistics/summary')

        # 시뮬레이션 없으므로 실패해야 함
        self.test("상태 코드 400", response.status_code, 400)

        data = json.loads(response.data)
        self.test("에러 상태", data.get('status'), 'error')

    def test_404_error(self):
        """404 에러 핸들링 테스트"""
        print("\n[Test 5] 에러 핸들링")

        response = self.client.get('/api/nonexistent')
        self.test("404 상태 코드", response.status_code, 404)

        data = json.loads(response.data)
        self.test("에러 상태", data.get('status'), 'error')

    def test_api_endpoints_exist(self):
        """API 엔드포인트 존재 확인"""
        print("\n[Test 6] API 엔드포인트 존재 확인")

        endpoints = [
            ('/api/health', 'GET'),
            ('/api/similarity/check', 'POST'),
            ('/api/simulation/run', 'POST'),
            ('/api/statistics/summary', 'GET'),
            ('/api/statistics/detailed', 'GET'),
            ('/api/export/json', 'GET'),
            ('/api/upload/flights', 'POST'),
        ]

        for endpoint, method in endpoints:
            if method == 'GET':
                response = self.client.get(endpoint)
            else:
                response = self.client.post(
                    endpoint,
                    json={},
                    content_type='application/json'
                )

            # 404가 아닌지 확인 (400 등 다른 에러는 괜찮음)
            is_endpoint_exists = response.status_code != 404
            self.test(f"엔드포인트 존재: {method} {endpoint}", is_endpoint_exists, True)

    def test_json_response_format(self):
        """JSON 응답 형식 검증"""
        print("\n[Test 7] JSON 응답 형식 검증")

        response = self.client.get('/api/health')
        self.test("응답이 JSON", response.content_type, 'application/json')

        data = json.loads(response.data)
        self.test("상태 필드 포함", 'status' in data, True)

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*70)
        print("Flask API 엔드포인트 테스트")
        print("="*70)

        self.test_health_check()
        self.test_similarity_check()
        self.test_simulation_without_data()
        self.test_statistics_without_simulation()
        self.test_404_error()
        self.test_api_endpoints_exist()
        self.test_json_response_format()

        print("\n" + "="*70)
        print(f"테스트 완료: {self.passed} 통과, {self.failed} 실패")
        print("="*70 + "\n")

        return self.failed == 0


if __name__ == '__main__':
    tester = TestFlaskAPI()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
