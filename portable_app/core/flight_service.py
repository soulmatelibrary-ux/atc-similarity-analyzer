"""
항공편 데이터 서비스
- 파일 업로드 후 DB 저장
- 지점별 통과시간 및 섹터 진입진출시간 계산
- 유사호출 감지 및 DB 저장
"""
import logging
import json
import os
from datetime import datetime
from database.db_manager import DatabaseManager
from utils.sector_parser import parse_sector_times, calculate_sector_overlaps
from core.similarity_engine import check_similarity
from core import flight_processor

logger = logging.getLogger(__name__)

# 글로벌 진행 상태 저장소 (프로세스 별)
upload_progress = {}

# 진행 상황 저장 디렉토리
PROGRESS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.uploads_progress')
os.makedirs(PROGRESS_DIR, exist_ok=True)

def save_progress_to_file(process_id, progress_data):
    """진행 상황을 파일에 저장"""
    if not process_id:
        return
    try:
        progress_file = os.path.join(PROGRESS_DIR, f'{process_id}.json')
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"진행 상황 저장 오류: {e}")


class FlightService:
    def __init__(self, db_manager=None):
        self.db = db_manager or DatabaseManager()

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
                    'stage': '[1/2] 항공편 벌크 입력 중...',
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
                    'stage': f'[1/2 완료] {inserted_count:,}개 항공편 입력 완료',
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
        """
        저장된 항공편의 섹터 진입진출시간 계산 및 저장 (단계 2)

        Args:
            flights_data: 항공편 데이터 (list of dict)
            process_id: 진행 상황 추적 ID (선택사항)

        Returns:
            dict: {'status': 'success'/'error', 'message': str, 'sector_count': int}
        """
        try:
            import time
            start_time = time.time()

            # 데이터베이스에서 방금 삽입된 항공편 조회
            flights = self.db.get_all_flights()
            if not flights:
                logger.warning("저장된 항공편이 없습니다")
                return {
                    'status': 'warning',
                    'message': '계산할 항공편이 없습니다',
                    'sector_count': 0
                }

            logger.info(f"[단계 2] 섹터 시간 계산 시작: {len(flights)}개 항공편")

            if process_id:
                progress = {
                    'total': len(flights),
                    'processed': 0,
                    'stage': '[2/2] 섹터 진입진출시간 계산 중...',
                    'percent': 46
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            # 섹터 시간 배치 수집
            sector_times_batch = []
            sector_idx = 0

            # 먼저 전체 섹터 수 계산
            total_sectors = 0
            for flight_data in flights_data:
                sector_str = flight_data.get('SECTOR_PASSAGE_TIMES', '')
                eobd = flight_data.get('EOBD', '2025-12-13')
                if sector_str:
                    try:
                        sectors = parse_sector_times(sector_str, eobd)
                        total_sectors += len(sectors)
                    except:
                        pass

            logger.debug(f"총 섹터 수: {total_sectors}")

            # 각 항공편의 섹터 정보 파싱 및 저장
            flight_id_map = {}
            for flight in flights:
                flight_id_map[flight['callsign']] = flight['id']

            for flight_data in flights_data:
                callsign = flight_data.get('CALLSIGN')
                if callsign not in flight_id_map:
                    continue

                flight_id = flight_id_map[callsign]
                sector_str = flight_data.get('SECTOR_PASSAGE_TIMES', '')
                eobd = flight_data.get('EOBD', '2025-12-13')

                if sector_str:
                    try:
                        sectors = parse_sector_times(sector_str, eobd)
                        for sector_name, times in sectors.items():
                            entry_time = times['entry'].strftime('%H:%M:%S')
                            exit_time = times['exit'].strftime('%H:%M:%S')
                            sector_times_batch.append((flight_id, sector_name, entry_time, exit_time))

                            sector_idx += 1
                            if total_sectors > 0 and sector_idx % 5 == 0 and process_id:  # 10 → 5로 변경 (더 자주 업데이트)
                                percent = 46 + int((sector_idx / total_sectors) * 44)
                                progress = {
                                    'total': len(flights),
                                    'processed': sector_idx,
                                    'stage': f'[2/2] 섹터 계산 중... ({sector_idx:,}/{total_sectors:,})',
                                    'percent': min(percent, 98)
                                }
                                upload_progress[process_id] = progress
                                save_progress_to_file(process_id, progress)
                    except Exception as e:
                        logger.warning(f"항공편 {callsign}의 섹터 파싱 오류: {e}")
                        continue

            # 배치로 섹터 시간 삽입
            if sector_times_batch:
                try:
                    self.db.insert_batch_sector_times(sector_times_batch)
                    logger.info(f"[단계 2] {len(sector_times_batch)}개 섹터 시간 저장 완료")
                except Exception as e:
                    logger.error(f"섹터 시간 저장 오류: {e}")
            else:
                logger.warning("저장할 섹터 정보가 없습니다")

            elapsed = time.time() - start_time
            logger.info(f"[단계 2 완료] {elapsed:.2f}초 내에 {len(sector_times_batch)}개 섹터 시간 계산 및 저장")

            if process_id:
                progress = {
                    'total': len(flights),
                    'processed': len(flights),
                    'stage': f'[2/2 완료] {len(sector_times_batch):,}개 섹터 저장 완료',
                    'percent': 99
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            return {
                'status': 'success',
                'message': f'{len(sector_times_batch)}개 섹터 시간 계산 및 저장 완료',
                'sector_count': len(sector_times_batch),
                'elapsed_time': elapsed
            }

        except Exception as e:
            logger.error(f"섹터 계산 오류: {e}")

            if process_id:
                upload_progress[process_id] = {
                    'total': 0,
                    'processed': 0,
                    'stage': f'계산 오류: {str(e)}',
                    'percent': 33
                }

            return {
                'status': 'error',
                'message': f'섹터 시간 계산 실패: {str(e)}',
                'sector_count': 0
            }

    def process_and_save_flights(self, flights_data, upload_file_name, file_size, process_id=None):
        """
        업로드된 항공편 데이터를 처리하고 DB에 저장 (전체 파이프라인)

        이 메서드는 다음 단계를 순차적으로 실행합니다:
        1. 항공편 벌크 입력 (초고속)
        2. 섹터 시간 계산 및 저장
        3. 유사호출 감지 (선택사항)

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

            # 단계 2: 섹터 시간 계산
            result2 = self.calculate_sector_times(flights_data, process_id)

            # 단계 3: 지점별 통과시간 계산 (flight_processor)
            if process_id:
                progress = {
                    'total': len(flights_data),
                    'processed': len(flights_data),
                    'stage': '[3/3] 지점별 통과시간 계산 중...',
                    'percent': 70
                }
                upload_progress[process_id] = progress
                save_progress_to_file(process_id, progress)

            logger.info(f"[단계 3] 지점별 통과시간 계산 시작: flight_processor 실행")
            try:
                # flight_processor 실행 (DB에 직접 저장)
                import time as time_module
                fp_start = time_module.time()

                flight_processor.process_flight_plans(self.db)

                fp_elapsed = time_module.time() - fp_start
                logger.info(f"[단계 3 완료] {fp_elapsed:.2f}초 내에 지점별 통과시간 계산 완료")

                if process_id:
                    progress = {
                        'total': len(flights_data),
                        'processed': len(flights_data),
                        'stage': f'✅ 완료! ({result1["inserted_count"]:,}개 항공편 + {result2["sector_count"]:,}개 섹터 + 지점별 시간)',
                        'percent': 100
                    }
                    upload_progress[process_id] = progress
                    save_progress_to_file(process_id, progress)
            except Exception as fp_error:
                logger.warning(f"[단계 3] flight_processor 실행 중 오류 (무시): {fp_error}")
                # 에러가 발생해도 진행 상황은 완료로 표시
                if process_id:
                    progress = {
                        'total': len(flights_data),
                        'processed': len(flights_data),
                        'stage': f'✅ 기본 완료! ({result1["inserted_count"]:,}개 항공편 + {result2["sector_count"]:,}개 섹터)',
                        'percent': 100
                    }
                    upload_progress[process_id] = progress
                    save_progress_to_file(process_id, progress)

            total_time = time.time() - start_time
            logger.info(f"[전체 완료] {total_time:.2f}초 내에 전체 처리 완료")

            return {
                'status': 'success',
                'message': f'{result1["inserted_count"]}개 항공편 입력 + {result2["sector_count"]}개 섹터 계산 완료',
                'inserted_count': result1['inserted_count'],
                'sector_count': result2['sector_count'],
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

    def detect_similarities(self, min_overlap_minutes=2):
        """
        저장된 항공편 데이터에서 유사호출 감지 및 DB 저장 (최적화 버전)

        최적화 순서:
        1️⃣ 메모리에 모든 항공편의 섹터 정보 미리 로드
        2️⃣ 각 쌍에 대해 섹터 겹침 확인 (메모리 - 빠름)
        3️⃣ 섹터 겹치는 경우만 유사도 검사
        4️⃣ 유사도 있고 겹치면 DB 저장

        Args:
            min_overlap_minutes: 최소 공존시간 (분)

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

            # 📌 최적화: 모든 항공편의 섹터 정보를 메모리에 미리 로드 (한 번만)
            logger.info("Preloading sector information for all flights...")
            preload_start = time.time()
            sector_cache = {}
            for flight in flight_list:
                flight_id = flight['id']
                sector_times = self.db.get_sector_times(flight_id)

                # dict로 변환 (메모리에 캐시)
                sector_cache[flight_id] = {
                    st['sector_name']: {
                        'entry': datetime.strptime(st['entry_time'], '%H:%M:%S').time(),
                        'exit': datetime.strptime(st['exit_time'], '%H:%M:%S').time()
                    }
                    for st in sector_times
                }
            preload_time = time.time() - preload_start
            logger.info(f"✓ Sector information preloaded: {preload_time:.3f}s")

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
            total_pairs = len(flight_list) * (len(flight_list) - 1) // 2
            processed_pairs = 0

            # 시간 추정용 변수
            first_batch_time = None
            first_batch_pairs = 100  # 처음 100쌍의 시간으로 추정

            # 배치 저장용 리스트
            batch_similarities = []
            batch_overlaps = []
            batch_size = 500  # 500개씩 배치 저장

            for i in range(len(flight_list)):
                for j in range(i + 1, len(flight_list)):
                    flight1 = flight_list[i]
                    flight2 = flight_list[j]

                    call1 = flight1['callsign']
                    call2 = flight2['callsign']
                    flight1_id = flight1['id']
                    flight2_id = flight2['id']

                    # 📌 순서 1️⃣: 섹터 겹침 확인 (메모리에서 - 가장 빠름)
                    t1 = time.time()
                    sectors1 = sector_cache.get(flight1_id, {})
                    sectors2 = sector_cache.get(flight2_id, {})

                    # 겹치는 섹터 찾기 (빠른 전처리)
                    common_sectors = set(sectors1.keys()) & set(sectors2.keys())
                    time_sector_check += time.time() - t1
                    sector_check_count += 1

                    if not common_sectors:
                        # 섹터가 겹치지 않으면 즉시 스킵
                        skip_count += 1
                        processed_pairs += 1
                        continue

                    # 📌 순서 2️⃣: 섹터가 겹치면 유사도 검사
                    t2 = time.time()
                    level, score = check_similarity(call1, call2)
                    time_similarity_check += time.time() - t2
                    similarity_check_count += 1

                    if not level:
                        # 유사도가 없으면 스킵
                        skip_count += 1
                        processed_pairs += 1
                        continue

                    # 📌 Step 3️⃣: 공존 시간 계산 (유사호출이 있는 쌍만 처리)
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
                        processed_pairs += 1
                        continue

                    # 📌 Step 4️⃣: 배치에 추가 (즉시 저장 대신 배치 처리)
                    t4 = time.time()
                    has_overlap = len(overlaps) > 0
                    total_overlap = sum(o['overlap_minutes'] for o in overlaps)
                    overlap_count = len(overlaps)

                    # 배치에 추가
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
                    processed_pairs += 1
                    time_db_save += time.time() - t4

                    # 배치 크기 도달시 저장
                    if len(batch_similarities) >= batch_size:
                        self._save_similarity_batch(batch_similarities)
                        batch_similarities = []

                    # 시간 추정 (처음 100쌍 처리 후)
                    if processed_pairs == first_batch_pairs and first_batch_time is None:
                        first_batch_time = time.time() - stage1_start
                        avg_time_per_pair = first_batch_time / first_batch_pairs
                        estimated_total_time = avg_time_per_pair * total_pairs
                        remaining_pairs = total_pairs - processed_pairs
                        estimated_remaining_time = estimated_total_time - first_batch_time
                        logger.info(f"⏱️  [시간 추정] 처음 100쌍: {first_batch_time:.1f}초 → 전체 예상: {estimated_total_time:.0f}초 ({estimated_total_time/60:.1f}분), 남은 시간: ~{estimated_remaining_time/60:.1f}분")

                # 진행상황 로깅 (10개 항공편마다)
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    progress_pct = (processed_pairs / total_pairs * 100) if total_pairs > 0 else 0

                    # 현재 속도 기반 시간 추정
                    if processed_pairs > 10:
                        current_avg_time = elapsed / processed_pairs
                        estimated_total = current_avg_time * total_pairs
                        estimated_remaining = max(0, estimated_total - elapsed)
                        logger.info(f"📊 진행: {progress_pct:.1f}% ({processed_pairs:,}/{total_pairs:,} 쌍) | 유사호출: {similarity_count} | 소요: {elapsed:.1f}초 | 예상: {estimated_total:.0f}초 ({estimated_total/60:.1f}분) | 남은 시간: ~{estimated_remaining/60:.1f}분")

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
