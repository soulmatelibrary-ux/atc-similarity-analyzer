import pandas as pd
import math
import sys
import os
from datetime import datetime, timedelta
import re
from pathlib import Path

DEFAULT_SPEED_KMH = 820
DEFAULT_CLIMB_FPM = 1800
DEFAULT_CRUISE_ALTITUDE_FT = 35000

# 기본 공항 좌표 (웨이포인트 계산기용)
AIRPORT_COORDS = {
    'RKSI': (37.4606, 126.4407), 'RKSS': (37.5583, 126.7906),
    'RKPC': (33.5113, 126.4930), 'RKPK': (35.1795, 128.9429),
    'RKTU': (36.7167, 127.5000), 'RKTN': (35.8940, 128.6590),
    'RKJB': (34.9914, 126.3828), 'RKNY': (38.0613, 128.6693),
    'RKTL': (36.7683, 129.4140), 'RKJK': (35.9038, 126.6158),
    'RKSM': (37.4368, 127.1127), 'RKSG': (37.2405, 127.0094),
    'RKJY': (34.8433, 127.6171), 'RKPE': (35.1402, 128.6865),
    'RKPD': (33.3958, 126.7118), 'RKSO': (37.0911, 127.0309)
}

# ============================================================================
CURRENT_FILE = Path(__file__).resolve()
CORE_DIR = CURRENT_FILE.parent
PROJECT_ROOT = CORE_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger import setup_logger
from core import route_converter
from core.waypoint_calculator import WaypointCalculator, convert_icao_speed

logger = setup_logger(__name__)


def haversine(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two lat/lon points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def parse_eet(eet_str, target_code):
    """
    Parse EET string like 'RJJJ0114 RCAA0131' to find duration for target_code.
    Returns timedelta or None.
    """
    if not isinstance(eet_str, str):
        return None

    pattern = rf"{target_code}(\d{{4}})"
    match = re.search(pattern, eet_str)
    if match:
        hhmm = match.group(1)
        hours = int(hhmm[:2])
        mins = int(hhmm[2:])
        return timedelta(hours=hours, minutes=mins)
    return None

def parse_speed(speed_str):
    """Parse ICAO speed (KXXXX/NXXXX) and return km/h, or None if invalid."""
    if not isinstance(speed_str, str) or len(speed_str) < 2:
        return None

    unit = speed_str[0].upper()
    try:
        val = int(speed_str[1:])
        if unit == 'K':
            return val
        if unit == 'N':
            return val * 1.852  # Knots to km/h
        if unit == 'M':
            return (val / 100.0) * 1235  # Approximate Mach conversion
    except Exception:
        return None
    return None

def extract_dof_from_info_cn(info_cn_str):
    """
    Extract DOF (Date of Flight) from INFO_CN field.
    Format: DOF/YYMMDD
    Returns datetime.date object or None
    """
    if not isinstance(info_cn_str, str):
        return None

    pattern = r'DOF/(\d{6})'
    match = re.search(pattern, info_cn_str)
    if match:
        dof_str = match.group(1)
        try:
            yy = int(dof_str[:2])
            mm = int(dof_str[2:4])
            dd = int(dof_str[4:6])
            # Assume 20XX for years 00-99
            yyyy = 2000 + yy
            return datetime(yyyy, mm, dd).date()
        except:
            pass
    return None

def extract_eet_from_info_cn(info_cn_str):
    """
    Extract EET string from INFO_CN field.
    Format: EET/WAYPOINT1TIME1 WAYPOINT2TIME2 ...
    Returns EET string or empty string
    """
    if not isinstance(info_cn_str, str):
        return ''

    pattern = r'EET/([A-Z0-9\s]+?)(?:SEL/|CODE/|OPR/|RMK/|$)'
    match = re.search(pattern, info_cn_str)
    if match:
        eet_str = match.group(1).strip()
        return eet_str
    return ''

def parse_eobt(eobt_str):
    """
    Parse EOBT string to time.
    Handles formats: HH:MM, HHMM, or empty
    Returns datetime.time object (default 00:00 if empty/invalid)
    """
    if not isinstance(eobt_str, str) or eobt_str.strip() == '':
        return datetime.strptime('00:00', '%H:%M').time()

    eobt_str = eobt_str.strip()
    try:
        # Try HH:MM format
        if ':' in eobt_str:
            return datetime.strptime(eobt_str, '%H:%M').time()
        # Try HHMM format
        elif len(eobt_str) == 4:
            return datetime.strptime(eobt_str, '%H%M').time()
        else:
            return datetime.strptime('00:00', '%H:%M').time()
    except:
        return datetime.strptime('00:00', '%H:%M').time()

def calculate_trajectory(flight_data, coord_map, sectors, enroute_df, fix_col='FIXPNT'):
    """Calculate waypoint and sector times for a single flight."""

    try:
        callsign = str(flight_data.get('callsign', 'UNKNOWN'))
        dept = str(flight_data.get('dept', '') or '')
        dest = str(flight_data.get('dest', '') or '')
        route = str(flight_data.get('route', '') or '')
        speed_str = flight_data.get('speed', '')
        altitude_raw = flight_data.get('altitude', '')
        altitude_str = '' if altitude_raw is None else str(altitude_raw)
        aircraft_type = str(flight_data.get('aircraft_type', '') or '').upper()
        aircraft_profile = flight_data.get('aircraft_profile')
        eobd_str = str(flight_data.get('eobd', '') or '')
        eobt_str = str(flight_data.get('eobt', '') or '')
        eet_str = str(flight_data.get('eet', '') or '')
        info_cn = str(flight_data.get('info_cn', '') or '')

        profile_speed = profile_climb = profile_ceiling_ft = None
        if aircraft_profile:
            profile_speed = aircraft_profile.get('default_speed_kmh')
            if not profile_speed and aircraft_profile.get('default_speed_knots'):
                profile_speed = round(aircraft_profile['default_speed_knots'] * 1.852)
            profile_climb = aircraft_profile.get('default_climb_fpm')
            ceiling_fl = aircraft_profile.get('default_ceiling_fl')
            if ceiling_fl:
                profile_ceiling_ft = ceiling_fl * 100

        try:
            dof_date = datetime.strptime(eobd_str, '%Y-%m-%d').date()
        except Exception:
            dof_date = datetime.now().date()

        eobt_time = parse_eobt(eobt_str)
        base_time = datetime.combine(dof_date, eobt_time)

        is_dept = dept.startswith('RK')
        is_arr = dest.startswith('RK')

        speed_kmh = None
        if speed_str:
            try:
                alt_fl = None
                if altitude_str:
                    alt_match = re.search(r'(\d+)', altitude_str)
                    if alt_match:
                        alt_val = int(alt_match.group(1))
                        alt_fl = alt_val if alt_val > 500 else None
                speed_kmh = convert_icao_speed(str(speed_str), alt_fl)
            except Exception as convert_err:
                logger.debug(f"ICAO speed conversion failed: {convert_err}, falling back to legacy")
                speed_kmh = parse_speed(str(speed_str))

        if speed_kmh is not None and speed_kmh <= 0:
            speed_kmh = None
        if not speed_kmh and profile_speed:
            speed_kmh = profile_speed
        if not speed_kmh:
            speed_kmh = DEFAULT_SPEED_KMH

        logger.debug(f"Speed: {speed_str} → {speed_kmh:.1f} km/h")

        altitude_feet = 0
        alt_match = re.search(r'(\d+)', altitude_str)
        if alt_match:
            alt_val = int(alt_match.group(1))
            altitude_feet = alt_val if alt_val > 1000 else alt_val * 100
        if altitude_feet <= 0 and profile_ceiling_ft:
            altitude_feet = profile_ceiling_ft
        if altitude_feet <= 0:
            altitude_feet = DEFAULT_CRUISE_ALTITUDE_FT

        climb_rate_fpm = profile_climb if profile_climb and profile_climb > 0 else DEFAULT_CLIMB_FPM

        def estimate_climb_timedelta(target_feet, climb_rate):
            if target_feet <= 0:
                return timedelta(minutes=8)
            climb_rate = climb_rate or DEFAULT_CLIMB_FPM
            minutes = max(6, target_feet / climb_rate)
            return timedelta(minutes=minutes)

        expanded_points = route_converter.expand_route(enroute_df, fix_col, str(route))
        korea_points = [p for p in expanded_points if p in coord_map]

        if not korea_points:
            return {
                'status': 'error',
                'message': '한국 내 경유 지점을 찾을 수 없습니다. (Incheon FIR 경계 밖이거나 데이터 부족)',
                'waypoints': [],
                'sectors': []
            }

        points_data = []
        for i, pt in enumerate(korea_points):
            lat, lon = coord_map[pt]
            dist = 0
            if i > 0:
                prev_lat, prev_lon = points_data[-1]['lat'], points_data[-1]['lon']
                dist = haversine(prev_lat, prev_lon, lat, lon)

            points_data.append({
                'name': pt,
                'lat': lat,
                'lon': lon,
                'dist': dist,
                'sector': find_sector(lat, lon, sectors)
            })

        rkrr_duration = parse_eet(eet_str, 'RKRR')
        if not rkrr_duration and 'RKRR' in info_cn:
            info_cn_eet = extract_eet_from_info_cn(info_cn)
            rkrr_duration = parse_eet(info_cn_eet, 'RKRR')

        waypoints_result = []

        if is_dept:
            match = re.search(r'([A-Z]{4})(\d{4})', str(eet_str))
            if not match and info_cn:
                info_cn_eet = extract_eet_from_info_cn(info_cn)
                match = re.search(r'([A-Z]{4})(\d{4})', str(info_cn_eet))

            if match:
                hhmm = match.group(2)
                exit_delta = timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[2:]))
                exit_time = base_time + exit_delta

                if points_data:
                    try:
                        calc = WaypointCalculator(
                            aircraft_type=aircraft_type,
                            cruise_speed_kmh=speed_kmh,
                            climb_rate_fpm=climb_rate_fpm
                        )

                        dept_coord = coord_map.get(dept) or AIRPORT_COORDS.get(dept)
                        waypoints_for_calc = []
                        if dept_coord:
                            waypoints_for_calc.append({'name': dept, 'lat': dept_coord[0], 'lon': dept_coord[1]})
                        waypoints_for_calc.extend({'name': p['name'], 'lat': p['lat'], 'lon': p['lon']}
                                                  for p in points_data)
                        calc_offset = 1 if dept_coord else 0

                        route_times = calc.calculate_route_times(
                            dept_time=base_time,
                            waypoints=waypoints_for_calc,
                            cruise_altitude_ft=altitude_feet
                        )

                        route_results = route_times[calc_offset:] if calc_offset else route_times
                        if not route_results:
                            raise ValueError('Insufficient route time results')

                        first_calc_time = route_results[0]['time']
                        first_wp_time = min(first_calc_time, exit_time)

                        remaining_calc_seconds = max(
                            0,
                            (route_results[-1]['time'] - first_calc_time).total_seconds()
                        )
                        remaining_eet_seconds = max(0, (exit_time - first_wp_time).total_seconds())
                        scale = remaining_eet_seconds / remaining_calc_seconds if remaining_calc_seconds > 0 else 1.0

                        for idx_pts, calc_result in enumerate(route_results):
                            if idx_pts >= len(points_data):
                                break

                            if idx_pts == 0:
                                points_data[idx_pts]['time'] = first_wp_time
                            else:
                                elapsed_calc = (calc_result['time'] - first_calc_time).total_seconds()
                                adj_time = first_wp_time + timedelta(seconds=elapsed_calc * scale)
                                if idx_pts == len(points_data) - 1:
                                    adj_time = exit_time
                                points_data[idx_pts]['time'] = adj_time

                            points_data[idx_pts]['calc_phase'] = calc_result.get('phase')
                            points_data[idx_pts]['calc_altitude'] = calc_result.get('altitude_ft')

                        if len(points_data) > len(route_results):
                            current_time = points_data[min(len(route_results)-1, len(points_data)-1)]['time']
                            for j in range(len(route_results), len(points_data)):
                                current_time += timedelta(hours=(points_data[j]['dist']/speed_kmh))
                                points_data[j]['time'] = current_time

                    except Exception as calc_err:
                        logger.warning(
                            f"EET-based calculator alignment failed ({calc_err}); falling back to climb estimate"
                        )

                        climb_time = estimate_climb_timedelta(altitude_feet, climb_rate_fpm)
                        first_wp_time = base_time + climb_time
                        if first_wp_time >= exit_time:
                            first_wp_time = exit_time
                        points_data[0]['time'] = first_wp_time

                        remaining_time = exit_time - first_wp_time
                        remaining_seconds = max(0, remaining_time.total_seconds())
                        total_remaining_dist = sum(p['dist'] for p in points_data[1:])

                        if remaining_seconds > 0 and total_remaining_dist > 0:
                            current_time = first_wp_time
                            for i in range(1, len(points_data)):
                                segment_dist = points_data[i]['dist']
                                if segment_dist <= 0:
                                    segment_seconds = 0
                                else:
                                    ratio = segment_dist / total_remaining_dist
                                    segment_seconds = remaining_seconds * ratio
                                current_time = current_time + timedelta(seconds=segment_seconds)
                                points_data[i]['time'] = current_time
                            points_data[-1]['time'] = exit_time
                        else:
                            current_time = first_wp_time
                            for i in range(1, len(points_data)):
                                current_time += timedelta(hours=(points_data[i]['dist'] / speed_kmh))
                                points_data[i]['time'] = current_time
            else:
                logger.info(f"Using optimized waypoint calculator (v2.2) for {aircraft_type}")

                try:
                    calc = WaypointCalculator(
                        aircraft_type=aircraft_type,
                        cruise_speed_kmh=speed_kmh,
                        climb_rate_fpm=climb_rate_fpm
                    )

                    dept_coord = coord_map.get(dept) or AIRPORT_COORDS.get(dept)
                    waypoints_for_calc = []
                    if dept_coord:
                        waypoints_for_calc.append({'name': dept, 'lat': dept_coord[0], 'lon': dept_coord[1]})
                    waypoints_for_calc.extend({'name': p['name'], 'lat': p['lat'], 'lon': p['lon']}
                                              for p in points_data)
                    calc_offset = 1 if dept_coord else 0

                    route_times = calc.calculate_route_times(
                        dept_time=base_time,
                        waypoints=waypoints_for_calc,
                        cruise_altitude_ft=altitude_feet
                    )

                    route_results = route_times[calc_offset:] if calc_offset else route_times

                    for idx_pts, calc_result in enumerate(route_results):
                        if idx_pts >= len(points_data):
                            break
                        points_data[idx_pts]['time'] = calc_result['time']
                        points_data[idx_pts]['calc_phase'] = calc_result.get('phase')
                        points_data[idx_pts]['calc_altitude'] = calc_result.get('altitude_ft')

                    logger.debug(f"✓ Optimized calculation completed for {len(route_times)} waypoints")

                except Exception as e:
                    logger.warning(f"Optimized calculator failed ({e}), falling back to v2.1 logic")

                    current_altitude_ft = 0.0
                    target_altitude_ft = float(altitude_feet)
                    current_time = base_time
                    climb_speed_kmh = speed_kmh * 0.7 if speed_kmh else 500
                    climb_rate = climb_rate_fpm

                    if points_data:
                        first_wp = points_data[0]
                        dept_loc = AIRPORT_COORDS.get(dept)
                        dist_to_wp1 = (
                            haversine(dept_loc[0], dept_loc[1], first_wp['lat'], first_wp['lon'])
                            if dept_loc else 50.0
                        )
                        segment_dist = dist_to_wp1
                        segment_time_seconds = 0

                        if current_altitude_ft < target_altitude_ft:
                            needed_alt = target_altitude_ft - current_altitude_ft
                            time_to_toc_min = needed_alt / climb_rate if climb_rate > 0 else 999
                            dist_to_toc = (time_to_toc_min / 60) * climb_speed_kmh

                            if dist_to_toc <= segment_dist:
                                segment_time_seconds = (
                                    (time_to_toc_min * 60) + ((segment_dist - dist_to_toc) / speed_kmh * 3600)
                                )
                                current_altitude_ft = target_altitude_ft
                            else:
                                segment_time_seconds = (segment_dist / climb_speed_kmh) * 3600
                                current_altitude_ft += (segment_time_seconds / 60) * climb_rate
                        else:
                            segment_time_seconds = (segment_dist / speed_kmh) * 3600

                        current_time += timedelta(seconds=segment_time_seconds)
                        points_data[0]['time'] = current_time

                        for i, p in enumerate(points_data[1:], 1):
                            segment_dist = p['dist']
                            segment_time_seconds = 0

                            if current_altitude_ft < target_altitude_ft:
                                needed_alt = target_altitude_ft - current_altitude_ft
                                time_to_toc_min = needed_alt / climb_rate if climb_rate > 0 else 999
                                dist_to_toc = (time_to_toc_min / 60) * climb_speed_kmh

                                if dist_to_toc <= segment_dist:
                                    segment_time_seconds = (
                                        (time_to_toc_min * 60) + ((segment_dist - dist_to_toc) / speed_kmh * 3600)
                                    )
                                    current_altitude_ft = target_altitude_ft
                                else:
                                    segment_time_seconds = (segment_dist / climb_speed_kmh) * 3600
                                    current_altitude_ft += (segment_time_seconds / 60) * climb_rate
                            else:
                                segment_time_seconds = (segment_dist / speed_kmh) * 3600

                            current_time += timedelta(seconds=segment_time_seconds)
                            p['time'] = current_time
        elif is_arr or rkrr_duration:
            entry_time = base_time + (rkrr_duration if rkrr_duration else timedelta(0))
            current_time = entry_time
            for i, p in enumerate(points_data):
                if i > 0:
                    current_time += timedelta(hours=(p['dist'] / speed_kmh))
                p['time'] = current_time
        else:
            current_time = base_time
            for i, p in enumerate(points_data):
                if i > 0:
                    current_time += timedelta(hours=(p['dist'] / speed_kmh))
                p['time'] = current_time

        for p in points_data:
            waypoints_result.append({
                'name': p['name'],
                'lat': p['lat'],
                'lon': p['lon'],
                'time': p['time'].strftime('%H:%M') if 'time' in p else 'N/A'
            })

        sector_usage = []
        if points_data and 'time' in points_data[0]:
            current_sector = None
            sector_enter_time = None
            sector_exit_time = None

            for p in points_data:
                sec = p['sector']
                time = p['time']

                if sec != current_sector:
                    if current_sector is not None:
                        sector_usage.append({
                            'name': current_sector,
                            'entry': sector_enter_time.strftime('%H:%M'),
                            'exit': sector_exit_time.strftime('%H:%M')
                        })
                    if sec is not None:
                        current_sector = sec
                        sector_enter_time = time
                        sector_exit_time = time
                else:
                    if sec is not None:
                        sector_exit_time = time

            if current_sector is not None:
                sector_usage.append({
                    'name': current_sector,
                    'entry': sector_enter_time.strftime('%H:%M'),
                    'exit': sector_exit_time.strftime('%H:%M')
                })

        return {
            'status': 'success',
            'waypoints': waypoints_result,
            'sectors': sector_usage,
            'route_expansion': ' '.join(korea_points)
        }

    except Exception as e:
        logger.error(f"Trajectory calculation error: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

def process_flight_plans(db_manager=None):
    """
    항공편 계획 처리 및 DB 저장

    Args:
        db_manager: DatabaseManager 인스턴스 (선택사항)
    """
    # 1. Load Reference Data
    # 기본 경로 설정
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    enroute_path = os.path.join(base_dir, 'data', 'enroute', 'enroute.xlsx')
    sector_path = os.path.join(base_dir, 'data', 'sectors', 'sector1.xlsx')

    # 절대 경로 존재 확인
    if not os.path.exists(enroute_path):
        print(f"Warning: enroute.xlsx not found at {enroute_path}")
        return

    if not os.path.exists(sector_path):
        print(f"Warning: sector1.xlsx not found at {sector_path}")
        return

    enroute_df, fix_col = route_converter.load_data(enroute_path)

    # Create coordinate map: FIX -> (LAT, LON)
    # Handle duplicates by taking first found (or average? First is safer)
    coord_map = {}
    for _, row in enroute_df.iterrows():
        fix = row[fix_col]
        if fix not in coord_map:
            coord_map[fix] = (row['LAT'], row['LON'])

    # 2. Load Flight Plan from Database
    if not db_manager:
        print("Warning: db_manager not provided")
        return

    try:
        flights = db_manager.get_all_flights()
        if not flights:
            print("No flights in database")
            return

        # DB 결과를 DataFrame으로 변환
        flights_list = [dict(f) for f in flights]
        fp_df = pd.DataFrame(flights_list)

        # 컬럼명을 대문자로 정규화
        fp_df.columns = [col.upper() for col in fp_df.columns]

        logger.info(f"Loaded {len(fp_df)} flights from database")
    except Exception as e:
        logger.error(f"Failed to load flights from database: {e}")
        return

    # Remove duplicates if any (keep first)
    fp_df = fp_df.loc[:, ~fp_df.columns.duplicated()]

    # Normalize column names for EOBD/EOBT (handle encoding issues)
    for col in fp_df.columns:
        col_str = str(col)
        if 'EOBD' in col_str or col_str.strip().endswith('BD'):
            if col != 'EOBD':
                fp_df.rename(columns={col: 'EOBD'}, inplace=True)
        if 'EOBT' in col_str or col_str.strip().endswith('BT'):
            if col != 'EOBT':
                fp_df.rename(columns={col: 'EOBT'}, inplace=True)

    # Check columns
    # User added: WAYPOINT_TIMES, SECTOR_PASSAGE_TIMES, ROUTE_EXPANSION
    # Ensure they exist or are created/reset
    # We reset them to ensure clean state
    fp_df['WAYPOINT_TIMES'] = ''
    fp_df['ROUTE_EXPANSION'] = ''

    # Ensure EOBD/EOBT columns exist
    if 'EOBD' not in fp_df.columns:
        fp_df['EOBD'] = ''
    if 'EOBT' not in fp_df.columns:
        fp_df['EOBT'] = ''
    if 'EET' not in fp_df.columns:
        fp_df['EET'] = ''
        
    # EOBT Assumption: 00:00 today
    base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
    # Create log file
    log_file = open(r'process_log.txt', 'w', encoding='utf-8')
    def log(msg):
        print(msg)
        log_file.write(msg + '\n')

    # Load Sectors (이미 위에서 경로 설정됨)
    sectors = load_sectors(sector_path)
    print(f"Loaded Sectors: {list(sectors.keys())}")

    # DB ID 캐시 생성 (조회 속도 및 정확성 향상)
    flight_id_cache = {}
    for f in flights_list:
        key = (f.get('callsign'), f.get('eobd'), f.get('eobt'))
        flight_id_cache[key] = f.get('id')

    total_flights = len(fp_df)
    processed_count = 0
    start_time = datetime.now()

    # 📊 지점별 통과시간 계산 프로세스 시작 로깅
    logger.info(f"=" * 80)
    logger.info(f"🚀 지점별 통과시간 계산 프로세스 시작")
    logger.info(f"   - 총 항공편: {total_flights:,}개")
    logger.info("   - 경로 확장 방식: calculate_trajectory (동일 로직 적용)")
    logger.info(f"   - 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"=" * 80)

    aircraft_profile_cache = {}

    # 배치 저장용 리스트
    waypoint_batch = []
    sector_batch = []
    BATCH_SIZE = 500

    for idx, row_tuple in enumerate(fp_df.itertuples(index=False)):
        try:
            processed_count += 1

            # namedtuple을 dictionary로 변환 (기존 코드와 호환)
            row = row_tuple._asdict()

            # 진행 상황 표시 (매 1000건마다 - 성능 개선)
            if processed_count % 1000 == 0 or processed_count == 1:
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / processed_count if processed_count > 0 else 0
                remaining = avg_time * (total_flights - processed_count)
                percent = int((processed_count / total_flights) * 100)
                speed = processed_count / (elapsed / 60) if elapsed > 0 else 0  # 건/분

                progress_msg = f"[flight_processor] 진행 중: {processed_count:,}/{total_flights:,} ({percent}%) | 속도: {speed:.0f}건/분 | 예상 남은 시간: {remaining/60:.1f}분"
                print(progress_msg)

                # 1000건마다 로그에도 기록
                if processed_count % 1000 == 0:
                    logger.info(progress_msg)

            callsign = row.get('CALLSIGN', f'FLT{idx}')
            dept = row.get('DEPT_AIRPORT_CD', '')
            dest = row.get('DEST_AIRPORT_CD', '')
            route = row.get('ENR', '')
            eet_str = row.get('EET', '')
            info_cn = row.get('INFO_CN', '')

            # Handle nan/float EET
            if pd.isna(eet_str):
                eet_str = ''
            else:
                eet_str = str(eet_str)

            # Extract EET from INFO_CN if EET column is empty or missing RKRR (common for international flights)
            if 'RKRR' not in eet_str:
                info_cn_eet = extract_eet_from_info_cn(str(info_cn))
                if 'RKRR' in info_cn_eet:
                    eet_str = info_cn_eet
                    fp_df.at[idx, 'EET'] = eet_str
                elif eet_str == '' and info_cn_eet:
                    # RKRR은 없지만 INFO_CN에 EET 정보가 있으면 일단 가져옴
                    eet_str = info_cn_eet
                    fp_df.at[idx, 'EET'] = eet_str

            # Extract EOBD from INFO_CN if not provided
            eobd_str = row.get('EOBD', '')
            eobt_str = row.get('EOBT', '')

            if pd.isna(eobd_str):
                eobd_str = ''
            else:
                eobd_str = str(eobd_str).strip()

            if pd.isna(eobt_str):
                eobt_str = ''
            else:
                eobt_str = str(eobt_str).strip()

            # Extract DOF from INFO_CN if EOBD is not provided
            if eobd_str == '':
                dof_date = extract_dof_from_info_cn(str(info_cn))
                if dof_date:
                    eobd_str = dof_date.strftime('%Y-%m-%d')
                    fp_df.at[idx, 'EOBD'] = eobd_str
                else:
                    # Fallback to today
                    dof_date = datetime.now().date()
                    eobd_str = dof_date.strftime('%Y-%m-%d')
                    fp_df.at[idx, 'EOBD'] = eobd_str
            else:
                try:
                    dof_date = datetime.strptime(eobd_str, '%Y-%m-%d').date()
                except:
                    dof_date = datetime.now().date()
                    eobd_str = dof_date.strftime('%Y-%m-%d')
                    fp_df.at[idx, 'EOBD'] = eobd_str

            # Parse EOBT
            if eobt_str == '':
                eobt_time = datetime.strptime('00:00', '%H:%M').time()
                fp_df.at[idx, 'EOBT'] = '00:00'
            else:
                eobt_time = parse_eobt(eobt_str)
                fp_df.at[idx, 'EOBT'] = eobt_time.strftime('%H:%M')

            # Create base_time from EOBD + EOBT
            base_time = datetime.combine(dof_date, eobt_time)

            speed_str = str(row.get('SPD', 'K0800'))
            altitude_value = row.get('ALT', row.get('ALTITUDE', ''))
            altitude_str = '' if pd.isna(altitude_value) else str(altitude_value)

            # Determine Type
            is_dept = str(dept).startswith('RK')
            is_arr = str(dest).startswith('RK')
            is_over = not is_dept and not is_arr

            # Verify GIA878 specifically
            is_target_debug = 'GIA878' in str(callsign)

            if is_target_debug:
                log(f"\n--- DEBUG: {callsign} ---")
                log(f"Route RAW: {route}")
                log(f"EET RAW: {eet_str} (Type: {type(eet_str)})")
                log(f"Type: {'DEPT' if is_dept else 'ARR' if is_arr else 'OVER'}")

            aircraft_raw = row.get('AIRCRAFT_TYPE') or row.get('AIRCRAFT')
            aircraft_code = ''
            if not pd.isna(aircraft_raw):
                aircraft_code = str(aircraft_raw).strip().upper()

            aircraft_profile = None
            if aircraft_code and db_manager:
                cache_hit = aircraft_profile_cache.get(aircraft_code)
                if cache_hit is None:
                    cache_hit = db_manager.get_aircraft_profile(aircraft_code)
                    aircraft_profile_cache[aircraft_code] = cache_hit if cache_hit else False
                if cache_hit and cache_hit is not False:
                    aircraft_profile = cache_hit

            flight_payload = {
                'callsign': str(callsign),
                'dept': str(dept),
                'dest': str(dest),
                'route': str(route),
                'speed': speed_str,
                'altitude': altitude_str,
                'aircraft_type': aircraft_code,
                'aircraft_profile': aircraft_profile,
                'eobd': eobd_str,
                'eobt': eobt_time.strftime('%H:%M'),
                'eet': eet_str,
                'info_cn': info_cn
            }

            trajectory = calculate_trajectory(flight_payload, coord_map, sectors, enroute_df, fix_col)

            if trajectory.get('status') != 'success':
                fp_df.at[idx, 'WAYPOINT_TIMES'] = ''
                fp_df.at[idx, 'SECTOR_PASSAGE_TIMES'] = ''
                fp_df.at[idx, 'ROUTE_EXPANSION'] = ''
                if is_target_debug:
                    log(f"Trajectory calculation failed: {trajectory.get('message')}")
                continue

            fp_df.at[idx, 'ROUTE_EXPANSION'] = trajectory.get('route_expansion', '')

            waypoints = trajectory.get('waypoints', [])
            sectors_result = trajectory.get('sectors', [])

            passing_times = []
            waypoint_entries = []
            for wp in waypoints:
                wp_time = wp.get('time')
                if not wp_time or wp_time == 'N/A':
                    continue
                hhmm = wp_time.replace(':', '')
                passing_times.append(f"{wp['name']} {hhmm}")
                waypoint_entries.append({'name': wp['name'], 'time': wp_time})

            sector_usage = []
            sector_entries = []
            for sector in sectors_result:
                entry = sector.get('entry')
                exit_time = sector.get('exit')
                name = sector.get('name')
                if not name or not entry or not exit_time:
                    continue
                entry_hhmm = entry.replace(':', '')
                exit_hhmm = exit_time.replace(':', '')
                sector_usage.append(f"{name} {entry_hhmm}-{exit_hhmm}")
                sector_entries.append({'name': name, 'entry': entry, 'exit': exit_time})

            fp_df.at[idx, 'WAYPOINT_TIMES'] = ' '.join(passing_times)
            fp_df.at[idx, 'SECTOR_PASSAGE_TIMES'] = ' '.join(sector_usage)

            # 📊 지점별 통과시간 계산 로깅
            if passing_times:
                waypoint_log = f"[WAYPOINT_TIMES] {callsign}: " + " -> ".join(passing_times)
                logger.info(waypoint_log)

                # 섹터별 진입/퇴출 시간 로깅
                if sector_usage:
                    sector_log = f"[SECTOR_PASSAGE_TIMES] {callsign}: " + ", ".join(sector_usage)
                    logger.info(sector_log)

            # DB에 직접 저장 (배치 처리용)
            if db_manager and callsign:
                try:
                    # 캐시에서 비행편 ID 조회 (기존의 반복적인 쿼리 제거)
                    key = (callsign, eobd_str, eobt_time.strftime('%H:%M'))
                    flight_id = flight_id_cache.get(key)

                    if flight_id:
                        # waypoint_times 배치 저장
                        for idx_wp, wp in enumerate(waypoint_entries, 1):
                            wp_name = wp['name']
                            wp_time_formatted = wp['time']
                            if wp_name and wp_time_formatted:
                                waypoint_batch.append((flight_id, wp_name, idx_wp, wp_time_formatted))

                        # sector_times 배치 저장
                        for sector in sector_entries:
                            sector_name = sector['name']
                            entry = sector['entry']
                            exit_time = sector['exit']
                            if sector_name and entry and exit_time:
                                entry_time_formatted = f"{entry[:2]}:{entry[3:]}:00" if len(entry) == 5 else f"{entry}:00"
                                exit_time_formatted = f"{exit_time[:2]}:{exit_time[3:]}:00" if len(exit_time) == 5 else f"{exit_time}:00"
                                sector_batch.append((flight_id, sector_name, entry_time_formatted, exit_time_formatted))

                        if is_target_debug:
                            log(f"✓ DB 저장 준비 완료: {callsign} ({len(passing_times)}개 지점, {len(sector_usage)}개 섹터)")
                    else:
                        logger.warning(f"Flight not found for {callsign} {eobd_str} {eobt_time}")

                    # 배치 크기 도달 시 일괄 저장
                    if len(waypoint_batch) >= BATCH_SIZE or len(sector_batch) >= BATCH_SIZE:
                        if waypoint_batch:
                            try:
                                db_manager.execute_batch_insert(
                                    """INSERT OR REPLACE INTO waypoint_times
                                       (flight_id, waypoint_name, waypoint_sequence, estimated_time)
                                       VALUES (?, ?, ?, ?)""",
                                    waypoint_batch
                                )
                                waypoint_batch.clear()
                            except Exception as batch_err:
                                logger.error(f"Waypoint batch insert error: {batch_err}")

                        if sector_batch:
                            try:
                                db_manager.execute_batch_insert(
                                    """INSERT OR REPLACE INTO sector_times
                                       (flight_id, sector_name, entry_time, exit_time)
                                       VALUES (?, ?, ?, ?)""",
                                    sector_batch
                                )
                                sector_batch.clear()
                            except Exception as batch_err:
                                logger.error(f"Sector batch insert error: {batch_err}")

                except Exception as e:
                    logger.error(f"DB 저장 오류 ({callsign}): {e}")
                    if is_target_debug:
                        log(f"✗ DB 저장 실패: {e}")

        except Exception as loop_error:
            logger.error(f"Error processing flight {idx}: {loop_error}")
            print(f"Error processing flight {idx}: {loop_error}")
            continue

    # 루프 끝에서 남은 배치 데이터 저장 (배치 처리 최적화)
    if db_manager:
        if waypoint_batch:
            try:
                db_manager.execute_batch_insert(
                    """INSERT OR REPLACE INTO waypoint_times
                       (flight_id, waypoint_name, waypoint_sequence, estimated_time)
                       VALUES (?, ?, ?, ?)""",
                    waypoint_batch
                )
                logger.info(f"Final waypoint batch inserted: {len(waypoint_batch)}개")
            except Exception as final_err:
                logger.error(f"Final waypoint batch insert error: {final_err}")

        if sector_batch:
            try:
                db_manager.execute_batch_insert(
                    """INSERT OR REPLACE INTO sector_times
                       (flight_id, sector_name, entry_time, exit_time)
                       VALUES (?, ?, ?, ?)""",
                    sector_batch
                )
                logger.info(f"Final sector batch inserted: {len(sector_batch)}개")
            except Exception as final_err:
                logger.error(f"Final sector batch insert error: {final_err}")

    # 최종 통계 출력 및 로깅
    total_elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n✅ [flight_processor] 처리 완료!")
    print(f"   - 처리된 항공편: {processed_count:,}개")
    print(f"   - 총 소요시간: {total_elapsed/60:.1f}분 ({total_elapsed:.0f}초)")
    print(f"   - 평균 처리시간: {(total_elapsed/processed_count)*1000:.1f}ms/건")
    print(f"   - 처리 속도: {processed_count/(total_elapsed/60):.0f}건/분")

    # 📊 지점별 통과시간 계산 완료 로깅
    logger.info(f"=" * 80)
    logger.info(f"✅ 지점별 통과시간 계산 프로세스 완료")
    logger.info(f"   - 처리된 항공편: {processed_count:,}개")
    logger.info(f"   - 총 소요시간: {total_elapsed/60:.1f}분 ({total_elapsed:.0f}초)")
    logger.info(f"   - 평균 처리시간: {(total_elapsed/processed_count)*1000:.1f}ms/건")
    logger.info(f"   - 처리 속도: {processed_count/(total_elapsed/60):.0f}건/분")
    logger.info(f"   - 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"=" * 80)

    log_file.close()
    print("Log saved to process_log.txt")

def load_sectors(file_path):
    """
    Load sector polygons from Excel.
    Returns dict: {SECTOR_ID: Polygon}
    """
    from shapely.geometry import Polygon
    
    try:
        # Load with header=1 based on inspection
        df = pd.read_excel(file_path, header=1)
        
        sectors = {}
        # Group by SECTOR_ID
        for sector_id, group in df.groupby('SECTOR_ID'):
            # Sort by SEQ just in case, though usually ordered
            group = group.sort_values('SEQ')
            points = list(zip(group['LON'], group['LAT']))
            if len(points) >= 3:
                sectors[sector_id] = Polygon(points)
        return sectors
    except Exception as e:
        print(f"Error loading sectors: {e}")
        return {}

def find_sector(lat, lon, sectors):
    """
    Find which sector a point belongs to.
    Returns SECTOR_ID or None.
    """
    from shapely.geometry import Point
    p = Point(lon, lat)
    for sec_id, poly in sectors.items():
        if poly.contains(p) or poly.touches(p): # Use contains/touches
            return sec_id
    return None


def parse_sector_times(sector_str, eobd_str='2024-01-01'):
    """
    섹터 진입/진출 시간 문자열을 파싱하여 datetime 딕셔너리로 변환

    Input: 'JH 08:15-08:35 JN 08:36-09:05'
    Output: {
        'JH': {'entry': datetime(...), 'exit': datetime(...)},
        'JN': {'entry': datetime(...), 'exit': datetime(...)}
    }

    Args:
        sector_str: 섹터 진입/진출 시간 문자열
        eobd_str: 날짜 문자열 (YYYY-MM-DD 형식)

    Returns:
        dict: 섹터별 진입/진출 시간 딕셔너리
    """
    import re
    from datetime import datetime, time

    sectors = {}
    if not sector_str:
        return sectors

    try:
        # Parse format: "SECTOR_NAME HH:MM-HH:MM"
        pattern = r'(\w+)\s+(\d{2}):(\d{2})-(\d{2}):(\d{2})'

        for match in re.finditer(pattern, str(sector_str)):
            sector_name = match.group(1)
            entry_hh = int(match.group(2))
            entry_mm = int(match.group(3))
            exit_hh = int(match.group(4))
            exit_mm = int(match.group(5))

            try:
                base_date = datetime.strptime(eobd_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                base_date = datetime.now().date()

            sectors[sector_name] = {
                'entry': datetime.combine(base_date, time(entry_hh, entry_mm)),
                'exit': datetime.combine(base_date, time(exit_hh, exit_mm))
            }

    except Exception as e:
        print(f"Error parsing sector times: {e}")
        return {}

    return sectors


if __name__ == "__main__":
    process_flight_plans()
