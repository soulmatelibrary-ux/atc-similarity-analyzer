"""
통계 분석 엔진 테스트
"""
import sys
import os
from datetime import datetime

# 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.statistics_engine import StatisticsEngine


class TestStatisticsEngine:
    """통계 분석 엔진 테스트 클래스"""

    def __init__(self):
        """초기화"""
        self.engine = StatisticsEngine()
        self.passed = 0
        self.failed = 0
        self.setup_test_data()

    def setup_test_data(self):
        """테스트 데이터 설정"""
        coexistences = [
            # 14시간대
            {
                'callsign1': 'GIA878',
                'callsign2': 'AIA878',
                'sector': 'JH',
                'coexist_minutes': 10.0,
                'risk_level': 'LOW',
                'entry_time': datetime(2025, 12, 14, 14, 30),
                'exit_time': datetime(2025, 12, 14, 14, 40)
            },
            # 15시간대
            {
                'callsign1': 'KAL123',
                'callsign2': 'AAL123',
                'sector': 'JN',
                'coexist_minutes': 15.0,
                'risk_level': 'HIGH',
                'entry_time': datetime(2025, 12, 14, 15, 0),
                'exit_time': datetime(2025, 12, 14, 15, 15)
            },
            # 16시간대 - 같은 콜사인쌍
            {
                'callsign1': 'GIA878',
                'callsign2': 'BIA870',
                'sector': 'JH',
                'coexist_minutes': 8.0,
                'risk_level': 'MEDIUM',
                'entry_time': datetime(2025, 12, 14, 16, 0),
                'exit_time': datetime(2025, 12, 14, 16, 8)
            },
            # 16시간대 - CRITICAL
            {
                'callsign1': 'KAL456',
                'callsign2': 'AAL456',
                'sector': 'KH',
                'coexist_minutes': 20.0,
                'risk_level': 'CRITICAL',
                'entry_time': datetime(2025, 12, 14, 16, 30),
                'exit_time': datetime(2025, 12, 14, 16, 50)
            }
        ]

        self.engine.add_coexistence_data(coexistences)

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

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*70)
        print("통계 분석 엔진 테스트 시작")
        print("="*70 + "\n")

        # Test 1: 시간대별 통계
        print("[Test 1] 시간대별 통계")
        hourly = self.engine.hourly_statistics()
        self.test("14시간대 통계 생성", '14' in hourly, True)
        self.test("14시간대 이벤트 수", hourly['14']['event_count'], 1)
        self.test("14시간대 저위험", hourly['14']['low_risk'], 1)
        self.test("15시간대 통계 생성", '15' in hourly, True)
        self.test("15시간대 고위험", hourly['15']['high_risk'], 1)
        self.test("16시간대 이벤트 수", hourly['16']['event_count'], 2)
        self.test("16시간대 CRITICAL", hourly['16']['critical_risk'], 1)

        # Test 2: 섹터별 통계
        print("\n[Test 2] 섹터별 통계")
        sector = self.engine.sector_statistics()
        self.test("섹터 JH 통계 생성", 'JH' in sector, True)
        self.test("섹터 JH 이벤트 수", sector['JH']['event_count'], 2)
        self.test("섹터 JN 통계 생성", 'JN' in sector, True)
        self.test("섹터 JN 이벤트 수", sector['JN']['event_count'], 1)
        self.test("섹터 KH 통계 생성", 'KH' in sector, True)
        self.test("섹터 총 수", len(sector), 3)

        # Test 3: 콜사인별 통계
        print("\n[Test 3] 콜사인별 통계")
        callsign = self.engine.callsign_statistics()
        self.test("콜사인 GIA878 통계", 'GIA878' in callsign, True)
        self.test("GIA878 공존 수", callsign['GIA878']['coexistence_count'], 2)
        self.test("GIA878 섹터", callsign['GIA878']['sectors'], ['JH'])
        self.test("콜사인 AAL123 통계", 'AAL123' in callsign, True)
        self.test("AAL123 공존 수", callsign['AAL123']['coexistence_count'], 1)
        self.test("콜사인 총 수", len(callsign), 7)  # GIA878, AIA878, BIA870, KAL123, AAL123, KAL456, AAL456

        # Test 4: 위험도별 통계
        print("\n[Test 4] 위험도별 통계")
        risk = self.engine.risk_level_statistics()
        self.test("CRITICAL 이벤트 수", risk['CRITICAL']['count'], 1)
        self.test("HIGH 이벤트 수", risk['HIGH']['count'], 1)
        self.test("MEDIUM 이벤트 수", risk['MEDIUM']['count'], 1)
        self.test("LOW 이벤트 수", risk['LOW']['count'], 1)

        # 위험도별 비율
        self.test("CRITICAL 비율", risk['CRITICAL']['percentage'], 25.0)
        self.test("HIGH 비율", risk['HIGH']['percentage'], 25.0)
        self.test("MEDIUM 비율", risk['MEDIUM']['percentage'], 25.0)
        self.test("LOW 비율", risk['LOW']['percentage'], 25.0)

        # Test 5: 요약 통계
        print("\n[Test 5] 요약 통계")
        summary = self.engine.generate_summary()
        self.test("전체 공존 수", summary['total_coexistences'], 4)
        self.test("섹터 수", summary['total_sectors'], 3)
        self.test("콜사인 수", summary['total_callsigns'], 7)
        self.test("CRITICAL 개수", summary['risk_distribution']['CRITICAL'], 1)
        self.test("HIGH 개수", summary['risk_distribution']['HIGH'], 1)
        self.test("고위험 비율 (50%)", summary['high_risk_percentage'], 50.0)

        # Test 6: 시간대별 평균 공존시간
        print("\n[Test 6] 시간대별 평균 공존시간")
        hourly = self.engine.hourly_statistics()
        self.test("14시간대 평균", hourly['14']['avg_coexist_minutes'], 10.0)
        self.test("15시간대 평균", hourly['15']['avg_coexist_minutes'], 15.0)
        avg_16 = (8 + 20) / 2
        self.test("16시간대 평균", round(hourly['16']['avg_coexist_minutes'], 1), round(avg_16, 1))

        # Test 7: 섹터별 위험도 비율
        print("\n[Test 7] 섹터별 위험도 비율")
        sector = self.engine.sector_statistics()
        # JH: LOW(1) + MEDIUM(1) = 0 high risk / 2 events = 0%
        self.test("섹터 JH 고위험 비율", sector['JH']['high_risk_ratio'], 0.0)
        # JN: HIGH(1) = 1 high risk / 1 event = 100%
        self.test("섹터 JN 고위험 비율", sector['JN']['high_risk_ratio'], 1.0)
        # KH: CRITICAL(1) = 1 high risk / 1 event = 100%
        self.test("섹터 KH 고위험 비율", sector['KH']['high_risk_ratio'], 1.0)

        # Test 8: 섹터별 상위 콜사인 쌍
        print("\n[Test 8] 섹터별 상위 콜사인 쌍")
        sector = self.engine.sector_statistics()
        jh_pairs = [p['pair'] for p in sector['JH']['top_callsign_pairs']]
        self.test("섹터 JH 콜사인 쌍 포함", 'AIA878-GIA878' in jh_pairs or 'GIA878-AIA878' in jh_pairs, True)

        # Test 9: 콜사인별 가장 흔한 파트너
        print("\n[Test 9] 콜사인별 가장 흔한 파트너")
        callsign = self.engine.callsign_statistics()
        # GIA878의 파트너: AIA878(1), BIA870(1) - 같으면 먼저 나온 것
        self.test("GIA878 파트너 존재", callsign['GIA878']['most_common_partner'] is not None, True)

        # Test 10: JSON 내보내기
        print("\n[Test 10] JSON 내보내기")
        try:
            summary = self.engine.generate_summary()
            self.engine.export_to_json(summary, 'test_summary.json')
            import os
            file_exists = os.path.exists('test_summary.json')
            self.test("JSON 파일 생성", file_exists, True)
            if file_exists:
                os.remove('test_summary.json')
        except Exception as e:
            print(f"✗ JSON 내보내기 실패: {e}")
            self.failed += 1

        # Test 11: 콜사인별 위험도 비율
        print("\n[Test 11] 콜사인별 위험도 비율")
        callsign = self.engine.callsign_statistics()
        # AAL123: HIGH(1) = 100%
        self.test("AAL123 고위험 비율", callsign['AAL123']['high_risk_percentage'], 100.0)
        # AIA878: LOW(1) = 0%
        self.test("AIA878 고위험 비율", callsign['AIA878']['high_risk_percentage'], 0.0)

        # Test 12: 콜사인별 평균 위험도
        print("\n[Test 12] 콜사인별 평균 위험도")
        callsign = self.engine.callsign_statistics()
        self.test("AAL123 평균 위험도", callsign['AAL123']['avg_risk_level'], 'HIGH')
        self.test("AIA878 평균 위험도", callsign['AIA878']['avg_risk_level'], 'LOW')

        # 결과 출력
        print("\n" + "="*70)
        print(f"테스트 완료: {self.passed} 통과, {self.failed} 실패")
        print("="*70 + "\n")

        return self.failed == 0


if __name__ == '__main__':
    tester = TestStatisticsEngine()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
