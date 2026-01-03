import pandas as pd
import math
import sys
import os
from datetime import datetime, timedelta
import re
from pathlib import Path

# ============================================================================
# 프로젝트 경로 설정 (한 번만 수행)
# ============================================================================
CURRENT_FILE = Path(__file__).resolve()
CORE_DIR = CURRENT_FILE.parent
PROJECT_ROOT = CORE_DIR.parent

# 프로젝트 루트가 sys.path에 없으면 추가
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# 모듈 import
# ============================================================================
from utils.logger import setup_logger
from core import route_converter

logger = setup_logger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) * math.sin(dlon / 2)
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
    """
    Parse ICAO speed e.g. K0926 -> 926 km/h, N0501 -> 501 knots.
    Returns speed in km/h.
    """
    if not isinstance(speed_str, str) or len(speed_str) < 2:
        return 800 # Default fallback

    unit = speed_str[0]
    try:
        val = int(speed_str[1:])
        if unit == 'K':
            return val
        elif unit == 'N':
            return val * 1.852 # Knots to km/h
        elif unit == 'M':
            # Mac number, approximate... let's say Mach 1 ~ 1235 km/h
            return (val / 100.0) * 1235
    except:
        pass
    return 800

def parse_altitude(alt_str):
    """
    Parse ICAO altitude field (ALT column).

    Examples:
    - F400 → 40000 feet (Flight Level 400)
    - S0890 → 8900 meters → ~29200 feet (Standard Metric)
    - A100 → 100 feet (Altitude)
    - M0500 → 500 meters → ~1640 feet (Metric)

    Returns:
        int: altitude in feet, or None if invalid
    """
    if not isinstance(alt_str, str) or len(alt_str) < 2:
        return None

    unit = alt_str[0]
    try:
        val = int(alt_str[1:])
        if unit == 'F':  # Flight Level (FL400 = 40000 feet)
            return val * 100
        elif unit == 'S':  # Standard Metric (meters)
            return int(val * 3.28084)
        elif unit == 'A':  # Altitude (feet)
            return val
        elif unit == 'M':  # Metric (meters)
            return int(val * 3.28084)
    except Exception as e:
        logger.debug(f"parse_altitude error for '{alt_str}': {e}")
        pass

    return None

def get_aircraft_speed_and_climb(db_manager, aircraft_type, spd_str):
    """
    Get speed and climb rate for aircraft with fallback mechanism.

    Priority:
    1. SPD field from CSV
    2. aircraft_profiles.default_speed_kmh (기종 기본 속도)
    3. Hardcoded default (800 km/h)

    Also retrieves climb rate and ceiling from aircraft_profiles.

    Args:
        db_manager: DatabaseManager instance
        aircraft_type: ICAO aircraft code (e.g., 'B77L', 'A321')
        spd_str: Speed string from CSV (e.g., 'K0926', 'N0501')

    Returns:
        dict: {
            'speed_kmh': int,
            'speed_source': 'csv' | 'aircraft_profile' | 'default',
            'climb_fpm': int,  # feet per minute
            'ceiling_fl': int   # Flight Level
        }
    """
    result = {
        'speed_kmh': 800,
        'speed_source': 'default',
        'climb_fpm': 2000,
        'ceiling_fl': 410
    }

    # 1. Try to use SPD from CSV first
    if spd_str and isinstance(spd_str, str):
        speed = parse_speed(spd_str)
        if speed and speed > 0:
            result['speed_kmh'] = speed
            result['speed_source'] = 'csv'

            # Still get climb rate from aircraft_profiles if available
            if aircraft_type and db_manager:
                try:
                    profile = db_manager.get_aircraft_profile(aircraft_type)
                    if profile:
                        if profile.get('default_climb_fpm'):
                            result['climb_fpm'] = profile['default_climb_fpm']
                        if profile.get('default_ceiling_fl'):
                            result['ceiling_fl'] = profile['default_ceiling_fl']
                except Exception as e:
                    logger.debug(f"Failed to get aircraft profile for {aircraft_type}: {e}")

            return result

    # 2. Try aircraft_profiles (if SPD is empty/invalid)
    if aircraft_type and db_manager:
        try:
            profile = db_manager.get_aircraft_profile(aircraft_type)
            if profile:
                if profile.get('default_speed_kmh') and profile['default_speed_kmh'] > 0:
                    result['speed_kmh'] = profile['default_speed_kmh']
                    result['speed_source'] = 'aircraft_profile'

                if profile.get('default_climb_fpm') and profile['default_climb_fpm'] > 0:
                    result['climb_fpm'] = profile['default_climb_fpm']

                if profile.get('default_ceiling_fl') and profile['default_ceiling_fl'] > 0:
                    result['ceiling_fl'] = profile['default_ceiling_fl']

                return result
        except Exception as e:
            logger.debug(f"Failed to get aircraft profile for {aircraft_type}: {e}")

    # 3. Use defaults (already set in result)
    return result

def calculate_climb_time_simple(distance_km, dep_alt_ft, cruise_alt_ft, climb_fpm, speed_kmh):
    """
    Method A: Simple Linear Climb Calculation.

    Assumes constant climb rate and constant horizontal speed.
    Calculates how long it takes to climb from departure altitude to cruise altitude,
    then adds time for remaining cruise distance.

    Args:
        distance_km: Total horizontal distance (km)
        dep_alt_ft: Departure altitude (feet)
        cruise_alt_ft: Cruise (target) altitude (feet)
        climb_fpm: Climb rate (feet per minute)
        speed_kmh: Horizontal speed (km/h)

    Returns:
        dict: {
            'climb_time_minutes': float,
            'climb_distance_km': float,
            'cruise_distance_km': float,
            'cruise_time_minutes': float,
            'total_time_minutes': float
        }
    """
    if speed_kmh <= 0:
        speed_kmh = 800  # Fallback

    if climb_fpm <= 0:
        climb_fpm = 2000  # Fallback

    # Calculate altitude change
    altitude_gain_ft = max(0, cruise_alt_ft - dep_alt_ft)

    # Calculate climb time (minutes)
    climb_time_minutes = altitude_gain_ft / climb_fpm if climb_fpm > 0 else 0

    # Calculate distance covered during climb
    # Speed: km/h → km/min = speed_kmh / 60
    climb_speed_km_per_min = speed_kmh / 60
    climb_distance_km = climb_speed_km_per_min * climb_time_minutes

    # Calculate cruise distance and time
    cruise_distance_km = max(0, distance_km - climb_distance_km)
    cruise_time_minutes = cruise_distance_km / climb_speed_km_per_min if climb_speed_km_per_min > 0 else 0

    total_time_minutes = climb_time_minutes + cruise_time_minutes

    return {
        'climb_time_minutes': climb_time_minutes,
        'climb_distance_km': climb_distance_km,
        'cruise_distance_km': cruise_distance_km,
        'cruise_time_minutes': cruise_time_minutes,
        'total_time_minutes': total_time_minutes
    }

def calculate_waypoints_with_eet(exit_time, points_data, speed_kmh, dep_alt_ft, cruise_alt_ft, climb_fpm):
    """
    Method B: EET Backtracking Waypoint Time Calculation.

    Works backwards from a known exit time (EET).
    Distributes climb phase based on accumulated distance from departure.

    Args:
        exit_time: Known exit time (datetime.time or datetime.datetime)
        points_data: List of dicts with keys 'name', 'dist' (distance from departure in km)
        speed_kmh: Horizontal speed (km/h)
        dep_alt_ft: Departure altitude (feet)
        cruise_alt_ft: Cruise (target) altitude (feet)
        climb_fpm: Climb rate (feet per minute)

    Returns:
        List of dicts: [
            {
                'name': str,
                'time': datetime.time or datetime.datetime,
                'altitude_ft': int,
                'is_climbing': bool,
                'distance_km': float
            },
            ...
        ]
    """
    if speed_kmh <= 0:
        speed_kmh = 800

    if climb_fpm <= 0:
        climb_fpm = 2000

    # Convert exit_time to datetime.time if it's datetime.datetime
    if isinstance(exit_time, datetime):
        exit_time_only = exit_time.time()
    else:
        exit_time_only = exit_time

    # Calculate climb parameters
    altitude_gain_ft = max(0, cruise_alt_ft - dep_alt_ft)
    climb_time_minutes = altitude_gain_ft / climb_fpm if climb_fpm > 0 else 0
    climb_speed_km_per_min = speed_kmh / 60
    climb_distance_km = climb_speed_km_per_min * climb_time_minutes

    # Work backwards from exit_time
    current_time = datetime.combine(datetime.today(), exit_time_only)
    result = []

    # Reverse iterate through points to calculate times backwards
    for i in range(len(points_data) - 1, -1, -1):
        point = points_data[i]
        point_distance_from_start = point.get('dist', 0)

        # Adjust time based on distance to next point (if not last)
        if i < len(points_data) - 1:
            next_point = points_data[i + 1]
            dist_to_next = next_point.get('dist', 0) - point_distance_from_start
            if dist_to_next > 0:
                travel_time_minutes = dist_to_next / climb_speed_km_per_min
                current_time = current_time - timedelta(minutes=travel_time_minutes)

        # Determine altitude and climb status based on distance
        if point_distance_from_start > 0 and point_distance_from_start <= climb_distance_km and climb_distance_km > 0:
            # In climb phase (but not at departure point)
            progress = point_distance_from_start / climb_distance_km
            altitude_ft = int(dep_alt_ft + (altitude_gain_ft * progress))
            is_climbing = True
        else:
            # Cruise phase or at departure point
            if point_distance_from_start == 0:
                # Departure point
                altitude_ft = dep_alt_ft
            else:
                # Cruise phase
                altitude_ft = cruise_alt_ft
            is_climbing = False

        result.append({
            'name': point.get('name', f'Point_{i}'),
            'time': current_time.time(),
            'altitude_ft': altitude_ft,
            'is_climbing': is_climbing,
            'distance_km': point_distance_from_start
        })

    # Reverse to get correct order (from start to end)
    return list(reversed(result))

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

def process_flight_plans(db_manager=None):
    """
    항공편 계획 처리 및 DB 저장

    Args:
        db_manager: DatabaseManager 인스턴스 (선택사항)
    """
    # 1. Load Reference Data from Database
    if not db_manager:
        from database.db_manager import DatabaseManager
        db_manager = DatabaseManager()

    # DB에서 경유지점 데이터 로드
    enroute_df = db_manager.get_all_waypoints_df()
    if enroute_df.empty:
        print("Error: waypoints 테이블이 비어있습니다. 데이터베이스를 확인하세요.")
        return

    fix_col = 'fixpnt'  # DB 컬럼명

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

    # Load Sectors from Database
    sectors = load_sectors(db_manager)
    if not sectors:
        print("Error: sector_boundaries 테이블이 비어있습니다. 데이터베이스를 확인하세요.")
        return
    print(f"Loaded Sectors: {list(sectors.keys())}")

    total_flights = len(fp_df)
    processed_count = 0
    start_time = datetime.now()

    # 📊 지점별 통과시간 계산 프로세스 시작 로깅
    logger.info(f"=" * 80)
    logger.info(f"🚀 지점별 통과시간 계산 프로세스 시작")
    logger.info(f"   - 총 항공편: {total_flights:,}개")
    logger.info(f"   - 확장 경로점: {len(korea_points) if 'korea_points' in locals() else '미정'}개")
    logger.info(f"   - 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"=" * 80)

    for idx, row in fp_df.iterrows():
        try:
            processed_count += 1

            # 진행 상황 표시 (매 100건마다)
            if processed_count % 100 == 0 or processed_count == 1:
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / processed_count if processed_count > 0 else 0
                remaining = avg_time * (total_flights - processed_count)
                percent = int((processed_count / total_flights) * 100)
                speed = processed_count / (elapsed / 60) if elapsed > 0 else 0  # 건/분

                progress_msg = f"[flight_processor] 진행 중: {processed_count:,}/{total_flights:,} ({percent}%) | 속도: {speed:.0f}건/분 | 예상 남은 시간: {remaining/60:.1f}분"
                print(progress_msg)

                # 20건마다 로그에도 기록
                if processed_count % 500 == 0:
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

            # Extract EET from INFO_CN if EET column is empty
            if eet_str == '':
                eet_str = extract_eet_from_info_cn(str(info_cn))
                if eet_str:
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
            aircraft_type = str(row.get('AIRCRAFT_TYPE', ''))
            alt_str = str(row.get('ALT', ''))

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
                log(f"Aircraft Type: {aircraft_type}, ALT: {alt_str}")
                log(f"Type: {'DEPT' if is_dept else 'ARR' if is_arr else 'OVER'}")

            # Expand Route
            expanded_points = route_converter.expand_route(enroute_df, fix_col, str(route))

            # Filter for Korea points (those in coord_map)
            korea_points = [p for p in expanded_points if p in coord_map]

            if not korea_points:
                fp_df.at[idx, 'ROUTE_EXPANSION'] = ''
                if is_target_debug:
                    log("No Korea points found in route expansion.")
                continue

            fp_df.at[idx, 'ROUTE_EXPANSION'] = ' '.join(korea_points)
            if is_target_debug:
                log(f"Expanded Korea Points: {korea_points}")

            # Calculate Times - Get speed and climb rate with fallback
            aircraft_info = get_aircraft_speed_and_climb(db_manager, aircraft_type, speed_str)
            speed_kmh = aircraft_info['speed_kmh']
            speed_source = aircraft_info['speed_source']
            climb_fpm = aircraft_info['climb_fpm']
            ceiling_fl = aircraft_info['ceiling_fl']

            # Parse altitude (CFL - Cruise Flight Level)
            cruise_alt_ft = parse_altitude(alt_str)
            if not cruise_alt_ft:
                cruise_alt_ft = ceiling_fl * 100

            if is_target_debug:
                log(f"Speed: {speed_str} -> {speed_kmh} km/h (source: {speed_source})")
                log(f"Climb Rate: {climb_fpm} fpm, CFL: {cruise_alt_ft} ft, Ceiling: {ceiling_fl} FL")

            passing_times = []

            # Points with Time Data
            # We need to store time for sector calc
            timed_points = []

            # First, find Entry/Exit times relative to Base Time
            rkrr_duration = parse_eet(eet_str, 'RKRR')
            if is_target_debug:
                log(f"RKRR EET Duration: {rkrr_duration}")

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
                    'sector': find_sector(lat, lon, sectors) # Find Sector
                })

            def format_pt_time(name, dt):
                return f"{name} {dt.strftime('%H%M')}"

            if is_dept:
                match = re.search(r'([A-Z]{4})(\d{4})', str(eet_str))
                if match:
                    hhmm = match.group(2)
                    exit_delta = timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[2:]))
                    exit_time = base_time + exit_delta

                    # Method B: EET Backtracking (현재 사용 방식)
                    waypoints_b = calculate_waypoints_with_eet(
                        exit_time,
                        points_data,
                        speed_kmh,
                        dep_alt_ft=0,  # RK 출발 (지면)
                        cruise_alt_ft=cruise_alt_ft,
                        climb_fpm=climb_fpm
                    )

                    # Store Method B results and times
                    passing_times = []
                    for wp_b in waypoints_b:
                        passing_times.append(format_pt_time(wp_b['name'], wp_b['time']))
                        # Also store time in points_data for sector calculation
                        for p in points_data:
                            if p['name'] == wp_b['name']:
                                p['time'] = wp_b['time']
                                p['altitude_ft'] = wp_b['altitude_ft']
                                p['is_climbing'] = wp_b['is_climbing']
                                break

                    # Method A: Simple Linear Climb (비교용)
                    # 총 거리 계산 (첫 지점 제외)
                    if len(points_data) > 1:
                        total_dist = sum(p['dist'] for p in points_data[1:])
                    else:
                        total_dist = 0

                    climb_a = calculate_climb_time_simple(
                        distance_km=total_dist,
                        dep_alt_ft=0,
                        cruise_alt_ft=cruise_alt_ft,
                        climb_fpm=climb_fpm,
                        speed_kmh=speed_kmh
                    )

                    # Calculate waypoints for Method A
                    waypoints_a = []
                    current_time = exit_time
                    accumulated_dist = 0

                    for i in range(len(points_data) - 1, -1, -1):
                        p = points_data[i]
                        # Calculate time from travel distance
                        if i < len(points_data) - 1:
                            dist_to_next = points_data[i+1]['dist']
                            travel_hours = dist_to_next / speed_kmh
                            current_time = current_time - timedelta(hours=travel_hours)

                        accumulated_dist += p['dist']

                        # Determine altitude based on climb phase
                        if accumulated_dist <= climb_a['climb_distance_km'] and climb_a['climb_distance_km'] > 0:
                            progress = accumulated_dist / climb_a['climb_distance_km']
                            altitude_ft = int(0 + (cruise_alt_ft * progress))
                            is_climbing = True
                        else:
                            altitude_ft = cruise_alt_ft
                            is_climbing = False

                        waypoints_a.append({
                            'name': p['name'],
                            'time': current_time,
                            'altitude_ft': altitude_ft,
                            'is_climbing': is_climbing
                        })

                    waypoints_a = list(reversed(waypoints_a))
                else:
                    # No EET match - use simple forward calculation
                    current_time = base_time
                    waypoints_b = []
                    for i, p in enumerate(points_data):
                        if i > 0:
                            dist = p['dist']
                            current_time += timedelta(hours=(dist/speed_kmh))
                        passing_times.append(format_pt_time(p['name'], current_time))
                        points_data[i]['time'] = current_time
                        waypoints_b.append({
                            'name': p['name'],
                            'time': current_time,
                            'altitude_ft': cruise_alt_ft,
                            'is_climbing': False
                        })
                    waypoints_a = []  # No comparison in this case

            elif is_arr:
                waypoints_b = []
                waypoints_a = []
                if rkrr_duration:
                    # User Requirement: Entry Time = EOBT (Base) + RKRR time
                    # This Entry Time applies to the FIRST point of the Korea sector (Entry Point)
                    entry_time = base_time + rkrr_duration
                    if is_target_debug:
                        log(f"Entry Time (RKRR): {entry_time.strftime('%H:%M')}")

                    current_time = entry_time
                    for i, p in enumerate(points_data):
                        if i == 0:
                            # First point IS the entry point, so it gets the entry_time directly
                            if is_target_debug:
                                log(f"  -> {p['name']} (Entry): {current_time.strftime('%H:%M')}")
                        else:
                            # Subsequent points add travel time from previous
                            dist_from_prev = p['dist'] # This is dist from prev point as calculated above
                            travel_hours = dist_from_prev / speed_kmh
                            current_time += timedelta(hours=travel_hours)
                            if is_target_debug:
                                log(f"  -> {p['name']} (+{dist_from_prev:.2f}km): {current_time.strftime('%H:%M')}")

                        passing_times.append(format_pt_time(p['name'], current_time))
                        points_data[i]['time'] = current_time
                        # ARR flights enter at cruise altitude (no climb)
                        waypoints_b.append({
                            'name': p['name'],
                            'time': current_time,
                            'altitude_ft': cruise_alt_ft,
                            'is_climbing': False
                        })
                else:
                    passing_times = ["EET_ERROR"]

            else: # Overflight
                waypoints_b = []
                waypoints_a = []
                if rkrr_duration:
                    entry_time = base_time + rkrr_duration
                    current_time = entry_time
                    for i, p in enumerate(points_data):
                        if i > 0:
                            dist = p['dist']
                            current_time += timedelta(hours=(dist/speed_kmh))
                        passing_times.append(format_pt_time(p['name'], current_time))
                        points_data[i]['time'] = current_time
                        # OVER flights also at cruise altitude (no climb)
                        waypoints_b.append({
                            'name': p['name'],
                            'time': current_time,
                            'altitude_ft': cruise_alt_ft,
                            'is_climbing': False
                        })
                else:
                    passing_times = []

            # --- Sector Analysis ---
            sector_usage = []
            if passing_times and passing_times[0] != "EET_ERROR" and points_data and 'time' in points_data[0]:
                # Simplify: Group contiguous points in same sector
                current_sector = None
                sector_enter_time = None
                sector_exit_time = None

                for p in points_data:
                    sec = p['sector']
                    time = p['time']

                    if sec != current_sector:
                        # Sector Changed
                        if current_sector is not None:
                            # Close previous sector
                            sector_usage.append(f"{current_sector} {sector_enter_time.strftime('%H%M')}-{sector_exit_time.strftime('%H%M')}")

                        if sec is not None:
                            # Start new sector
                            current_sector = sec
                            sector_enter_time = time
                            sector_exit_time = time # Initialize exit same as enter
                    else:
                        # Same sector, update exit time
                        if sec is not None:
                            sector_exit_time = time

                # Close last sector
                if current_sector is not None:
                    sector_usage.append(f"{current_sector} {sector_enter_time.strftime('%H%M')}-{sector_exit_time.strftime('%H%M')}")

            fp_df.at[idx, 'WAYPOINT_TIMES'] = ' '.join(passing_times)
            fp_df.at[idx, 'SECTOR_PASSAGE_TIMES'] = ' '.join(sector_usage) if sector_usage else ''

            # 📊 지점별 통과시간 계산 로깅
            if korea_points and passing_times:
                waypoint_log = f"[WAYPOINT_TIMES] {callsign}: " + " -> ".join(passing_times)
                logger.info(waypoint_log)

                # 섹터별 진입/퇴출 시간 로깅
                if sector_usage:
                    sector_log = f"[SECTOR_PASSAGE_TIMES] {callsign}: " + ", ".join(sector_usage)
                    logger.info(sector_log)

            # DB에 직접 저장 (db_manager가 있으면)
            if db_manager and callsign:
                try:
                    # 비행편 ID 조회
                    flight_result = db_manager.execute_query(
                        """SELECT id FROM flights
                           WHERE callsign = ? AND eobd = ? AND eobt = ?""",
                        (callsign, eobd_str, eobt_time.strftime('%H:%M'))
                    )
                    flight_rows = list(flight_result)

                    if flight_rows:
                        flight_id = flight_rows[0]['id']

                        # Update flights table with aircraft info
                        try:
                            db_manager.execute_query(
                                """UPDATE flights SET
                                   calculated_speed_kmh = ?,
                                   speed_source = ?,
                                   climb_rate_fpm = ?,
                                   cruise_flight_level = ?,
                                   is_climbing = ?
                                   WHERE id = ?""",
                                (speed_kmh, speed_source, climb_fpm, ceiling_fl, int(is_dept))
                            )
                        except Exception as e:
                            logger.debug(f"Failed to update flight info for {callsign}: {e}")

                        # waypoint_times 테이블에 저장 (Method B 사용)
                        for idx_wp, wp_b in enumerate(waypoints_b, 1):
                            try:
                                wp_time_formatted = wp_b['time'].strftime('%H:%M:%S')

                                db_manager.execute_insert(
                                    """INSERT OR REPLACE INTO waypoint_times
                                       (flight_id, waypoint_name, waypoint_sequence, estimated_time,
                                        altitude_ft, is_climbing, time_method)
                                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                    (flight_id, wp_b['name'], idx_wp, wp_time_formatted,
                                     wp_b['altitude_ft'], int(wp_b['is_climbing']), 'eet_backtrack')
                                )
                            except Exception as wp_err:
                                logger.debug(f"Waypoint save error for {callsign}: {wp_err}")

                        # climb_calculations 테이블에 저장 (Method A vs B 비교)
                        if is_dept and waypoints_a:
                            for idx_wp, (wp_a, wp_b) in enumerate(zip(waypoints_a, waypoints_b), 1):
                                try:
                                    time_diff = abs((wp_a['time'] - wp_b['time']).total_seconds())
                                    alt_diff = abs(wp_a['altitude_ft'] - wp_b['altitude_ft'])

                                    db_manager.execute_insert(
                                        """INSERT INTO climb_calculations
                                           (flight_id, waypoint_name, waypoint_sequence,
                                            simple_linear_time, simple_linear_altitude_ft,
                                            eet_backtrack_time, eet_backtrack_altitude_ft,
                                            time_difference_seconds, altitude_difference_ft)
                                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                        (flight_id, wp_a['name'], idx_wp,
                                         wp_a['time'].strftime('%H:%M:%S'), wp_a['altitude_ft'],
                                         wp_b['time'].strftime('%H:%M:%S'), wp_b['altitude_ft'],
                                         time_diff, alt_diff)
                                    )
                                except Exception as cc_err:
                                    logger.debug(f"Climb calculation save error for {callsign}: {cc_err}")

                        # sector_times 테이블에 저장
                        for sector_info in sector_usage:
                            try:
                                # Parse "SECTOR HHMM-HHMM" format
                                parts = sector_info.split()
                                if len(parts) >= 2:
                                    sector_name = parts[0]
                                    times = parts[1].split('-')
                                    if len(times) == 2:
                                        entry_hhmm = times[0]
                                        exit_hhmm = times[1]
                                        # Convert HHMM to HH:MM:SS format
                                        entry_time_formatted = f"{entry_hhmm[:2]}:{entry_hhmm[2:]}:00"
                                        exit_time_formatted = f"{exit_hhmm[:2]}:{exit_hhmm[2:]}:00"

                                        db_manager.execute_insert(
                                            """INSERT OR REPLACE INTO sector_times
                                               (flight_id, sector_name, entry_time, exit_time)
                                               VALUES (?, ?, ?, ?)""",
                                            (flight_id, sector_name, entry_time_formatted, exit_time_formatted)
                                        )
                            except Exception as st_err:
                                logger.debug(f"Sector time save error for {callsign}: {st_err}")

                        if is_target_debug:
                            log(f"✓ DB 저장 완료: {callsign} ({len(passing_times)}개 지점, {len(sector_usage)}개 섹터)")
                    else:
                        logger.warning(f"Flight not found for {callsign} {eobd_str} {eobt_time}")
                except Exception as e:
                    logger.error(f"DB 저장 오류 ({callsign}): {e}")
                    if is_target_debug:
                        log(f"✗ DB 저장 실패: {e}")

        except Exception as loop_error:
            logger.error(f"Error processing flight {idx}: {loop_error}")
            print(f"Error processing flight {idx}: {loop_error}")
            continue

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

def load_sectors(db_manager=None):
    """
    Load sector polygons from database.
    Returns dict: {SECTOR_ID: Polygon}
    """
    from shapely.geometry import Polygon

    if not db_manager:
        from database.db_manager import DatabaseManager
        db_manager = DatabaseManager()

    try:
        # DB에서 섹터 경계 데이터 로드
        sectors_dict = db_manager.get_sector_boundaries_dict()
        if not sectors_dict:
            raise RuntimeError("sector_boundaries 테이블이 비어있습니다. 데이터베이스를 확인하세요.")
        return sectors_dict
    except Exception as e:
        logger.error(f"섹터 데이터 로드 오류: {e}")
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
