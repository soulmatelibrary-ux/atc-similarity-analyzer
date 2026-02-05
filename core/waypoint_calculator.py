"""
웨이포인트 시간 계산 모듈 (정밀 버전)
항공 기종과 고도 상승을 정확히 고려한 계산

Features:
- 항공 기종별 최적화된 상승 속도
- ICAO Speed Format 정확한 파싱
- Climb Phase / Cruise Phase 명확한 구분
- EET vs Climb 계산 결과 비교 검증
- 관제시스템 실측 데이터 기반 FIX간 이동시간 룩업 테이블
"""

import math
import logging
import json
import os
from datetime import timedelta

logger = logging.getLogger(__name__)

# ============================================================================
# 1. 항공 기종별 상승 속도 비율
# ============================================================================

AIRCRAFT_CLIMB_SPEED_RATIOS = {
    # 대형 화물/여객기 (상승 느림)
    'B74': 0.65,   # Boeing 747
    'A38': 0.65,   # Airbus A380
    'A34': 0.66,   # Airbus A340

    # 중형 와이드바디 (중간)
    'B77': 0.70,   # Boeing 777
    'B78': 0.72,   # Boeing 787 Dreamliner
    'A33': 0.68,   # Airbus A330
    'A35': 0.70,   # Airbus A350

    # 소형 와이드바디 / 협폭 (상승 빠름)
    'B75': 0.75,   # Boeing 757
    'B76': 0.74,   # Boeing 767
    'A32': 0.73,   # Airbus A320
    'A31': 0.75,   # Airbus A310
    'A30': 0.72,   # Airbus A300

    # 기타
    'CRJ': 0.78,   # Bombardier CRJ
    'E17': 0.76,   # Embraer E170
}

# 기본값
DEFAULT_CLIMB_SPEED_RATIO = 0.70
DEFAULT_CLIMB_RATE_FPM = 1800
DEFAULT_CRUISE_SPEED_KMH = 900

# ============================================================================
# 1.5 FIX간 이동시간 룩업 테이블 (관제시스템 실측 데이터)
# ============================================================================

_FIX_TRAVEL_LOOKUP = None  # 캐시

def _get_fix_travel_lookup():
    """
    FIX간 이동시간 룩업 테이블 로드 (싱글톤 패턴)

    Returns:
        dict: {from_fix: {to_fix: avg_minutes, ...}, ...}
    """
    global _FIX_TRAVEL_LOOKUP

    if _FIX_TRAVEL_LOOKUP is not None:
        return _FIX_TRAVEL_LOOKUP

    # 파일 경로 탐색
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'database', 'fix_travel_times_lookup.json'),
        os.path.join(os.path.dirname(__file__), '..', 'data', 'fix_travel_times_lookup.json'),
        'database/fix_travel_times_lookup.json',
        'fix_travel_times_lookup.json',
    ]

    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    _FIX_TRAVEL_LOOKUP = json.load(f)
                logger.info(f"FIX 이동시간 룩업 테이블 로드 완료: {len(_FIX_TRAVEL_LOOKUP)}개 출발지점 ({abs_path})")
                return _FIX_TRAVEL_LOOKUP
            except Exception as e:
                logger.warning(f"FIX 룩업 테이블 로드 실패: {e}")

    logger.warning("FIX 이동시간 룩업 테이블 파일을 찾을 수 없음")
    _FIX_TRAVEL_LOOKUP = {}
    return _FIX_TRAVEL_LOOKUP


def _reload_fix_travel_lookup():
    """
    FIX 이동시간 룩업 테이블 캐시를 강제로 다시 로드
    JSON 파일이 업데이트된 후 호출하여 메모리 캐시 갱신
    """
    global _FIX_TRAVEL_LOOKUP
    _FIX_TRAVEL_LOOKUP = None
    return _get_fix_travel_lookup()


def get_fix_travel_time(from_fix, to_fix):
    """
    두 FIX 간의 실측 기반 이동시간 조회

    Args:
        from_fix: 출발 FIX 이름
        to_fix: 도착 FIX 이름

    Returns:
        float or None: 이동시간 (분), 데이터 없으면 None
    """
    lookup = _get_fix_travel_lookup()

    if from_fix in lookup and to_fix in lookup[from_fix]:
        return lookup[from_fix][to_fix]

    return None


# ============================================================================
# 2. ICAO Speed Format 파싱
# ============================================================================

def convert_icao_speed(speed_str, altitude_fl=None):
    """
    ICAO Speed Format 변환

    입력 형식:
    - K0900: Knots (900 knots)
    - N0500: Knots (500 knots)
    - M0.80: Mach (Mach 0.80)

    Args:
        speed_str: ICAO format speed string
        altitude_fl: 고도 (FL 단위), Mach 변환 시 필요

    Returns:
        float: km/h 단위의 속도, 또는 None (파싱 실패)
    """
    if not speed_str:
        return None

    speed_str = str(speed_str).strip().upper()

    try:
        # Knots 형식: K0900, N0500
        if speed_str[0] in ['K', 'N']:
            knots = int(speed_str[1:])
            kmh = knots * 1.852  # 1 knot = 1.852 km/h
            logger.debug(f"Speed parse: {speed_str} → {knots} knots → {kmh:.1f} km/h")
            return kmh

        # Mach 형식: M0.80, M0.85
        elif speed_str[0] == 'M':
            mach = float(speed_str[1:])

            # ISA 표준 대기에서 음속 계산
            if altitude_fl:
                # 고도(FL) → 온도(°C)
                # ISA: 약 -2°C/1000ft, sea level 15°C
                # FL = Flight Level (100 ft 단위)
                altitude_ft = altitude_fl * 100
                temp_celsius = 15 - (altitude_ft / 1000 * 2.0)
            else:
                # 기본값: sea level
                temp_celsius = 15

            # 음속 계산: a = 38.967 * sqrt(T_K) [m/s]
            # 또는: a = 661.5 * sqrt(T_K / 288.15) [knots]
            temp_kelvin = temp_celsius + 273.15
            if temp_kelvin <= 0:
                # 불가능한 온도, 기본값 사용
                speed_of_sound_knots = 661.5
            else:
                speed_of_sound_knots = 661.5 * math.sqrt(temp_kelvin / 288.15)

            speed_kmh = mach * speed_of_sound_knots * 1.852

            logger.debug(
                f"Speed parse: {speed_str} (FL{altitude_fl}, {temp_celsius:.1f}°C, {temp_kelvin:.1f}K) → "
                f"Mach {mach} → {speed_kmh:.1f} km/h (a={speed_of_sound_knots:.1f} knots)"
            )
            return speed_kmh

        else:
            logger.warning(f"Unknown speed format: {speed_str}")
            return None

    except (ValueError, IndexError) as e:
        logger.warning(f"Speed parsing error for '{speed_str}': {e}")
        return None


# ============================================================================
# 3. 거리 계산
# ============================================================================

def haversine(lat1, lon1, lat2, lon2):
    """
    Haversine 공식으로 두 점 사이의 거리 계산

    Args:
        lat1, lon1: 출발점 (도 단위)
        lat2, lon2: 도착점 (도 단위)

    Returns:
        float: 거리 (km)
    """
    R = 6371  # 지구 반지름 (km)

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))

    return R * c


# ============================================================================
# 4. 웨이포인트 시간 계산
# ============================================================================

class WaypointCalculator:
    """
    정밀한 웨이포인트 도달 시간 계산기
    """

    def __init__(self, aircraft_type, cruise_speed_kmh=None, climb_rate_fpm=None):
        """
        초기화

        Args:
            aircraft_type: ICAO aircraft code (B77L, B744 등)
            cruise_speed_kmh: 순항 속도 (km/h)
            climb_rate_fpm: 상승률 (feet/minute)
        """
        self.aircraft_type = aircraft_type
        self.cruise_speed_kmh = cruise_speed_kmh or DEFAULT_CRUISE_SPEED_KMH
        self.climb_rate_fpm = climb_rate_fpm or DEFAULT_CLIMB_RATE_FPM

        # 항공 기종에서 prefix 추출 (B777 → B77)
        prefix = (aircraft_type or 'XXX')[:3].upper()
        self.climb_speed_ratio = AIRCRAFT_CLIMB_SPEED_RATIOS.get(prefix, DEFAULT_CLIMB_SPEED_RATIO)
        self.climb_speed_kmh = self.cruise_speed_kmh * self.climb_speed_ratio

        logger.info(
            f"WaypointCalculator initialized: {aircraft_type} "
            f"(cruise={self.cruise_speed_kmh} km/h, climb_rate={self.climb_rate_fpm} fpm, "
            f"climb_speed={self.climb_speed_kmh:.1f} km/h)"
        )

    def calculate_segment_time(self, segment_dist_km, current_alt_ft, target_alt_ft):
        """
        특정 구간의 비행 시간 계산

        Args:
            segment_dist_km: 구간 거리 (km)
            current_alt_ft: 현재 고도 (feet)
            target_alt_ft: 목표 고도 (feet)

        Returns:
            dict: {
                'time_seconds': 비행 시간 (초),
                'final_altitude_ft': 구간 끝의 고도 (feet),
                'phase': 'climbing' | 'climb_and_cruise' | 'cruise',
                'details': {...}
            }
        """
        if segment_dist_km <= 0:
            return {
                'time_seconds': 0,
                'final_altitude_ft': current_alt_ft,
                'phase': 'zero_distance',
                'details': {}
            }

        # 이미 순항 고도에 도달한 경우
        if current_alt_ft >= target_alt_ft:
            time_seconds = (segment_dist_km / self.cruise_speed_kmh) * 3600
            return {
                'time_seconds': time_seconds,
                'final_altitude_ft': current_alt_ft,
                'phase': 'cruise',
                'details': {
                    'cruise_dist_km': segment_dist_km,
                    'cruise_speed_kmh': self.cruise_speed_kmh,
                    'time_minutes': time_seconds / 60
                }
            }

        # 상승이 필요한 경우
        altitude_gain_needed = target_alt_ft - current_alt_ft
        time_to_toc_minutes = altitude_gain_needed / self.climb_rate_fpm
        distance_to_toc_km = (time_to_toc_minutes / 60) * self.climb_speed_kmh

        if distance_to_toc_km < segment_dist_km:
            # 이 구간에서 순항 고도에 도달
            climb_time_seconds = time_to_toc_minutes * 60
            cruise_dist_km = segment_dist_km - distance_to_toc_km
            cruise_time_seconds = (cruise_dist_km / self.cruise_speed_kmh) * 3600
            total_time_seconds = climb_time_seconds + cruise_time_seconds

            return {
                'time_seconds': total_time_seconds,
                'final_altitude_ft': target_alt_ft,
                'phase': 'climb_and_cruise',
                'details': {
                    'climb_dist_km': distance_to_toc_km,
                    'climb_speed_kmh': self.climb_speed_kmh,
                    'climb_time_minutes': time_to_toc_minutes,
                    'cruise_dist_km': cruise_dist_km,
                    'cruise_speed_kmh': self.cruise_speed_kmh,
                    'cruise_time_minutes': cruise_time_seconds / 60,
                    'total_time_minutes': total_time_seconds / 60
                }
            }
        else:
            # 이 구간에서는 아직 순항 고도 미도달
            segment_time_seconds = (segment_dist_km / self.climb_speed_kmh) * 3600
            altitude_gained = (segment_time_seconds / 60) * self.climb_rate_fpm
            final_alt = current_alt_ft + altitude_gained

            return {
                'time_seconds': segment_time_seconds,
                'final_altitude_ft': final_alt,
                'phase': 'climbing',
                'details': {
                    'climb_dist_km': segment_dist_km,
                    'climb_speed_kmh': self.climb_speed_kmh,
                    'time_minutes': segment_time_seconds / 60,
                    'altitude_gain_ft': altitude_gained,
                    'final_altitude_ft': final_alt
                }
            }

    def calculate_first_waypoint_time(self, dept_time, dept_airport_coords, first_waypoint_coords,
                                     cruise_altitude_ft):
        """
        Departure 공항에서 첫 웨이포인트까지의 도달 시간 계산

        Args:
            dept_time: 출발 시간 (datetime) - None이면 상대 시간 반환
            dept_airport_coords: 출발 공항 좌표 (tuple: lat, lon)
            first_waypoint_coords: 첫 웨이포인트 좌표 (tuple: lat, lon)
            cruise_altitude_ft: 순항 고도 (feet)

        Returns:
            dict: {
                'time': 첫 웨이포인트 도달 시간 (datetime) - dept_time이 None이면 None
                'time_delta': 출발에서 경과 시간 (timedelta),
                'distance_km': 거리 (km),
                'phase': 'climbing' | 'climb_and_cruise',
                'details': {...}
            }
        """
        # 거리 계산
        distance_km = haversine(
            dept_airport_coords[0], dept_airport_coords[1],
            first_waypoint_coords[0], first_waypoint_coords[1]
        )

        # 시간 계산 (출발점 고도 = 0)
        result = self.calculate_segment_time(distance_km, 0, cruise_altitude_ft)

        time_delta = timedelta(seconds=result['time_seconds'])
        arrival_time = dept_time + time_delta if dept_time else None

        return {
            'time': arrival_time,
            'time_delta': time_delta,
            'distance_km': distance_km,
            'phase': result['phase'],
            'details': {
                **result['details'],
                'aircraft_type': self.aircraft_type,
                'climb_speed_ratio': self.climb_speed_ratio,
                'cruise_altitude_ft': cruise_altitude_ft,
                'climb_rate_fpm': self.climb_rate_fpm
            }
        }

    def calculate_route_times(self, dept_time, waypoints, cruise_altitude_ft, use_lookup=True):
        """
        경로의 모든 웨이포인트 도달 시간 계산

        Args:
            dept_time: 출발 시간
            waypoints: 웨이포인트 리스트
                [
                    {'name': 'RKSI', 'lat': 37.46, 'lon': 126.44},  # Departure (첫 번째)
                    {'name': 'BEDES', 'lat': 36.15, 'lon': 126.81},
                    {'name': 'SADLI', 'lat': 36.14, 'lon': 127.24},
                    ...
                ]
            cruise_altitude_ft: 순항 고도
            use_lookup: 관제시스템 실측 룩업 테이블 사용 여부 (기본: True)

        Returns:
            list: 각 웨이포인트의 도달 시간과 상세 정보
        """
        results = []
        current_time = dept_time
        current_altitude_ft = 0
        lookup_hits = 0
        lookup_misses = 0

        for i, wp in enumerate(waypoints):
            if i == 0:
                # 첫 번째는 출발 공항
                results.append({
                    'sequence': 0,
                    'name': wp['name'],
                    'lat': wp['lat'],
                    'lon': wp['lon'],
                    'time': current_time,
                    'altitude_ft': 0,
                    'phase': 'departure',
                    'cumulative_distance_km': 0,
                    'time_source': 'departure'
                })
            else:
                # 이전 웨이포인트에서 현재 웨이포인트까지의 거리
                prev_wp = waypoints[i - 1]
                segment_dist = haversine(
                    prev_wp['lat'], prev_wp['lon'],
                    wp['lat'], wp['lon']
                )

                # 1순위: 관제시스템 실측 데이터 룩업 테이블
                lookup_time_minutes = None
                time_source = 'calculated'

                if use_lookup:
                    lookup_time_minutes = get_fix_travel_time(prev_wp['name'], wp['name'])

                if lookup_time_minutes is not None:
                    # 룩업 테이블 히트: 실측 데이터 사용
                    segment_time_seconds = lookup_time_minutes * 60
                    time_source = 'lookup'
                    lookup_hits += 1

                    # 고도는 거리 기반으로 추정
                    segment_result = self.calculate_segment_time(
                        segment_dist, current_altitude_ft, cruise_altitude_ft
                    )
                    current_altitude_ft = segment_result['final_altitude_ft']
                    phase = segment_result['phase']
                    details = {
                        **segment_result['details'],
                        'lookup_time_minutes': lookup_time_minutes,
                        'calculated_time_minutes': segment_result['time_seconds'] / 60,
                        'time_diff_minutes': lookup_time_minutes - (segment_result['time_seconds'] / 60)
                    }
                else:
                    # 2순위: 기존 거리/속도 기반 계산 (폴백)
                    segment_result = self.calculate_segment_time(
                        segment_dist, current_altitude_ft, cruise_altitude_ft
                    )
                    segment_time_seconds = segment_result['time_seconds']
                    current_altitude_ft = segment_result['final_altitude_ft']
                    phase = segment_result['phase']
                    details = segment_result['details']
                    lookup_misses += 1

                current_time += timedelta(seconds=segment_time_seconds)

                # 누적 거리
                cumulative_dist = (
                    results[-1].get('cumulative_distance_km', 0) + segment_dist
                )

                results.append({
                    'sequence': i,
                    'name': wp['name'],
                    'lat': wp['lat'],
                    'lon': wp['lon'],
                    'time': current_time,
                    'altitude_ft': current_altitude_ft,
                    'phase': phase,
                    'segment_distance_km': segment_dist,
                    'segment_time_minutes': segment_time_seconds / 60,
                    'cumulative_distance_km': cumulative_dist,
                    'time_source': time_source,
                    'details': details
                })

        # 룩업 통계 로깅
        if use_lookup and (lookup_hits > 0 or lookup_misses > 0):
            total = lookup_hits + lookup_misses
            hit_rate = (lookup_hits / total * 100) if total > 0 else 0
            logger.debug(
                f"FIX 룩업 통계: {lookup_hits}/{total} 히트 ({hit_rate:.1f}%), "
                f"{lookup_misses}개 폴백 계산"
            )

        return results


# ============================================================================
# 5. 유틸리티 함수
# ============================================================================

def format_waypoint_time(waypoint_time):
    """웨이포인트 도달 시간을 HH:MM 형식으로 포맷"""
    if not waypoint_time:
        return 'N/A'
    if isinstance(waypoint_time, timedelta):
        total_seconds = int(waypoint_time.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return waypoint_time.strftime('%H:%M') if hasattr(waypoint_time, 'strftime') else str(waypoint_time)


def validate_climb_vs_eet(climb_time_seconds, eet_time_seconds, threshold_percent=20):
    """
    Climb 계산과 EET 계산 결과 비교

    Args:
        climb_time_seconds: Climb 계산 결과 (초)
        eet_time_seconds: EET 기반 계산 결과 (초)
        threshold_percent: 경고 임계값 (%)

    Returns:
        dict: {
            'difference_percent': 차이 (%)
            'is_suspicious': 차이가 임계값 초과 여부
            'recommendation': 권장사항
        }
    """
    if not eet_time_seconds or eet_time_seconds == 0:
        return {
            'difference_percent': None,
            'is_suspicious': False,
            'recommendation': 'EET data not available'
        }

    diff_percent = abs(climb_time_seconds - eet_time_seconds) / eet_time_seconds * 100

    return {
        'difference_percent': diff_percent,
        'is_suspicious': diff_percent > threshold_percent,
        'recommendation': (
            f"Climb: {climb_time_seconds:.0f}s, EET: {eet_time_seconds:.0f}s, "
            f"Diff: {diff_percent:.1f}% "
            f"{'⚠️ Review needed' if diff_percent > threshold_percent else '✓ OK'}"
        )
    }


if __name__ == '__main__':
    # 테스트 예시
    logging.basicConfig(level=logging.DEBUG)

    # Test Case 1: B77L (인천 출발)
    print("\n=== Test Case 1: B77L from Incheon ===")
    calc = WaypointCalculator('B77L', cruise_speed_kmh=905, climb_rate_fpm=2000)

    # 출발: RKSI (인천)
    # 첫 지점: BEDES (Yellow Sea)
    rksi_coords = (37.4606, 126.4407)
    bedes_coords = (36.1511, 126.8119)
    cruise_alt_ft = 37000

    result = calc.calculate_first_waypoint_time(
        dept_time=None,  # None이면 상대 시간으로 계산
        dept_airport_coords=rksi_coords,
        first_waypoint_coords=bedes_coords,
        cruise_altitude_ft=cruise_alt_ft
    )

    print(f"Distance: {result['distance_km']:.1f} km")
    print(f"Phase: {result['phase']}")
    print(f"Time: {format_waypoint_time(result['time_delta'])}")
    print(f"Details: {result['details']}")
