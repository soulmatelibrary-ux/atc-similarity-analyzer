"""
항공편 데이터 서비스
- 파일 업로드 후 DB 저장
- 지점별 통과시간 및 섹터 진입진출시간 계산
- 유사호출 감지 및 DB 저장
"""
import logging
import json
import os
import tempfile
import re
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from database.db_manager import DatabaseManager
from core.similarity_engine import check_similarity
from core.flight_processor import calculate_trajectory
from core.modeling_resources import get_modeling_resources

logger = logging.getLogger(__name__)

# 글로벌 진행 상태 저장소 (프로세스 별)
upload_progress = {}

# 진행 상황 저장 디렉토리
PROGRESS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.uploads_progress')
os.makedirs(PROGRESS_DIR, exist_ok=True)

CALLSIGN_PREFIX_PATTERN = re.compile(r'^[A-Z]+')
DIGIT_PATTERN = re.compile(r'\d')


def extract_callsign_prefix(callsign):
    if not callsign:
        return ''
    match = CALLSIGN_PREFIX_PATTERN.match(str(callsign).upper())
    return match.group(0) if match else ''


def extract_callsign_digits(callsign):
    if not callsign:
        return ''
    return ''.join(DIGIT_PATTERN.findall(str(callsign)))


def normalize_eobt(value):
    if value is None:
        return '00:00'
    value = str(value).strip()
    if not value or value.lower() == 'nan':
        return '00:00'
    if len(value) >= 5 and value[2] == ':':
        return value[:5]
    digits_only = ''.join(ch for ch in value if ch.isdigit())
    if not digits_only:
        return '00:00'
    padded = digits_only.zfill(4)
    return f"{padded[:2]}:{padded[2:]}"

def save_progress_to_file(process_id, progress_data):
    """진행 상황을 파일에 저장"""
    if not process_id:
        return
    try:
        progress_file = os.path.join(PROGRESS_DIR, f'{process_id}.json')
        tmp_fd, tmp_path = tempfile.mkstemp(prefix=f'{process_id}_', suffix='.json', dir=PROGRESS_DIR)
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as tmp:
                json.dump(progress_data, tmp, ensure_ascii=False)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, progress_file)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    except Exception as e:
        logger.error(f"진행 상황 저장 오류: {e}")


class FlightService:
    def __init__(self, db_manager=None):
        self.db = db_manager or DatabaseManager()

    @staticmethod
    def _add_pairs_from_bucket(bucket_map, candidate_set):
        for bucket in bucket_map.values():
            if len(bucket) < 2:
                continue
            for f1, f2 in combinations(bucket, 2):
                pair = (f1, f2) if f1 < f2 else (f2, f1)
                candidate_set.add(pair)

    @staticmethod
    def _build_candidate_pairs_for_date(flights):
        candidate_pairs = set()
        prefix_buckets = defaultdict(list)
        sandwich_buckets = defaultdict(list)
        transposition_buckets = defaultdict(list)
        digits_buckets = defaultdict(list)
        digitset_buckets = defaultdict(list)

        for flight in flights:
            flight_id = flight['id']
            prefix = flight.get('prefix', '')
            digits = flight.get('digits', '')

            if prefix:
                prefix_buckets[prefix].append(flight_id)
                if len(prefix) >= 2:
                    sandwich_key = f"{prefix[0]}_{prefix[-1]}"
                    sandwich_buckets[sandwich_key].append(flight_id)
                if len(prefix) == 3:
                    trans_key = (prefix[0], ''.join(sorted(prefix[1:])))
                    transposition_buckets[trans_key].append(flight_id)

            if digits:
                digits_buckets[digits].append(flight_id)
                if len(digits) > 1:
                    digitset_key = ''.join(sorted(digits))
                    digitset_buckets[digitset_key].append(flight_id)

        FlightService._add_pairs_from_bucket(prefix_buckets, candidate_pairs)
        FlightService._add_pairs_from_bucket(sandwich_buckets, candidate_pairs)
        FlightService._add_pairs_from_bucket(transposition_buckets, candidate_pairs)
        FlightService._add_pairs_from_bucket(digits_buckets, candidate_pairs)
        FlightService._add_pairs_from_bucket(digitset_buckets, candidate_pairs)

        return candidate_pairs

    def insert_flights_bulk(self, flights_data, upload_file_name, file_size, process_id=None):
        """
        항공편 데이터를 벌크로 데이터베이스에 삽입 (단계 1)

        Args:
            flights_data: 검증된 항공편 데이터 (list of dict)
            upload_file_name: 업로드 파일명
            file_size: 파일 크기 (bytes)
            process_id: 진행 상황 추적 ID (선택사항)

        Returns:
            dict: {'status': 'success'/'error', 'message': str, 'inserted_count': int, 'flights_data': list}
        """
        try:
            import time
            start_time = time.time()
            logger.info(f"[단계 1] 벌크 항공편 삽입 시작: {len(flights_data)}개 항공편")

            # 진행 상태 초기화
            if process_id:
                progress = {
                    'total': len(flights_data),
                    'processed': 0,
                    'stage': '[1/3] 항공편 벌크 입력 중...',
                    'percent': 1
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            # 벌크 INSERT (다중 행 VALUES)
            result = self.db.insert_batch_flights(flights_data)
            flight_ids_list = result['ids']
            inserted_count = result['count']
            error_count = len(flights_data) - inserted_count

            # 진행 상태 업데이트 (단계 1 완료)
            if process_id:
                progress = {
                    'total': len(flights_data),
                    'processed': inserted_count,
                    'stage': f'[1/3 완료] {inserted_count:,}개 항공편 입력 완료',
                    'percent': 45
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            elapsed = time.time() - start_time
            logger.info(f"[단계 1 완료] {elapsed:.3f}초 내에 {inserted_count}개 항공편 삽입 완료")

            # 업로드 이력 기록
            self.db.record_upload(
                upload_file_name,
                file_size,
                inserted_count,
                status='data_inserted',
                error_msg=f"{error_count} flights failed" if error_count > 0 else None
            )

            return {
                'status': 'success',
                'message': f'{inserted_count}개 항공편 벌크 입력 완료',
                'inserted_count': inserted_count,
                'error_count': error_count,
                'flights_data': flights_data,
                'elapsed_time': elapsed
            }

        except Exception as e:
            logger.error(f"벌크 입력 오류: {e}")
            self.db.record_upload(upload_file_name, file_size, 0, status='failed', error_msg=str(e))

            if process_id:
                upload_progress[process_id] = {
                    'total': len(flights_data),
                    'processed': 0,
                    'stage': f'입력 오류: {str(e)}',
                    'percent': 0
                }

            return {
                'status': 'error',
                'message': f'항공편 입력 실패: {str(e)}',
                'inserted_count': 0
            }

    def calculate_sector_times(self, flights_data, process_id=None):
        """Calculate waypoint and sector passage times using the shared trajectory engine."""
        try:
            import time
            start_time = time.time()

            if not flights_data:
                return {
                    'status': 'warning',
                    'message': '계산할 항공편이 없습니다',
                    'sector_count': 0,
                    'waypoint_count': 0
                }

            total_records = len(flights_data)

            resources = get_modeling_resources()
            enroute_df = resources['enroute_df']
            fix_col = resources['fix_col']
            coord_map = resources['coord_map']
            sectors = resources['sectors']

            flights = self.db.get_all_flights()
            if not flights:
                logger.warning("저장된 항공편이 없습니다")
                return {
                    'status': 'warning',
                    'message': '계산할 항공편이 없습니다',
                    'sector_count': 0,
                    'waypoint_count': 0
                }

            logger.info(f"[단계 2] 궤적 및 섹터 계산 시작: {len(flights_data)}개 비행계획")

            if process_id:
                progress = {
                    'total': total_records,
                    'processed': 0,
                    'stage': '[2/3] 궤적 계산 중...',
                    'percent': 46
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            flight_id_map = {}
            for flight in flights:
                key = (
                    str(flight.get('callsign') or '').upper(),
                    str(flight.get('eobd') or ''),
                    normalize_eobt(flight.get('eobt'))
                )
                flight_id_map[key] = flight['id']

            waypoint_batch = []
            sector_batch = []
            waypoint_total = 0
            sector_total = 0
            processed = 0
            success_count = 0
            BATCH_SIZE = 500
            aircraft_profile_cache = {}

            def get_aircraft_profile_cached(aircraft_code):
                if not aircraft_code:
                    return None
                if aircraft_code not in aircraft_profile_cache:
                    profile = self.db.get_aircraft_profile(aircraft_code)
                    aircraft_profile_cache[aircraft_code] = profile if profile else None
                return aircraft_profile_cache[aircraft_code]

            for row in flights_data:
                processed += 1
                callsign = str(row.get('CALLSIGN', '') or '').strip().upper()
                if not callsign:
                    continue

                eobd = str(row.get('EOBD', '') or '').strip()
                eobt = normalize_eobt(row.get('EOBT', '00:00'))
                key = (callsign, eobd, eobt)
                flight_id = flight_id_map.get(key)
                if not flight_id:
                    continue

                route = str(row.get('ENR', '') or '')
                if not route.strip():
                    continue

                aircraft_code = str(row.get('AIRCRAFT_TYPE', '') or '').strip().upper()

                payload = {
                    'callsign': callsign,
                    'dept': str(row.get('DEPT_AIRPORT_CD', '') or '').strip().upper(),
                    'dest': str(row.get('DEST_AIRPORT_CD', '') or '').strip().upper(),
                    'route': route,
                    'speed': str(row.get('SPD', '') or ''),
                    'altitude': '' if row.get('ALT') is None else str(row.get('ALT')),
                    'aircraft_type': aircraft_code,
                    'aircraft_profile': get_aircraft_profile_cached(aircraft_code),
                    'eobd': eobd,
                    'eobt': eobt,
                    'eet': str(row.get('EET', '') or ''),
                    'info_cn': str(row.get('INFO_CN', '') or '')
                }

                result = calculate_trajectory(payload, coord_map, sectors, enroute_df, fix_col)
                if result.get('status') != 'success':
                    logger.debug(f"Trajectory 계산 실패: {callsign} - {result.get('message')}")
                    continue

                success_count += 1

                waypoint_entries = result.get('waypoints', [])
                for idx_wp, waypoint in enumerate(waypoint_entries, 1):
                    wp_name = waypoint.get('name')
                    wp_time = waypoint.get('time')
                    if not wp_name or not wp_time or wp_time == 'N/A':
                        continue
                    formatted_time = f"{wp_time}:00" if len(wp_time) == 5 and wp_time[2] == ':' else wp_time
                    waypoint_batch.append((flight_id, wp_name, idx_wp, formatted_time))
                    waypoint_total += 1
                    if len(waypoint_batch) >= BATCH_SIZE:
                        self.db.execute_batch_insert(
                            """INSERT OR REPLACE INTO waypoint_times
                                   (flight_id, waypoint_name, waypoint_sequence, estimated_time)
                                   VALUES (?, ?, ?, ?)""",
                            waypoint_batch
                        )
                        waypoint_batch.clear()

                sector_entries = result.get('sectors', [])
                for sector in sector_entries:
                    name = sector.get('name')
                    entry = sector.get('entry')
                    exit_time = sector.get('exit')
                    if not name or not entry or not exit_time:
                        continue
                    entry_db = f"{entry}:00" if len(entry) == 5 and entry[2] == ':' else entry
                    exit_db = f"{exit_time}:00" if len(exit_time) == 5 and exit_time[2] == ':' else exit_time
                    sector_batch.append((flight_id, name, entry_db, exit_db))
                    sector_total += 1
                    if len(sector_batch) >= BATCH_SIZE:
                        self.db.insert_batch_sector_times(sector_batch)
                        sector_batch.clear()

                if process_id and (processed % 10 == 0 or processed == total_records):
                    percent = 45 + int((processed / total_records) * 40)
                    percent = min(percent, 85)
                    progress = {
                        'total': total_records,
                        'processed': processed,
                        'stage': f'[2/3] 궤적 계산 중... ({processed:,}/{total_records:,})',
                        'percent': percent
                    }
                    upload_progress[process_id] = progress
                    save_progress_to_file(process_id, progress)

            if waypoint_batch:
                self.db.execute_batch_insert(
                    """INSERT OR REPLACE INTO waypoint_times
                           (flight_id, waypoint_name, waypoint_sequence, estimated_time)
                           VALUES (?, ?, ?, ?)""",
                    waypoint_batch
                )

            if sector_batch:
                self.db.insert_batch_sector_times(sector_batch)

            elapsed = time.time() - start_time
            logger.info(
                f"[단계 2 완료] {elapsed:.2f}초 내에 {success_count}개 항공편 궤적 계산 → "
                f"{waypoint_total}개 지점 / {sector_total}개 섹터 저장"
            )

            if process_id:
                progress = {
                    'total': total_records,
                    'processed': total_records,
                    'stage': f'[2/3 완료] {success_count:,}개 항공편 궤적 계산 완료',
                    'percent': 85
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            return {
                'status': 'success',
                'message': f'{success_count}개 항공편 궤적 계산 완료',
                'sector_count': sector_total,
                'waypoint_count': waypoint_total,
                'elapsed_time': elapsed
            }

        except Exception as e:
            logger.error(f"궤적 계산 오류: {e}")

            if process_id:
                upload_progress[process_id] = {
                    'total': total_records if 'total_records' in locals() else 0,
                    'processed': 0,
                    'stage': f'계산 오류: {str(e)}',
                    'percent': 33
                }

            return {
                'status': 'error',
                'message': f'궤적 계산 실패: {str(e)}',
                'sector_count': 0,
                'waypoint_count': 0
            }

    def process_and_save_flights(self, flights_data, upload_file_name, file_size, process_id=None):
        """
        업로드된 항공편 데이터를 처리하고 DB에 저장 (전체 파이프라인)

        이 메서드는 다음 단계를 순차적으로 실행합니다:
        1. 항공편 벌크 입력 (초고속)
        2. 궤적 계산 + 지점/섹터 시간 저장
        3. 유사호출 감지

        Args:
            flights_data: 검증된 항공편 데이터 (list of dict)
            upload_file_name: 업로드 파일명
            file_size: 파일 크기 (bytes)
            process_id: 진행 상황 추적 ID (선택사항)

        Returns:
            dict: {'status': 'success'/'error', 'message': str, 'inserted_count': int}
        """
        try:
            import time
            start_time = time.time()
            logger.info(f"[전체 파이프라인] {len(flights_data)}개 항공편 처리 시작")

            # 단계 1: 항공편 벌크 입력
            result1 = self.insert_flights_bulk(flights_data, upload_file_name, file_size, process_id)

            if result1['status'] != 'success':
                return result1

            # 단계 2: 궤적 및 섹터 계산
            result2 = self.calculate_sector_times(flights_data, process_id)
            if result2.get('status') not in ('success', 'warning'):
                return result2

            logger.info(f"[단계 3] 유사호출 감지 시작")
            if process_id:
                progress = {
                    'total': len(flights_data),
                    'processed': len(flights_data),
                    'stage': '[3/3] 유사호출 감지 중...',
                    'percent': 90
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            sim_start = time.time()
            sim_result = self.detect_similarities(process_id=process_id)
            sim_elapsed = time.time() - sim_start
            logger.info(f"[단계 3 완료] {sim_elapsed:.2f}초 내에 유사호출 감지 완료: {sim_result.get('similarity_count', 0)}건")

            if process_id:
                progress = {
                    'total': len(flights_data),
                    'processed': len(flights_data),
                    'stage': f'✅ 완료! ({result1["inserted_count"]:,}개 항공편 + {result2.get("waypoint_count", 0):,}개 지점 + {result2.get("sector_count", 0):,}개 섹터 + {sim_result.get("similarity_count", 0):,}건 감지)',
                    'percent': 100
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            total_time = time.time() - start_time
            logger.info(f"[전체 완료] {total_time:.2f}초 내에 전체 처리 완료")

            return {
                'status': 'success',
                'message': (
                    f"{result1['inserted_count']}개 항공편 입력 + {result2.get('waypoint_count', 0)}개 지점 / "
                    f"{result2.get('sector_count', 0)}개 섹터 계산 + {sim_result.get('similarity_count', 0)}건 유사호출 감지 완료"
                ),
                'inserted_count': result1['inserted_count'],
                'sector_count': result2.get('sector_count', 0),
                'waypoint_count': result2.get('waypoint_count', 0),
                'similarity_count': sim_result.get('similarity_count', 0),
                'total_time': total_time
            }

        except Exception as e:
            logger.error(f"전체 파이프라인 오류: {e}")

            if process_id:
                upload_progress[process_id] = {
                    'total': len(flights_data),
                    'processed': 0,
                    'stage': f'오류: {str(e)}',
                    'percent': 0
                }

            return {
                'status': 'error',
                'message': f'항공편 처리 실패: {str(e)}',
                'inserted_count': 0
            }

    def detect_similarities(self, min_overlap_minutes=2, process_id=None):
        """
        저장된 항공편 데이터에서 유사호출 감지 및 DB 저장 (최적화 버전)

        Args:
            min_overlap_minutes: 최소 공존시간 (분)
            process_id: 진행 상황 추적 ID (선택사항)

        Returns:
            dict: {'status': 'success'/'error', 'similarity_count': int}
        """
        try:
            import time
            start_time = time.time()
            logger.info("Starting optimized similarity detection...")

            flights = self.db.get_all_flights()
            if not flights:
                return {'status': 'error', 'message': '저장된 항공편이 없습니다'}

            flight_list = list(flights)
            logger.info(f"Total flights: {len(flight_list)}")

            # 날짜별 & 호출부별 버킷 생성을 위한 메타데이터 준비
            flights_by_date = defaultdict(list)
            flight_lookup = {}
            for flight in flight_list:
                callsign = flight.get('callsign', '')
                prefix = extract_callsign_prefix(callsign)
                digits = extract_callsign_digits(callsign)
                meta = dict(flight)
                meta['prefix'] = prefix
                meta['digits'] = digits
                eobd = flight.get('eobd') or 'UNKNOWN'
                flights_by_date[eobd].append(meta)
                flight_lookup[flight['id']] = meta

            total_pairs = sum(len(day_flights) * (len(day_flights) - 1) // 2 for day_flights in flights_by_date.values())

            # 유사 후보 쌍 사전 필터링
            daily_candidate_pairs = {}
            candidate_total = 0
            for eobd, day_flights in flights_by_date.items():
                pairs = self._build_candidate_pairs_for_date(day_flights)
                daily_candidate_pairs[eobd] = pairs
                candidate_total += len(pairs)

            if candidate_total == 0:
                logger.info("No candidate pairs after bucketing; skipping similarity detection.")
                return {'status': 'success', 'message': '유사 후보가 없습니다', 'similarity_count': 0, 'count': 0, 'execution_time': 0}

            reduction_pct = (candidate_total / total_pairs * 100) if total_pairs else 0
            logger.info(f"Candidate pair reduction: {total_pairs:,} → {candidate_total:,} ({reduction_pct:.2f}% of original)")

            # 📌 후보 항공편만 섹터 정보 미리 로드
            logger.info("Preloading sector information for candidate flights...")
            preload_start = time.time()
            sector_cache = {}
            candidate_flight_ids = set()
            for pairs in daily_candidate_pairs.values():
                for fid1, fid2 in pairs:
                    candidate_flight_ids.add(fid1)
                    candidate_flight_ids.add(fid2)

            for flight_id in candidate_flight_ids:
                sector_times = self.db.get_sector_times(flight_id)
                sector_cache[flight_id] = {
                    st['sector_name']: {
                        'entry': datetime.strptime(st['entry_time'], '%H:%M:%S').time(),
                        'exit': datetime.strptime(st['exit_time'], '%H:%M:%S').time()
                    }
                    for st in sector_times
                }
            preload_time = time.time() - preload_start
            logger.info(f"✓ Sector information preloaded: {preload_time:.3f}s (for {len(candidate_flight_ids)} flights)")

            similarity_count = 0
            skip_count = 0  # 섹터 겹침 없어서 스킵한 쌍

            # 성능 측정 변수
            time_sector_check = 0.0
            time_similarity_check = 0.0
            time_overlap_calc = 0.0
            time_db_save = 0.0

            sector_check_count = 0
            similarity_check_count = 0
            overlap_calc_count = 0

            # ============================================================================
            # 통합 처리 방식: 유사도 감지 → 공존 시간 계산 → 즉시 DB 저장 (한 번에 처리)
            # 이전 방식: Stage 1 필터링 → candidate_pairs 임시 저장 → Stage 2 처리 (메모리 비효율)
            # 최적화: 유사호출이 있는 쌍(섹터 동일)만 공존시간 계산하므로 빠름 + 메모리 효율 ✨
            # ============================================================================
            logger.info("Unified Processing: Sector check → Similarity check → Overlap calc → DB save...")
            stage1_start = time.time()

            # 총 쌍의 개수
            processed_pairs = 0

            # 시간 추정용 변수
            first_batch_time = None
            first_batch_pairs = 100  # 처음 100쌍의 시간으로 추정

            # 배치 저장용 리스트
            batch_similarities = []
            batch_size = 500  # 500개씩 배치 저장
            for eobd, pairs in daily_candidate_pairs.items():
                for flight1_id, flight2_id in pairs:
                    flight1 = flight_lookup.get(flight1_id)
                    flight2 = flight_lookup.get(flight2_id)
                    processed_pairs += 1

                    if not flight1 or not flight2:
                        continue

                    call1 = flight1['callsign']
                    call2 = flight2['callsign']

                    t1 = time.time()
                    sectors1 = sector_cache.get(flight1_id, {})
                    sectors2 = sector_cache.get(flight2_id, {})
                    common_sectors = set(sectors1.keys()) & set(sectors2.keys())
                    time_sector_check += time.time() - t1
                    sector_check_count += 1

                    if not common_sectors:
                        skip_count += 1
                        continue

                    t2 = time.time()
                    level, score = check_similarity(call1, call2)
                    time_similarity_check += time.time() - t2
                    similarity_check_count += 1

                    if not level:
                        skip_count += 1
                        continue

                    t3 = time.time()
                    overlaps = calculate_sector_overlaps_from_dict(
                        sectors1,
                        sectors2,
                        min_overlap_minutes,
                        flight1.get('eobd')
                    )
                    time_overlap_calc += time.time() - t3
                    overlap_calc_count += 1

                    if not overlaps:
                        skip_count += 1
                        continue

                    t4 = time.time()
                    has_overlap = len(overlaps) > 0
                    total_overlap = sum(o['overlap_minutes'] for o in overlaps)
                    overlap_count = len(overlaps)

                    batch_similarities.append({
                        'flight_id_1': flight1_id,
                        'flight_id_2': flight2_id,
                        'callsign_1': call1,
                        'callsign_2': call2,
                        'level': level,
                        'score': score,
                        'has_overlap': has_overlap,
                        'total_overlap': total_overlap,
                        'overlap_count': overlap_count,
                        'overlaps': overlaps
                    })

                    similarity_count += 1
                    time_db_save += time.time() - t4

                    if len(batch_similarities) >= batch_size:
                        self._save_similarity_batch(batch_similarities)
                        batch_similarities = []

                    if processed_pairs == first_batch_pairs and first_batch_time is None:
                        first_batch_time = time.time() - stage1_start
                        avg_time_per_pair = first_batch_time / first_batch_pairs
                        estimated_total_time = avg_time_per_pair * candidate_total
                        remaining_pairs = candidate_total - processed_pairs
                        estimated_remaining_time = max(0, estimated_total_time - first_batch_time)
                        logger.info(
                            f"⏱️  [시간 추정] 처음 100쌍: {first_batch_time:.1f}초 → 전체 예상: {estimated_total_time:.0f}초 ({estimated_total_time/60:.1f}분), 남은 시간: ~{estimated_remaining_time/60:.1f}분"
                        )

                    if processed_pairs % 10000 == 0 or processed_pairs == candidate_total:
                        elapsed = time.time() - start_time
                        progress_pct = (processed_pairs / candidate_total * 100) if candidate_total else 0

                        if processed_pairs > 10:
                            current_avg_time = elapsed / processed_pairs
                            estimated_total = current_avg_time * candidate_total
                            estimated_remaining = max(0, estimated_total - elapsed)
                            rem_min = estimated_remaining / 60
                            status_msg = (
                                f"📊 진행: {progress_pct:.1f}% ({processed_pairs:,}/{candidate_total:,} 후보) | 유사호출: {similarity_count} | 남은 시간: ~{rem_min:.1f}분"
                            )
                            logger.info(status_msg)

                            if process_id:
                                actual_pct = 85 + (progress_pct * 0.15)
                                progress = {
                                    'total': candidate_total,
                                    'processed': processed_pairs,
                                    'stage': f'[3/3] 유사호출 감지 중... ({progress_pct:.1f}%, 약 {rem_min:.1f}분 남음)',
                                    'percent': min(99, int(actual_pct))
                                }
                                upload_progress[process_id] = progress
                                save_progress_to_file(process_id, progress)

            # 마지막 배치 저장
            if batch_similarities:
                self._save_similarity_batch(batch_similarities)

            unified_time = time.time() - stage1_start
            logger.info(f"✓ Unified processing completed: {similarity_count} similarities saved ({unified_time:.3f}s")

            # 통계 캐시 업데이트
            self.db.cache_statistics()

            total_time = time.time() - start_time
            total_pairs = len(flight_list) * (len(flight_list) - 1) // 2
            skip_rate = (skip_count / total_pairs * 100) if total_pairs > 0 else 0

            logger.info(f"\n{'='*70}")
            logger.info(f"✅ Similarity detection completed!")
            logger.info(f"{'='*70}")
            logger.info(f"📊 Results:")
            logger.info(f"   • Found: {similarity_count} similarities")
            logger.info(f"   • Skipped: {skip_count} pairs ({skip_rate:.1f}%)")
            logger.info(f"\n⏱️  Performance Breakdown:")
            logger.info(f"   1️⃣ Sector preload: {preload_time:.3f}s ({preload_time/total_time*100:.1f}%)")
            if sector_check_count > 0:
                logger.info(f"   2️⃣ Sector check (모든 쌍): {time_sector_check:.3f}s ({time_sector_check/total_time*100:.1f}%) - {sector_check_count}회")
                logger.info(f"      └─ 평균: {time_sector_check/sector_check_count*1000:.3f}ms/회")
            if similarity_check_count > 0:
                logger.info(f"   3️⃣ Similarity check (겹치는 쌍): {time_similarity_check:.3f}s ({time_similarity_check/total_time*100:.1f}%) - {similarity_check_count}회")
                logger.info(f"      └─ 평균: {time_similarity_check/similarity_check_count*1000:.3f}ms/회")
            if overlap_calc_count > 0:
                logger.info(f"   4️⃣ Overlap calc (유사도 있는 쌍): {time_overlap_calc:.3f}s ({time_overlap_calc/total_time*100:.1f}%) - {overlap_calc_count}회")
                logger.info(f"      └─ 평균: {time_overlap_calc/overlap_calc_count*1000:.3f}ms/회")
            if similarity_count > 0:
                logger.info(f"   5️⃣ DB save (최종 저장): {time_db_save:.3f}s ({time_db_save/total_time*100:.1f}%) - {similarity_count}회")
                logger.info(f"      └─ 평균: {time_db_save/similarity_count*1000:.3f}ms/회")
            logger.info(f"\n   Total time: {total_time:.3f}s")
            logger.info(f"{'='*70}\n")

            return {
                'status': 'success',
                'message': f'{similarity_count}개의 유사호출 감지',
                'similarity_count': similarity_count,
                'count': similarity_count,  # CLI 호환성을 위해 추가
                'skipped_count': skip_count,
                'execution_time': total_time
            }

        except Exception as e:
            logger.error(f"Similarity detection error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'유사호출 감지 실패: {str(e)}'
            }

    def _save_similarity_batch(self, batch_similarities):
        """배치로 유사호출 데이터 저장 (DB 접근 최소화)"""
        try:
            for item in batch_similarities:
                # similarities 테이블에 저장
                similarity_id = self.db.insert_similarity(
                    item['flight_id_1'],
                    item['flight_id_2'],
                    item['callsign_1'],
                    item['callsign_2'],
                    item['level'],
                    item['score'],
                    item['has_overlap'],
                    item['total_overlap'],
                    item['overlap_count']
                )

                # 섹터 겹침 상세 정보 저장
                if similarity_id and item['overlaps']:
                    for overlap in item['overlaps']:
                        self.db.insert_sector_overlap(
                            similarity_id,
                            overlap['sector'],
                            overlap['entry1'],
                            overlap['exit1'],
                            overlap['entry2'],
                            overlap['exit2'],
                            overlap['overlap_start'],
                            overlap['overlap_end'],
                            overlap['overlap_minutes']
                        )
        except Exception as e:
            logger.error(f"배치 저장 오류: {e}")


def calculate_sector_overlaps_from_dict(sectors1, sectors2, min_overlap_minutes=2, eobd=None):
    """
    딕셔너리 형식의 섹터 정보로 겹침 계산

    Args:
        sectors1: {'sector_name': {'entry': time, 'exit': time}, ...}
        sectors2: 동일 형식
        min_overlap_minutes: 최소 공존시간
        eobd: 비행 날짜 (DATE 또는 문자열 'YYYY-MM-DD')

    Returns:
        list: 겹침 정보 리스트
    """
    overlaps = []

    if not sectors1 or not sectors2:
        return overlaps

    try:
        from datetime import datetime as dt, date

        # eobd를 date 객체로 변환
        if isinstance(eobd, str):
            base_date = dt.strptime(eobd, '%Y-%m-%d').date()
        elif isinstance(eobd, date):
            base_date = eobd
        else:
            # eobd가 없거나 유효하지 않으면 None을 저장 (데이터베이스에 의존)
            base_date = None

        common_sectors = set(sectors1.keys()) & set(sectors2.keys())

        for sector in common_sectors:
            s1_entry = sectors1[sector]['entry']
            s1_exit = sectors1[sector]['exit']
            s2_entry = sectors2[sector]['entry']
            s2_exit = sectors2[sector]['exit']

            # time을 datetime로 변환 (비교하기 위해)
            if base_date:
                s1_entry_dt = dt.combine(base_date, s1_entry)
                s1_exit_dt = dt.combine(base_date, s1_exit)
                s2_entry_dt = dt.combine(base_date, s2_entry)
                s2_exit_dt = dt.combine(base_date, s2_exit)
            else:
                # base_date가 없으면 현재 날짜 사용
                s1_entry_dt = dt.combine(dt.now().date(), s1_entry)
                s1_exit_dt = dt.combine(dt.now().date(), s1_exit)
                s2_entry_dt = dt.combine(dt.now().date(), s2_entry)
                s2_exit_dt = dt.combine(dt.now().date(), s2_exit)

            overlap_start_dt = max(s1_entry_dt, s2_entry_dt)
            overlap_end_dt = min(s1_exit_dt, s2_exit_dt)

            if overlap_start_dt < overlap_end_dt:
                overlap_duration = overlap_end_dt - overlap_start_dt
                overlap_minutes = int(overlap_duration.total_seconds() / 60)

                if overlap_minutes >= min_overlap_minutes:
                    overlaps.append({
                        'sector': sector,
                        'entry1': s1_entry.strftime('%H:%M'),
                        'exit1': s1_exit.strftime('%H:%M'),
                        'entry2': s2_entry.strftime('%H:%M'),
                        'exit2': s2_exit.strftime('%H:%M'),
                        'overlap_start': overlap_start_dt.isoformat(),  # ISO format datetime
                        'overlap_end': overlap_end_dt.isoformat(),      # ISO format datetime
                        'overlap_minutes': overlap_minutes
                    })

    except Exception as e:
        logger.error(f"Error calculating sector overlaps: {e}")

    return overlaps
