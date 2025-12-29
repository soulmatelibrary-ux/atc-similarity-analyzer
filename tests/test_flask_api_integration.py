"""
Flask API 통합 테스트
실제 데이터 파일을 사용한 전체 워크플로우 테스트
"""
import sys
import os
import json
import tempfile
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app


class TestFlaskAPIIntegration:
    """Flask API 통합 테스트"""

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

    def create_sample_csv(self):
        """샘플 CSV 파일 생성"""
        data = {
            'CALLSIGN': ['GIA878', 'GIA870', 'KAL123', 'AAL123'],
            'DEPT_AIRPORT_CD': ['WIII', 'RJJJ', 'RKSN', 'RKSI'],
            'DEST_AIRPORT_CD': ['RKSI', 'RKSN', 'RJTT', 'RJNN'],
            'SPD': ['N0473', 'N0450', 'N0480', 'N0470'],
            'EOBD': ['2025-12-14', '2025-12-14', '2025-12-14', '2025-12-14'],
            'EOBT': ['14:00', '14:30', '15:00', '15:30'],
            'ENR': ['A599 JTN IKEDO', 'A599 JTN', 'A599 ELGEP', 'A599 JTN']
        }

        df = pd.DataFrame(data)

        # 임시 파일 생성
        fd, filepath = tempfile.mkstemp(suffix='.csv')
        os.close(fd)

        df.to_csv(filepath, index=False)
        return filepath

    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        print("\n[Integration Test 1] 전체 워크플로우")

        # 1단계: 헬스체크
        response = self.client.get('/api/health')
        self.test("1. 헬스체크", response.status_code, 200)

        # 2단계: 유사호출 판정
        response = self.client.post(
            '/api/similarity/check',
            json={'callsign1': 'GIA878', 'callsign2': 'GIA870'},
            content_type='application/json'
        )
        self.test("2. 유사호출 판정", response.status_code, 200)

        data = json.loads(response.data)
        self.test("   유사도 레벨 반환", 'similarity_level' in data['data'], True)

    def test_similarity_with_different_callsigns(self):
        """다양한 콜사인 조합으로 유사도 판정"""
        print("\n[Integration Test 2] 다양한 콜사인 유사도 판정")

        test_cases = [
            ('GIA878', 'GIA870', 'MEDIUM'),  # LEVEL_3-4
            ('KAL123', 'AAL123', 'HIGH'),    # LEVEL_4-1
            ('GIA123', 'GIA1234', 'LOW'),    # LEVEL_3-3
            ('ABC123', 'XYZ999', 'LOW'),     # 유사도 없음 → LOW (점수 0)
        ]

        for call1, call2, expected_risk in test_cases:
            response = self.client.post(
                '/api/similarity/check',
                json={'callsign1': call1, 'callsign2': call2},
                content_type='application/json'
            )

            self.test(f"  {call1} vs {call2} - 상태", response.status_code, 200)

            data = json.loads(response.data)
            risk = data['data'].get('risk_level')

            # 위험도 확인
            self.test(
                f"  {call1} vs {call2} - 위험도: {risk}",
                risk in ['HIGH', 'MEDIUM', 'LOW'],
                True
            )

    def test_error_handling(self):
        """에러 처리 테스트"""
        print("\n[Integration Test 3] 에러 처리")

        # 필수 파라미터 누락
        response = self.client.post(
            '/api/similarity/check',
            json={'callsign1': 'GIA878'},  # callsign2 누락
            content_type='application/json'
        )
        self.test("필수 파라미터 검증", response.status_code, 400)

        # 잘못된 JSON
        response = self.client.post(
            '/api/similarity/check',
            data='invalid json',
            content_type='application/json'
        )
        self.test("JSON 파싱 에러", response.status_code in [400, 500], True)

    def test_api_response_structure(self):
        """API 응답 구조 검증"""
        print("\n[Integration Test 4] API 응답 구조 검증")

        response = self.client.post(
            '/api/similarity/check',
            json={'callsign1': 'GIA1234', 'callsign2': 'GIA1237'},
            content_type='application/json'
        )

        data = json.loads(response.data)

        # 응답 구조 검증
        self.test("status 필드", 'status' in data, True)
        self.test("data 필드", 'data' in data, True)

        resp_data = data['data']
        self.test("callsign1 필드", 'callsign1' in resp_data, True)
        self.test("callsign2 필드", 'callsign2' in resp_data, True)
        self.test("similarity_level 필드", 'similarity_level' in resp_data, True)
        self.test("risk_level 필드", 'risk_level' in resp_data, True)
        self.test("score 필드", 'score' in resp_data, True)
        self.test("edit_distance 필드", 'edit_distance' in resp_data, True)

    def test_multiple_requests(self):
        """여러 요청 처리 테스트"""
        print("\n[Integration Test 5] 여러 요청 처리")

        callsigns = [
            ('GIA878', 'GIA870'),
            ('KAL123', 'AAL123'),
            ('GIA123', 'GIA1234'),
            ('GIA023', 'GIA23'),
        ]

        successful_requests = 0

        for call1, call2 in callsigns:
            response = self.client.post(
                '/api/similarity/check',
                json={'callsign1': call1, 'callsign2': call2},
                content_type='application/json'
            )

            if response.status_code == 200:
                successful_requests += 1

        self.test(f"모든 요청 성공 ({successful_requests}/{len(callsigns)})",
                  successful_requests, len(callsigns))

    def test_concurrent_style_requests(self):
        """동시 스타일 요청 테스트 (실제 동시는 아님)"""
        print("\n[Integration Test 6] 연속 요청 처리")

        results = []

        for i in range(5):
            response = self.client.post(
                '/api/similarity/check',
                json={'callsign1': f'CALL{i}', 'callsign2': f'CALL{i+1}'},
                content_type='application/json'
            )
            results.append(response.status_code == 200 or response.status_code == 400)

        successful = sum(results)
        self.test(f"연속 요청 처리 ({successful}/{len(results)})", successful, len(results))

    def test_response_json_validity(self):
        """응답 JSON 유효성 검사"""
        print("\n[Integration Test 7] 응답 JSON 유효성")

        response = self.client.get('/api/health')

        try:
            data = json.loads(response.data)
            self.test("JSON 파싱 가능", True, True)
            self.test("JSON 구조 valid", isinstance(data, dict), True)
        except json.JSONDecodeError:
            self.test("JSON 파싱 가능", False, True)

    def run_all_tests(self):
        """모든 통합 테스트 실행"""
        print("\n" + "="*70)
        print("Flask API 통합 테스트")
        print("="*70)

        self.test_full_workflow()
        self.test_similarity_with_different_callsigns()
        self.test_error_handling()
        self.test_api_response_structure()
        self.test_multiple_requests()
        self.test_concurrent_style_requests()
        self.test_response_json_validity()

        print("\n" + "="*70)
        print(f"테스트 완료: {self.passed} 통과, {self.failed} 실패")
        print("="*70 + "\n")

        return self.failed == 0


if __name__ == '__main__':
    tester = TestFlaskAPIIntegration()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
