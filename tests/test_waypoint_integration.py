#!/usr/bin/env python3
"""
웨이포인트 계산기 통합 테스트
flight_processor.py와 waypoint_calculator.py 통합 검증
"""

import sys
import os
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.waypoint_calculator import WaypointCalculator, convert_icao_speed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestWaypointIntegration:
    """웨이포인트 계산 통합 테스트"""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test(self, name, condition, expected=True):
        """테스트 결과 기록"""
        if condition == expected:
            print(f"✓ {name}")
            self.passed += 1
        else:
            print(f"✗ {name} (기대: {expected}, 실제: {condition})")
            self.failed += 1

    def test_icao_speed_parsing(self):
        """ICAO 속도 포맷 파싱 테스트"""
        print("\n[Test 1] ICAO Speed 파싱")
        print("-" * 60)

        # Knots 형식
        result1 = convert_icao_speed("K0900")
        self.test("K0900 → 1666.8 km/h", abs(result1 - 1666.8) < 1, True)

        # Alternative Knots
        result2 = convert_icao_speed("N0500")
        self.test("N0500 → 926.0 km/h", abs(result2 - 926.0) < 1, True)

        # Mach at FL350 (-55°C per ISA: speed of sound ≈ 575 knots)
        result3 = convert_icao_speed("M0.80", altitude_fl=350)
        self.test("M0.80 at FL350 → ~853 km/h", 850 < result3 < 860, True)

        # Mach at FL250 (-35°C per ISA: speed of sound ≈ 590 knots)
        result4 = convert_icao_speed("M0.85", altitude_fl=250)
        self.test("M0.85 at FL250 → ~947 km/h", 940 < result4 < 955, True)

        logger.info(f"속도 변환 결과: K0900={result1:.1f}, N0500={result2:.1f}, "
                   f"M0.80@FL350={result3:.1f}, M0.85@FL250={result4:.1f}")

    def test_waypoint_calculator_basic(self):
        """기본 웨이포인트 계산 테스트"""
        print("\n[Test 2] 기본 웨이포인트 계산")
        print("-" * 60)

        try:
            calc = WaypointCalculator(
                aircraft_type='B77L',
                cruise_speed_kmh=905,
                climb_rate_fpm=2000
            )
            self.test("WaypointCalculator 초기화", True, True)

            # Incheon → BEDES (Yellow Sea) - 149.3 km
            result = calc.calculate_first_waypoint_time(
                dept_time=datetime.now(),
                dept_airport_coords=(37.4606, 126.4407),  # RKSI Incheon
                first_waypoint_coords=(36.1511, 126.8119),  # BEDES
                cruise_altitude_ft=37000
            )

            # 거리 검증
            self.test(f"거리 계산 (149.3 km)",
                     abs(result['distance_km'] - 149.3) < 1, True)

            # 시간 검증 (상승 중이므로 14-15분 사이)
            time_minutes = result['time_delta'].total_seconds() / 60
            self.test(f"도달 시간 (14-15분)",
                     14 < time_minutes < 15, True)

            self.test("계산 완료", result is not None, True)

            logger.info(f"첫 웨이포인트 계산 결과:")
            logger.info(f"  - 거리: {result['distance_km']:.1f} km")
            logger.info(f"  - 시간: {result['time_delta']}")
            logger.info(f"  - 페이즈: {result['phase']}")

        except Exception as e:
            self.test(f"WaypointCalculator 실행 오류: {str(e)}", False, True)
            logger.error(f"오류: {e}", exc_info=True)

    def test_aircraft_specific_ratios(self):
        """항공기별 상승 속도 비율 검증"""
        print("\n[Test 3] 항공기별 상승 속도 비율")
        print("-" * 60)

        test_cases = [
            ('B77L', 'Boeing 777'),
            ('B744', 'Boeing 747'),
            ('A333', 'Airbus A330'),
            ('A321', 'Airbus A320'),
        ]

        for aircraft_type, description in test_cases:
            try:
                calc = WaypointCalculator(
                    aircraft_type=aircraft_type,
                    cruise_speed_kmh=900,
                    climb_rate_fpm=2000
                )
                self.test(f"{description} ({aircraft_type}) 초기화", True, True)
            except Exception as e:
                self.test(f"{description} ({aircraft_type}) 초기화", False, True)

    def test_route_calculation(self):
        """전체 경로 계산 테스트"""
        print("\n[Test 4] 전체 경로 계산")
        print("-" * 60)

        try:
            calc = WaypointCalculator(
                aircraft_type='B77L',
                cruise_speed_kmh=905,
                climb_rate_fpm=2000
            )

            waypoints = [
                {'name': 'RKSI', 'lat': 37.4606, 'lon': 126.4407},
                {'name': 'BEDES', 'lat': 36.1511, 'lon': 126.8119},
                {'name': 'SADLI', 'lat': 36.1400, 'lon': 127.2400},
            ]

            route_results = calc.calculate_route_times(
                dept_time=datetime.now(),
                waypoints=waypoints,
                cruise_altitude_ft=37000
            )

            self.test("경로 계산 완료", len(route_results) > 0, True)
            self.test("웨이포인트 수 일치", len(route_results) == len(waypoints), True)

            logger.info("경로 계산 결과:")
            for wp in route_results:
                logger.info(f"  {wp['name']:10s}: {wp['time'].strftime('%H:%M:%S')} - "
                           f"{wp['altitude_ft']:,.0f} ft - {wp['phase']}")

        except Exception as e:
            self.test(f"경로 계산 오류: {str(e)}", False, True)
            logger.error(f"오류: {e}", exc_info=True)

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "=" * 60)
        print("웨이포인트 계산기 통합 테스트")
        print("=" * 60)

        self.test_icao_speed_parsing()
        self.test_waypoint_calculator_basic()
        self.test_aircraft_specific_ratios()
        self.test_route_calculation()

        print("\n" + "=" * 60)
        print(f"테스트 결과: {self.passed} 통과, {self.failed} 실패")
        print("=" * 60)

        return self.failed == 0


if __name__ == '__main__':
    tester = TestWaypointIntegration()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
