"""
엔드-투-엔드 통합 테스트
실제 항공편 데이터를 사용하여 전체 시스템 동작 확인
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.similarity_engine import check_similarity, get_risk_level
from core.sector_calculator import SectorCalculator
from core.statistics_engine import StatisticsEngine


class TestE2E:
    """엔드-투-엔드 통합 테스트"""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test(self, name, condition, expected=True):
        if condition == expected:
            print(f"✓ {name}")
            self.passed += 1
        else:
            print(f"✗ {name} (기대: {expected}, 실제: {condition})")
            self.failed += 1

    def test_similarity_with_real_callsigns(self):
        """실제 콜사인으로 유사도 판정 테스트"""
        print("\n[E2E Test 1] 유사호출 판정")

        test_cases = [
            ('GIA1234', 'GIA1237', 'LEVEL_3-8', 'HIGH'),  # 3자리 연속
            ('KAL123', 'AAL123', 'LEVEL_4-1', 'HIGH'),    # 다른 prefix + 숫자 동일
            ('GIA123', 'GIA1234', 'LEVEL_3-3', 'LOW'),    # 연속 블록 동일
            ('GIA023', 'GIA23', 'LEVEL_5-1', 'LOW'),      # Leading zero
        ]

        for callsign1, callsign2, expected_level, expected_risk in test_cases:
            level, ed = check_similarity(callsign1, callsign2)
            risk = get_risk_level(level)

            self.test(
                f"  {callsign1} vs {callsign2} → {level}",
                level, expected_level
            )
            self.test(
                f"    위험도: {risk}",
                risk, expected_risk
            )

    def test_sector_coexistence_workflow(self):
        """섹터 공존 계산 워크플로우"""
        print("\n[E2E Test 2] 섹터 공존 계산 워크플로우")

        calculator = SectorCalculator()

        # 실제 항공편 시나리오
        flights = [
            {
                'callsign': 'GIA878',
                'sector': 'JH',
                'entry_time': datetime(2025, 12, 14, 14, 30),
                'exit_time': datetime(2025, 12, 14, 14, 50),
                'lat': 37.2, 'lon': 127.1,
                'altitude': 370,
                'speed': 473
            },
            {
                'callsign': 'AIA878',
                'sector': 'JH',
                'entry_time': datetime(2025, 12, 14, 14, 35),
                'exit_time': datetime(2025, 12, 14, 14, 55),
                'lat': 37.25, 'lon': 127.05,
                'altitude': 350,
                'speed': 470
            },
            {
                'callsign': 'KAL456',
                'sector': 'JN',
                'entry_time': datetime(2025, 12, 14, 15, 0),
                'exit_time': datetime(2025, 12, 14, 15, 20),
                'lat': 37.5, 'lon': 127.5,
                'altitude': 280,
                'speed': 450
            }
        ]

        # 1단계: 모든 공존 계산
        coexistences = calculator.calculate_all_coexistences(flights)
        self.test("공존 계산 완료", len(coexistences) > 0, True)

        # 2단계: 위험도 판정
        has_risk_levels = all('risk_level' in c for c in coexistences)
        self.test("위험도 판정 포함", has_risk_levels, True)

        # 3단계: 필터링
        filtered = calculator.filter_coexistences(
            coexistences,
            min_coexist_minutes=10
        )
        self.test("필터링 적용", len(filtered) <= len(coexistences), True)

        # 4단계: 섹터별 통계
        stats = calculator.get_sector_statistics(coexistences)
        self.test("섹터별 통계 생성", len(stats) > 0, True)
        self.test("JH 섹터 존재", 'JH' in stats, True)

    def test_statistics_generation(self):
        """통계 생성 워크플로우"""
        print("\n[E2E Test 3] 통계 분석 워크플로우")

        stats_engine = StatisticsEngine()

        # 샘플 공존 데이터
        coexistences = [
            {
                'callsign1': 'GIA878', 'callsign2': 'AIA878',
                'sector': 'JH', 'risk_level': 'LOW',
                'coexist_minutes': 20.0,
                'entry_time': datetime(2025, 12, 14, 14, 30),
                'exit_time': datetime(2025, 12, 14, 14, 50)
            },
            {
                'callsign1': 'KAL123', 'callsign2': 'AAL123',
                'sector': 'JN', 'risk_level': 'HIGH',
                'coexist_minutes': 15.0,
                'entry_time': datetime(2025, 12, 14, 15, 0),
                'exit_time': datetime(2025, 12, 14, 15, 15)
            }
        ]

        stats_engine.add_coexistence_data(coexistences)

        # 1단계: 시간대별 통계
        hourly = stats_engine.hourly_statistics()
        self.test("시간대별 통계", len(hourly) > 0, True)
        self.test("14시간대 포함", '14' in hourly, True)

        # 2단계: 섹터별 통계
        sector = stats_engine.sector_statistics()
        self.test("섹터별 통계", len(sector) > 0, True)
        self.test("JH 섹터 포함", 'JH' in sector, True)

        # 3단계: 콜사인별 통계
        callsign = stats_engine.callsign_statistics()
        self.test("콜사인별 통계", len(callsign) > 0, True)
        self.test("GIA878 포함", 'GIA878' in callsign, True)

        # 4단계: 위험도별 통계
        risk = stats_engine.risk_level_statistics()
        self.test("위험도별 통계", len(risk) == 4, True)

        # 5단계: 요약 통계
        summary = stats_engine.generate_summary()
        self.test("요약 통계 생성", 'total_coexistences' in summary, True)
        self.test("위험도 분포 포함", 'risk_distribution' in summary, True)

    def test_complete_pipeline(self):
        """완전한 파이프라인 테스트"""
        print("\n[E2E Test 4] 완전한 파이프라인 (유사도 → 공존 → 통계)")

        # 단계 1: 유사호출 판정
        level1, _ = check_similarity('GIA1234', 'GIA1237')
        self.test("Step 1: 유사호출 판정", level1 != '', True)

        # 단계 2: 공존 계산
        calculator = SectorCalculator()
        flight1 = {
            'callsign': 'GIA1234', 'sector': 'JH',
            'entry_time': datetime(2025, 12, 14, 14, 0),
            'exit_time': datetime(2025, 12, 14, 14, 30),
            'lat': 37.2, 'lon': 127.1, 'altitude': 370
        }
        flight2 = {
            'callsign': 'GIA1237', 'sector': 'JH',
            'entry_time': datetime(2025, 12, 14, 14, 15),
            'exit_time': datetime(2025, 12, 14, 14, 45),
            'lat': 37.25, 'lon': 127.05, 'altitude': 350
        }

        coexist = calculator.calculate_coexistence(flight1, flight2)
        self.test("Step 2: 공존 계산", coexist is not None, True)

        # 단계 3: 통계 분석
        if coexist:
            stats_engine = StatisticsEngine()
            stats_engine.add_coexistence_data([coexist])
            summary = stats_engine.generate_summary()
            self.test("Step 3: 통계 생성", summary['total_coexistences'], 1)

    def test_data_export(self):
        """데이터 내보내기 테스트"""
        print("\n[E2E Test 5] 데이터 내보내기")

        calculator = SectorCalculator()

        coexistences = [
            {
                'callsign1': 'GIA878', 'callsign2': 'AIA878',
                'sector': 'JH', 'risk_level': 'LOW',
                'coexist_minutes': 10.0,
                'horizontal_separation_km': 7.1,
                'vertical_separation_feet': 2000,
                'entry_time': datetime(2025, 12, 14, 14, 30),
                'exit_time': datetime(2025, 12, 14, 14, 40)
            }
        ]

        # CSV 내보내기
        try:
            calculator.export_to_csv(coexistences, 'test_output.csv')
            self.test("CSV 내보내기", os.path.exists('test_output.csv'), True)
            if os.path.exists('test_output.csv'):
                os.remove('test_output.csv')
        except Exception as e:
            self.test("CSV 내보내기", False, True)

        # JSON 내보내기
        try:
            calculator.export_to_json(coexistences, 'test_output.json')
            self.test("JSON 내보내기", os.path.exists('test_output.json'), True)
            if os.path.exists('test_output.json'):
                os.remove('test_output.json')
        except Exception as e:
            self.test("JSON 내보내기", False, True)

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*70)
        print("엔드-투-엔드 통합 테스트")
        print("="*70)

        self.test_similarity_with_real_callsigns()
        self.test_sector_coexistence_workflow()
        self.test_statistics_generation()
        self.test_complete_pipeline()
        self.test_data_export()

        print("\n" + "="*70)
        print(f"테스트 완료: {self.passed} 통과, {self.failed} 실패")
        print("="*70 + "\n")

        return self.failed == 0


if __name__ == '__main__':
    tester = TestE2E()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
