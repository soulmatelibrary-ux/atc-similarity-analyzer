"""
섹터 공존 계산 엔진 테스트
"""
import sys
import os
from datetime import datetime, timedelta

# 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sector_calculator import SectorCalculator


class TestSectorCalculator:
    """섹터 공존 계산 엔진 테스트 클래스"""

    def __init__(self):
        """초기화"""
        self.calculator = SectorCalculator()
        self.passed = 0
        self.failed = 0

    def test(self, name, condition, expected=True):
        """
        테스트 실행

        Args:
            name: 테스트 이름
            condition: 테스트 조건
            expected: 예상 결과 (기본값: True)
        """
        if condition == expected:
            print(f"✓ {name}")
            self.passed += 1
        else:
            print(f"✗ {name} (기대값: {expected}, 실제값: {condition})")
            self.failed += 1

    def test_range(self, name, value, min_val, max_val, tolerance=0.01):
        """
        범위 테스트

        Args:
            name: 테스트 이름
            value: 값
            min_val: 최소값
            max_val: 최대값
            tolerance: 허용 오차
        """
        if min_val - tolerance <= value <= max_val + tolerance:
            print(f"✓ {name} (값: {value})")
            self.passed += 1
        else:
            print(f"✗ {name} (기대: {min_val}-{max_val}, 실제: {value})")
            self.failed += 1

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*70)
        print("섹터 공존 계산 엔진 테스트 시작")
        print("="*70 + "\n")

        # Test 1: Haversine 거리 계산
        print("[Test 1] Haversine 거리 계산")
        dist = self.calculator.haversine(37.2, 127.1, 37.25, 127.15)
        self.test_range("좌표 (37.2, 127.1) -> (37.25, 127.15)", dist, 5, 10)

        # Test 2: 수직 분리 계산
        print("\n[Test 2] 수직 분리 거리 계산")
        vert_sep = self.calculator.calculate_vertical_separation(370, 350)
        self.test("고도 차이 (FL370 vs FL350)", vert_sep, 2000)

        vert_sep = self.calculator.calculate_vertical_separation(370, 370)
        self.test("고도 동일 (FL370 vs FL370)", vert_sep, 0)

        # Test 3: 시간 겹침 계산
        print("\n[Test 3] 시간 겹침 계산")
        start1 = datetime(2025, 12, 14, 14, 30)
        end1 = datetime(2025, 12, 14, 14, 45)
        start2 = datetime(2025, 12, 14, 14, 35)
        end2 = datetime(2025, 12, 14, 14, 50)

        overlap = self.calculator.time_overlap(start1, end1, start2, end2)
        overlap_minutes = overlap.total_seconds() / 60
        self.test("시간 겹침 (14:35-14:45 = 10분)", overlap_minutes, 10)

        # 겹침 없음
        start1 = datetime(2025, 12, 14, 14, 30)
        end1 = datetime(2025, 12, 14, 14, 45)
        start2 = datetime(2025, 12, 14, 14, 50)
        end2 = datetime(2025, 12, 14, 15, 0)

        overlap = self.calculator.time_overlap(start1, end1, start2, end2)
        overlap_minutes = overlap.total_seconds() / 60
        self.test("겹침 없음", overlap_minutes, 0)

        # Test 4: 공존 정보 계산
        print("\n[Test 4] 공존 정보 계산")
        flight1 = {
            'callsign': 'GIA878',
            'sector': 'JH',
            'entry_time': datetime(2025, 12, 14, 14, 30),
            'exit_time': datetime(2025, 12, 14, 14, 45),
            'lat': 37.2,
            'lon': 127.1,
            'altitude': 370,
            'speed': 473
        }

        flight2 = {
            'callsign': 'AIA878',
            'sector': 'JH',
            'entry_time': datetime(2025, 12, 14, 14, 35),
            'exit_time': datetime(2025, 12, 14, 14, 50),
            'lat': 37.25,
            'lon': 127.05,
            'altitude': 350,
            'speed': 470
        }

        coexist = self.calculator.calculate_coexistence(flight1, flight2)
        self.test("동일 섹터 공존 계산", coexist is not None, True)
        self.test("공존 시간 10분", coexist['coexist_minutes'], 10.0)
        self.test("수평 분리 5-10km", 5 <= coexist['horizontal_separation_km'] <= 10, True)
        self.test("수직 분리 2000피트", coexist['vertical_separation_feet'], 2000)

        # Test 5: 위험도 판정
        print("\n[Test 5] 위험도 판정")
        # CRITICAL: 수평/수직 분리 모두 미충족, 공존 시간 10분 이상
        risk = self.calculator._assess_risk(15, 1.5, 500)
        self.test("위험도: CRITICAL (분리 미충족, 공존 15분)", risk, 'CRITICAL')

        # HIGH: 수평 분리만 미충족, 공존 시간 > 15분
        risk = self.calculator._assess_risk(20, 1.5, 2000)
        self.test("위험도: HIGH (수평 미충족, 공존 20분)", risk, 'HIGH')

        # MEDIUM: 수직 분리만 미충족
        risk = self.calculator._assess_risk(10, 5, 500)
        self.test("위험도: MEDIUM (수직 미충족, 공존 10분)", risk, 'MEDIUM')

        # LOW: 분리 기준 충족
        risk = self.calculator._assess_risk(5, 5, 2000)
        self.test("위험도: LOW (분리 기준 충족)", risk, 'LOW')

        # Test 6: 다른 섹터의 공존
        print("\n[Test 6] 다른 섹터 항공편")
        flight3 = {
            'callsign': 'KAL456',
            'sector': 'JN',  # 다른 섹터
            'entry_time': datetime(2025, 12, 14, 14, 30),
            'exit_time': datetime(2025, 12, 14, 14, 45),
            'lat': 37.5,
            'lon': 127.5,
            'altitude': 280,
            'speed': 450
        }

        coexist = self.calculator.calculate_coexistence(flight1, flight3)
        self.test("다른 섹터는 None 반환", coexist is None, True)

        # Test 7: 시간 겹침 없음
        print("\n[Test 7] 시간 겹침 없음")
        flight4 = {
            'callsign': 'BIA878',
            'sector': 'JH',
            'entry_time': datetime(2025, 12, 14, 15, 0),  # 14:45 이후
            'exit_time': datetime(2025, 12, 14, 15, 15),
            'lat': 37.2,
            'lon': 127.1,
            'altitude': 370,
            'speed': 473
        }

        coexist = self.calculator.calculate_coexistence(flight1, flight4)
        self.test("겹침 없으면 None 반환", coexist is None, True)

        # Test 8: 모든 공존 계산
        print("\n[Test 8] 모든 공존 계산")
        flights = [flight1, flight2, flight3]
        coexistences = self.calculator.calculate_all_coexistences(flights)
        self.test("3개 항공편 중 1개 공존 쌍", len(coexistences), 1)

        # Test 9: 필터링
        print("\n[Test 9] 필터링")
        # 공존 시간 최소값 필터
        filtered = self.calculator.filter_coexistences(coexistences, min_coexist_minutes=15)
        self.test("공존 15분 이상 필터: 0건", len(filtered), 0)

        filtered = self.calculator.filter_coexistences(coexistences, min_coexist_minutes=5)
        self.test("공존 5분 이상 필터: 1건", len(filtered), 1)

        # 위험도 필터 (실제로는 LOW이므로 0건)
        filtered = self.calculator.filter_coexistences(
            coexistences,
            risk_levels=['CRITICAL', 'HIGH', 'MEDIUM']
        )
        self.test("중위험 이상 필터: 0건 (실제는 LOW)", len(filtered), 0)

        # LOW 필터
        filtered = self.calculator.filter_coexistences(
            coexistences,
            risk_levels=['LOW']
        )
        self.test("저위험 필터: 1건", len(filtered), 1)

        # Test 10: 섹터별 통계
        print("\n[Test 10] 섹터별 통계")
        stats = self.calculator.get_sector_statistics(coexistences)
        self.test("섹터 JH 통계 생성", 'JH' in stats, True)
        self.test("섹터 JH 이벤트 수", stats['JH']['event_count'], 1)
        self.test_range("섹터 JH 평균 공존시간", stats['JH']['avg_coexist_minutes'], 9, 11)

        # Test 11: CSV 내보내기
        print("\n[Test 11] CSV 내보내기")
        try:
            self.calculator.export_to_csv(coexistences, 'test_coexistence.csv')
            import os
            file_exists = os.path.exists('test_coexistence.csv')
            self.test("CSV 파일 생성", file_exists, True)
            if file_exists:
                os.remove('test_coexistence.csv')
        except Exception as e:
            print(f"✗ CSV 내보내기 실패: {e}")
            self.failed += 1

        # Test 12: JSON 내보내기
        print("\n[Test 12] JSON 내보내기")
        try:
            self.calculator.export_to_json(coexistences, 'test_coexistence.json')
            import os
            file_exists = os.path.exists('test_coexistence.json')
            self.test("JSON 파일 생성", file_exists, True)
            if file_exists:
                os.remove('test_coexistence.json')
        except Exception as e:
            print(f"✗ JSON 내보내기 실패: {e}")
            self.failed += 1

        # 결과 출력
        print("\n" + "="*70)
        print(f"테스트 완료: {self.passed} 통과, {self.failed} 실패")
        print("="*70 + "\n")

        return self.failed == 0


if __name__ == '__main__':
    tester = TestSectorCalculator()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
