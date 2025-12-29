#!/usr/bin/env python3
"""
Day 5 통합 테스트 스크립트
- CSV 업로드 → 데이터베이스 저장 → API 검증
- 고도 상승 계산 결과 확인
- 성능 측정
"""

import sys
import os
import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path

# 프로젝트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'portable_app'))

from core.flight_processor import (
    parse_altitude,
    get_aircraft_speed_and_climb,
    calculate_climb_time_simple,
    calculate_waypoints_with_eet
)
from database.db_manager import DatabaseManager


class Day5IntegrationTester:
    """Day 5 통합 테스트"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.test_results = []
        self.start_time = time.time()

    def log(self, test_name, status, message=""):
        """테스트 결과 로깅"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)

        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name}: {status}")
        if message:
            print(f"   → {message}")

    # ========== 테스트 1: 기본 함수 검증 ==========
    def test_altitude_parsing(self):
        """ALT 필드 파싱 테스트"""
        test_cases = [
            ("F340", 34000, "Flight Level"),
            ("F400", 40000, "Flight Level"),
            ("S0890", 2919, "Standard Metric"),
            ("A10000", 10000, "Altitude"),
            ("M0500", 1640, "Metric"),
        ]

        all_pass = True
        for alt_str, expected, desc in test_cases:
            result = parse_altitude(alt_str)
            if result is None or abs(result - expected) > 100:  # 오차 범위 100ft
                all_pass = False
                self.log(f"Altitude Parsing ({desc})", "FAIL",
                        f"{alt_str} expected {expected}ft, got {result}ft")
            else:
                self.log(f"Altitude Parsing ({desc})", "PASS",
                        f"{alt_str} → {result}ft")

        return all_pass

    # ========== 테스트 2: 항공기 기종 조회 ==========
    def test_aircraft_profile_lookup(self):
        """항공기 기종 정보 조회 테스트"""
        test_aircraft = ["B38M", "A333", "B787", "A321"]

        all_pass = True
        for aircraft_type in test_aircraft:
            try:
                info = get_aircraft_speed_and_climb(self.db_manager, aircraft_type, "")

                # 결과 검증
                if info['speed_kmh'] > 400 and info['climb_fpm'] > 0:
                    self.log(f"Aircraft Profile ({aircraft_type})", "PASS",
                            f"Speed: {info['speed_kmh']}km/h, "
                            f"Climb: {info['climb_fpm']}fpm, "
                            f"Source: {info['speed_source']}")
                else:
                    all_pass = False
                    self.log(f"Aircraft Profile ({aircraft_type})", "FAIL",
                            f"Invalid values: {info}")
            except Exception as e:
                all_pass = False
                self.log(f"Aircraft Profile ({aircraft_type})", "FAIL", str(e))

        return all_pass

    # ========== 테스트 3: 속도 Fallback 메커니즘 ==========
    def test_speed_fallback(self):
        """CSV SPD → aircraft_profiles → 기본값 Fallback 검증"""
        test_cases = [
            ("B38M", "N0467", "csv", 867),     # CSV SPD 있음 (N0467 = 467 knots × 1.852 ≈ 867 km/h)
            ("B38M", "", "aircraft_profile", 850),  # aircraft_profiles 사용 (B38M = 850 km/h)
            ("UNKNOWN_AC", "", "default", 800),  # 기본값
        ]

        all_pass = True
        for aircraft, spd, expected_source, expected_speed in test_cases:
            info = get_aircraft_speed_and_climb(self.db_manager, aircraft, spd)

            source_match = info['speed_source'] == expected_source
            speed_match = (expected_speed is None) or (abs(info['speed_kmh'] - expected_speed) < 10)  # 오차 범위 10km/h

            if source_match and speed_match:
                self.log(f"Speed Fallback ({aircraft}, {spd or 'empty'})", "PASS",
                        f"Source: {info['speed_source']}, Speed: {info['speed_kmh']}km/h")
            else:
                all_pass = False
                self.log(f"Speed Fallback ({aircraft}, {spd or 'empty'})", "FAIL",
                        f"Expected {expected_source}/{expected_speed}, "
                        f"got {info['speed_source']}/{info['speed_kmh']}")

        return all_pass

    # ========== 테스트 4: 고도 상승 계산 ==========
    def test_climb_calculations(self):
        """두 가지 계산 방식 비교"""
        # 테스트 데이터: 500km 거리, 해수면 출발, FL350 순항
        distance_km = 500
        dep_alt_ft = 0
        cruise_alt_ft = 35000
        climb_fpm = 2000
        speed_kmh = 450

        try:
            # Method A: 단순 선형
            result_a = calculate_climb_time_simple(
                distance_km, dep_alt_ft, cruise_alt_ft, climb_fpm, speed_kmh
            )

            # Method B: EET 역계산
            from datetime import datetime, timedelta
            exit_time = datetime(2025, 12, 26, 11, 0)
            points_data = [
                {'name': 'DEP', 'dist': 0},
                {'name': 'WP1', 'dist': 100},
                {'name': 'WP2', 'dist': 200},
                {'name': 'WP3', 'dist': 300},
                {'name': 'WP4', 'dist': 400},
                {'name': 'WP5', 'dist': 500},
            ]

            result_b = calculate_waypoints_with_eet(
                exit_time, points_data, speed_kmh, dep_alt_ft, cruise_alt_ft, climb_fpm
            )

            # 검증
            if (result_a['climb_time_minutes'] > 0 and
                len(result_b) == len(points_data)):
                self.log("Climb Calculation (Method A)", "PASS",
                        f"Climb time: {result_a['climb_time_minutes']:.1f}min, "
                        f"Total time: {result_a['total_time_minutes']:.1f}min ({result_a['total_time_minutes']/60:.2f}h)")
                self.log("Climb Calculation (Method B)", "PASS",
                        f"Waypoints calculated: {len(result_b)}, "
                        f"Altitudes range: {min(w['altitude_ft'] for w in result_b)}-"
                        f"{max(w['altitude_ft'] for w in result_b)}ft")
                return True
            else:
                self.log("Climb Calculation", "FAIL", "Invalid calculation results")
                return False
        except Exception as e:
            self.log("Climb Calculation", "FAIL", str(e))
            return False

    # ========== 테스트 5: 데이터베이스 스키마 ==========
    def test_database_schema(self):
        """필수 테이블 및 컬럼 검증"""
        required_tables = {
            'flights': ['calculated_speed_kmh', 'speed_source', 'climb_rate_fpm',
                       'cruise_flight_level'],
            'waypoint_times': ['altitude_ft', 'is_climbing'],
            'climb_calculations': ['flight_id', 'simple_linear_time', 'eet_backtrack_time'],
            'aircraft_profiles': ['icao_code', 'default_speed_kmh', 'default_climb_fpm']
        }

        all_pass = True
        for table, columns in required_tables.items():
            try:
                # 테이블 존재 확인
                with self.db_manager.get_connection_context() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"PRAGMA table_info({table})")
                    table_columns = {row[1] for row in cursor.fetchall()}

                    missing = set(columns) - table_columns
                    if missing:
                        all_pass = False
                        self.log(f"Database Schema ({table})", "FAIL",
                                f"Missing columns: {', '.join(missing)}")
                    else:
                        self.log(f"Database Schema ({table})", "PASS",
                                f"All {len(columns)} required columns present")
            except Exception as e:
                all_pass = False
                self.log(f"Database Schema ({table})", "FAIL", str(e))

        return all_pass

    # ========== 테스트 6: API 응답 구조 검증 ==========
    def test_api_response_structure(self):
        """API 응답 구조 검증"""
        # climb_calculations 쿼리 구조 검증
        try:
            with self.db_manager.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM flights LIMIT 1
                """)
                result = cursor.fetchone()

                if result:
                    flight_id = result[0]
                    # climb_calculations 테이블에서 쿼리
                    cursor.execute("""
                        SELECT
                            flight_id, waypoint_name, waypoint_sequence,
                            simple_linear_time, simple_linear_altitude_ft,
                            eet_backtrack_time, eet_backtrack_altitude_ft,
                            time_difference_seconds, altitude_difference_ft
                        FROM climb_calculations
                        WHERE flight_id = ?
                        LIMIT 5
                    """, (flight_id,))

                    rows = cursor.fetchall()
                    if rows:
                        self.log("API Response Structure (climb_calculations)", "PASS",
                                f"Query returned {len(rows)} rows with expected columns")
                    else:
                        self.log("API Response Structure (climb_calculations)", "PASS",
                                f"No climb calculation data yet (expected for fresh DB)")
                else:
                    self.log("API Response Structure", "PASS",
                            "No test data in database yet (expected for fresh DB)")
            return True
        except Exception as e:
            self.log("API Response Structure", "FAIL", str(e))
            return False

    # ========== 테스트 7: 성능 측정 ==========
    def test_performance(self):
        """함수 성능 측정"""
        import timeit

        try:
            # parse_altitude 성능
            alt_time = timeit.timeit(
                lambda: parse_altitude("F340"),
                number=1000
            )

            # get_aircraft_speed_and_climb 성능
            climb_time = timeit.timeit(
                lambda: get_aircraft_speed_and_climb(self.db_manager, "B38M", "N0467"),
                number=100
            )

            self.log("Performance (parse_altitude)", "PASS",
                    f"1000 calls: {alt_time*1000:.2f}ms ({alt_time*1e6/1000:.2f}μs/call)")
            self.log("Performance (get_aircraft_speed_and_climb)", "PASS",
                    f"100 calls: {climb_time*1000:.2f}ms ({climb_time*1e3/100:.2f}ms/call)")

            return True
        except Exception as e:
            self.log("Performance", "FAIL", str(e))
            return False

    # ========== 메인 테스트 실행 ==========
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*70)
        print("🧪 DAY 5 통합 테스트 시작")
        print("="*70 + "\n")

        tests = [
            ("기본 함수 검증", self.test_altitude_parsing),
            ("항공기 기종 조회", self.test_aircraft_profile_lookup),
            ("속도 Fallback", self.test_speed_fallback),
            ("고도 상승 계산", self.test_climb_calculations),
            ("데이터베이스 스키마", self.test_database_schema),
            ("API 응답 구조", self.test_api_response_structure),
            ("성능 측정", self.test_performance),
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
        elapsed = time.time() - self.start_time

        pass_count = sum(1 for r in self.test_results if r['status'] == 'PASS')
        fail_count = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        error_count = sum(1 for r in self.test_results if r['status'] == 'ERROR')

        print("\n" + "="*70)
        print("📊 테스트 결과 요약")
        print("="*70)
        print(f"✅ PASS:  {pass_count}")
        print(f"❌ FAIL:  {fail_count}")
        print(f"⚠️  ERROR: {error_count}")
        print(f"⏱️  소요 시간: {elapsed:.2f}초")
        print(f"📈 성공률: {pass_count / len(self.test_results) * 100:.1f}%")
        print("="*70 + "\n")

        # JSON으로 저장
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed': pass_count,
            'failed': fail_count,
            'errors': error_count,
            'duration_seconds': elapsed,
            'success_rate': pass_count / len(self.test_results) * 100,
            'tests': self.test_results
        }

        report_path = PROJECT_ROOT / "DAY5_INTEGRATION_TEST_RESULTS.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 상세 결과 저장: {report_path}")


if __name__ == '__main__':
    tester = Day5IntegrationTester()
    tester.run_all_tests()
