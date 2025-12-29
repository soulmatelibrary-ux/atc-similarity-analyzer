"""
SQLite 데이터베이스 관리자
- 데이터베이스 초기화 및 마이그레이션
- CRUD 작업 관리
"""
import sqlite3
import os
from datetime import datetime
from pathlib import Path
import json
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path='database/similarity_detector.db'):
        self.db_path = db_path
        self._ensure_db_exists()
        self._init_schema()

    def _ensure_db_exists(self):
        """데이터베이스 파일이 없으면 생성"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

    def _init_schema(self):
        """스키마 초기화"""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_path):
            logger.error(f"Schema file not found: {schema_path}")
            return

        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            conn.commit()
            conn.close()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")

    def get_connection(self):
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)  # 30초 타임아웃
        conn.row_factory = sqlite3.Row
        # WAL 모드 활성화 (동시성 개선)
        conn.execute("PRAGMA journal_mode=WAL")
        # 동시성 최적화
        conn.execute("PRAGMA synchronous=NORMAL")  # 더 빠른 쓰기
        conn.execute("PRAGMA cache_size=10000")    # 캐시 크기 증가
        conn.execute("PRAGMA temp_store=MEMORY")   # 임시 데이터를 메모리에 저장
        return conn

    @contextmanager
    def get_connection_context(self):
        """Context manager로 데이터베이스 연결 관리 (자동 close)"""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query, params=None):
        """SELECT 쿼리 실행"""
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution error: {e}", exc_info=True)
            return []

    def execute_insert(self, query, params=None):
        """INSERT 쿼리 실행"""
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Insert execution error: {e}", exc_info=True)
            return None

    def execute_batch_insert(self, query, params_list):
        """배치 INSERT 쿼리 실행 (성능 최적화)

        Args:
            query: INSERT 쿼리 (?, ? 플레이스홀더 포함)
            params_list: [(param1, param2, ...), ...] 리스트

        Returns:
            list: 삽입된 행의 ID 리스트
        """
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                last_ids = []
                for params in params_list:
                    cursor.execute(query, params)
                    last_ids.append(cursor.lastrowid)
                conn.commit()
                return last_ids
        except Exception as e:
            logger.error(f"Batch insert execution error: {e}", exc_info=True)
            return []

    def insert_batch_flights(self, flights_data):
        """대량 항공편 데이터 삽입 (벌크 INSERT - 초고속)

        Args:
            flights_data: [{'CALLSIGN': ..., 'DEPT_AIRPORT_CD': ..., ...}, ...] 리스트

        Returns:
            dict: {'ids': [id1, id2, ...], 'count': int}
        """
        if not flights_data:
            return {'ids': [], 'count': 0}

        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                batch_size = 100
                all_ids = []

                for batch_idx in range(0, len(flights_data), batch_size):
                    batch = flights_data[batch_idx:batch_idx + batch_size]

                    # 다중 행 INSERT 쿼리 생성: INSERT INTO ... VALUES (?, ...), (?, ...), ...
                    placeholders = ','.join(['(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'] * len(batch))
                    query = f"""
                    INSERT INTO flights (
                        callsign, dept_airport_cd, dest_airport_cd, aircraft_type,
                        spd, alt, enr, info_cn, eet, eobd, eobt, raw_sector_times
                    ) VALUES {placeholders}
                    """

                    # 파라미터 평탄화
                    params = []
                    for flight_data in batch:
                        params.extend([
                            flight_data.get('CALLSIGN'),
                            flight_data.get('DEPT_AIRPORT_CD'),
                            flight_data.get('DEST_AIRPORT_CD'),
                            flight_data.get('AIRCRAFT_TYPE'),
                            flight_data.get('SPD'),
                            flight_data.get('ALT'),
                            flight_data.get('ENR'),
                            flight_data.get('INFO_CN'),
                            flight_data.get('EET'),
                            flight_data.get('EOBD'),
                            flight_data.get('EOBT'),
                            flight_data.get('SECTOR_PASSAGE_TIMES')
                        ])

                    try:
                        cursor.execute(query, params)
                        last_id = cursor.lastrowid
                        batch_ids = list(range(last_id - len(batch) + 1, last_id + 1))
                        all_ids.extend(batch_ids)
                        logger.debug(f"Batch inserted: {len(batch)} flights (IDs: {batch_ids[0]}-{batch_ids[-1]})")
                    except Exception as e:
                        logger.error(f"Batch insert failed: {e}", exc_info=True)
                        # 실패한 배치는 개별 처리
                        for flight_data in batch:
                            try:
                                cursor.execute("""
                                    INSERT INTO flights (
                                        callsign, dept_airport_cd, dest_airport_cd, aircraft_type,
                                        spd, alt, enr, info_cn, eet, eobd, eobt, raw_sector_times
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, [
                                    flight_data.get('CALLSIGN'),
                                    flight_data.get('DEPT_AIRPORT_CD'),
                                    flight_data.get('DEST_AIRPORT_CD'),
                                    flight_data.get('AIRCRAFT_TYPE'),
                                    flight_data.get('SPD'),
                                    flight_data.get('ALT'),
                                    flight_data.get('ENR'),
                                    flight_data.get('INFO_CN'),
                                    flight_data.get('EET'),
                                    flight_data.get('EOBD'),
                                    flight_data.get('EOBT'),
                                    flight_data.get('SECTOR_PASSAGE_TIMES')
                                ])
                                all_ids.append(cursor.lastrowid)
                            except Exception as inner_e:
                                logger.warning(f"Failed to insert flight {flight_data.get('CALLSIGN')}: {inner_e}")

                conn.commit()
                logger.info(f"Batch flight insertion completed: {len(all_ids)} flights")
                return {'ids': all_ids, 'count': len(all_ids)}

        except Exception as e:
            logger.error(f"Batch flight insertion error: {e}", exc_info=True)
            return {'ids': [], 'count': 0}

    def execute_update(self, query, params=None):
        """UPDATE 쿼리 실행"""
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Update execution error: {e}", exc_info=True)
            return 0

    def execute_delete(self, query, params=None):
        """DELETE 쿼리 실행"""
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or [])
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Delete execution error: {e}", exc_info=True)
            return 0

    # ========================================================================
    # Flights 테이블 작업
    # ========================================================================

    def insert_flight(self, flight_data):
        """항공편 데이터 삽입"""
        query = """
        INSERT INTO flights (
            callsign, dept_airport_cd, dest_airport_cd, aircraft_type,
            spd, alt, enr, info_cn, eet, eobd, eobt, raw_sector_times
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            flight_data.get('CALLSIGN'),
            flight_data.get('DEPT_AIRPORT_CD'),
            flight_data.get('DEST_AIRPORT_CD'),
            flight_data.get('AIRCRAFT_TYPE'),
            flight_data.get('SPD'),
            flight_data.get('ALT'),
            flight_data.get('ENR'),
            flight_data.get('INFO_CN'),
            flight_data.get('EET'),
            flight_data.get('EOBD'),
            flight_data.get('EOBT'),
            flight_data.get('SECTOR_PASSAGE_TIMES')
        )

        return self.execute_insert(query, params)

    def get_flight(self, flight_id):
        """항공편 조회"""
        query = "SELECT * FROM flights WHERE id = ?"
        results = self.execute_query(query, (flight_id,))
        return dict(results[0]) if results else None

    def get_all_flights(self, limit=None):
        """모든 항공편 조회"""
        query = "SELECT * FROM flights ORDER BY id DESC"
        if limit:
            query += f" LIMIT {limit}"
        results = self.execute_query(query)
        return [dict(row) for row in results]

    # ========================================================================
    # Sector Times 테이블 작업
    # ========================================================================

    def insert_sector_time(self, flight_id, sector_name, entry_time, exit_time):
        """섹터 진입진출 시간 삽입"""
        query = """
        INSERT INTO sector_times (flight_id, sector_name, entry_time, exit_time)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(flight_id, sector_name) DO UPDATE SET
            entry_time = excluded.entry_time,
            exit_time = excluded.exit_time
        """
        params = (flight_id, sector_name, entry_time, exit_time)
        return self.execute_insert(query, params)

    def insert_batch_sector_times(self, sector_times_list):
        """배치로 여러 섹터 시간 삽입 (성능 최적화)

        Args:
            sector_times_list: [(flight_id, sector_name, entry_time, exit_time), ...] 리스트
        """
        query = """
        INSERT INTO sector_times (flight_id, sector_name, entry_time, exit_time)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(flight_id, sector_name) DO UPDATE SET
            entry_time = excluded.entry_time,
            exit_time = excluded.exit_time
        """
        return self.execute_batch_insert(query, sector_times_list)

    def get_sector_times(self, flight_id):
        """항공편의 모든 섹터 시간 조회"""
        query = "SELECT * FROM sector_times WHERE flight_id = ? ORDER BY sector_name"
        results = self.execute_query(query, (flight_id,))
        return [dict(row) for row in results]

    # ========================================================================
    # Similarities 테이블 작업
    # ========================================================================

    def insert_similarity(self, flight_id_1, flight_id_2, callsign_1, callsign_2,
                         level, score, has_overlap=False, overlap_minutes=0, overlap_count=0):
        """유사호출 감지 결과 삽입"""
        query = """
        INSERT INTO similarities (
            flight_id_1, flight_id_2, callsign_1, callsign_2,
            similarity_level, similarity_score,
            has_sector_overlap, total_overlap_minutes, overlap_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            flight_id_1, flight_id_2, callsign_1, callsign_2,
            level, score, has_overlap, overlap_minutes, overlap_count
        )

        return self.execute_insert(query, params)

    def get_similarities(self, min_overlap_minutes=2, limit=100):
        """유사호출 조회 (섹터 겹침 필터)"""
        query = """
        SELECT * FROM similarities
        WHERE has_sector_overlap = 1
        AND total_overlap_minutes >= ?
        ORDER BY total_overlap_minutes DESC, detected_at DESC
        LIMIT ?
        """
        results = self.execute_query(query, (min_overlap_minutes, limit))
        return [dict(row) for row in results]

    def get_similarity_details(self, similarity_id):
        """유사호출 상세 정보 조회"""
        query = """
        SELECT
            s.*,
            f1.callsign as flight1_callsign,
            f2.callsign as flight2_callsign
        FROM similarities s
        JOIN flights f1 ON s.flight_id_1 = f1.id
        JOIN flights f2 ON s.flight_id_2 = f2.id
        WHERE s.id = ?
        """
        results = self.execute_query(query, (similarity_id,))
        if results:
            similarity = dict(results[0])

            # 섹터 겹침 상세 정보 조회
            overlap_query = "SELECT * FROM sector_overlaps WHERE similarity_id = ?"
            overlap_results = self.execute_query(overlap_query, (similarity_id,))
            similarity['sector_overlaps'] = [dict(row) for row in overlap_results]

            return similarity
        return None

    # ========================================================================
    # Sector Overlaps 테이블 작업
    # ========================================================================

    def insert_sector_overlap(self, similarity_id, sector_name,
                             flight1_entry, flight1_exit,
                             flight2_entry, flight2_exit,
                             overlap_start, overlap_end, overlap_minutes):
        """섹터 겹침 정보 삽입"""
        query = """
        INSERT INTO sector_overlaps (
            similarity_id, sector_name,
            flight1_entry, flight1_exit,
            flight2_entry, flight2_exit,
            overlap_start, overlap_end, overlap_minutes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            similarity_id, sector_name,
            flight1_entry, flight1_exit,
            flight2_entry, flight2_exit,
            overlap_start, overlap_end, overlap_minutes
        )

        return self.execute_insert(query, params)

    # ========================================================================
    # 통계 작업
    # ========================================================================

    def get_statistics(self):
        """전체 통계 조회"""
        stats = {}

        # 총 항공편 수
        result = self.execute_query("SELECT COUNT(*) as count FROM flights")
        stats['total_flights'] = dict(result[0])['count'] if result else 0

        # 총 유사호출 쌍
        result = self.execute_query("SELECT COUNT(*) as count FROM similarities")
        stats['total_similarities'] = dict(result[0])['count'] if result else 0

        # 섹터 겹침이 있는 유사호출
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM similarities WHERE has_sector_overlap = 1"
        )
        stats['similarities_with_overlap'] = dict(result[0])['count'] if result else 0

        # 유사도 레벨별 분포
        result = self.execute_query("""
            SELECT similarity_level, COUNT(*) as count
            FROM similarities
            GROUP BY similarity_level
            ORDER BY count DESC
        """)
        stats['level_distribution'] = {
            dict(row)['similarity_level']: dict(row)['count'] for row in result
        }

        # 섹터별 겹침 통계
        result = self.execute_query("""
            SELECT sector_name, COUNT(*) as count, AVG(overlap_minutes) as avg_minutes
            FROM sector_overlaps
            GROUP BY sector_name
            ORDER BY count DESC
        """)
        stats['sector_statistics'] = [dict(row) for row in result]

        # 공존시간별 분포
        result = self.execute_query("""
            SELECT
                CASE
                    WHEN overlap_minutes < 5 THEN '5분 미만'
                    WHEN overlap_minutes < 10 THEN '5-10분'
                    WHEN overlap_minutes < 15 THEN '10-15분'
                    ELSE '15분 이상'
                END as time_range,
                COUNT(*) as count
            FROM sector_overlaps
            GROUP BY time_range
        """)
        stats['overlap_time_distribution'] = {dict(row)['time_range']: dict(row)['count'] for row in result}

        # 유사호출별 겹침 섹터 개수 분포
        result = self.execute_query("""
            SELECT overlap_count, COUNT(*) as count
            FROM similarities
            WHERE overlap_count > 0
            GROUP BY overlap_count
            ORDER BY overlap_count ASC
        """)
        stats['overlap_count_distribution'] = {
            str(dict(row)['overlap_count']): dict(row)['count'] for row in result
        }

        # 2개 이상 섹터에서 겹친 유사호출 쌍의 개수
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM similarities WHERE overlap_count >= 2"
        )
        stats['cross_sector_overlap_pairs'] = dict(result[0])['count'] if result else 0

        return stats

    def cache_statistics(self):
        """통계를 캐시에 저장"""
        stats = self.get_statistics()
        query = """
        INSERT INTO statistics_cache (cache_key, cache_value, expires_at)
        VALUES (?, ?, datetime('now', '+60 minutes'))
        ON CONFLICT(cache_key) DO UPDATE SET
            cache_value = excluded.cache_value,
            cached_at = CURRENT_TIMESTAMP,
            expires_at = excluded.expires_at
        """

        self.execute_insert(query, ('overall_statistics', json.dumps(stats, ensure_ascii=False)))
        logger.info("Statistics cached")

    def get_cached_statistics(self):
        """캐시된 통계 조회"""
        query = """
        SELECT cache_value FROM statistics_cache
        WHERE cache_key = 'overall_statistics'
        AND expires_at > datetime('now')
        """
        results = self.execute_query(query)
        if results:
            return json.loads(dict(results[0])['cache_value'])
        return None

    # ========================================================================
    # 업로드 이력
    # ========================================================================

    def record_upload(self, file_name, file_size, record_count, status='completed', error_msg=None):
        """업로드 이력 기록"""
        query = """
        INSERT INTO upload_history (file_name, file_size, record_count, status, error_message)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (file_name, file_size, record_count, status, error_msg)
        return self.execute_insert(query, params)

    def get_upload_history(self, limit=10):
        """업로드 이력 조회"""
        query = """
        SELECT * FROM upload_history
        ORDER BY uploaded_at DESC
        LIMIT ?
        """
        results = self.execute_query(query, (limit,))
        return [dict(row) for row in results]

    # ========================================================================
    # 항공기 기종 프로필 (Aircraft Profiles)
    # ========================================================================

    def get_aircraft_profile(self, icao_code):
        """
        기종 프로필 조회 (ICAO 코드 기준)

        Args:
            icao_code: ICAO 항공기 코드 (e.g., 'B77L', 'A321')

        Returns:
            dict: {icao_code, iata_code, manufacturer, model, default_speed_kmh,
                   default_climb_fpm, default_ceiling_fl, ...}
        """
        query = """
        SELECT * FROM aircraft_profiles
        WHERE icao_code = ?
        """
        results = self.execute_query(query, (icao_code,))
        rows = list(results)
        if rows:
            return dict(rows[0])
        return None

    def get_all_aircraft_profiles(self, limit=None):
        """
        모든 항공기 기종 프로필 조회

        Returns:
            list: 기종 프로필 리스트
        """
        query = """
        SELECT * FROM aircraft_profiles
        ORDER BY manufacturer, model
        """
        if limit:
            query += f" LIMIT {limit}"

        results = self.execute_query(query)
        return [dict(row) for row in results]

    def insert_aircraft_profile(self, icao_code, iata_code, manufacturer, model,
                               type_description, default_speed_kmh, default_speed_knots,
                               default_climb_fpm, default_ceiling_fl, notes=None):
        """
        항공기 기종 프로필 추가

        Args:
            icao_code: ICAO 코드 (필수, UNIQUE)
            iata_code: IATA 코드
            manufacturer: 제조사
            model: 모델명
            type_description: 설명
            default_speed_kmh: 기본 속도 (km/h)
            default_speed_knots: 기본 속도 (knots)
            default_climb_fpm: 기본 상승률 (feet/minute)
            default_ceiling_fl: 최대 고도 (Flight Level)
            notes: 비고
        """
        query = """
        INSERT OR REPLACE INTO aircraft_profiles
        (icao_code, iata_code, manufacturer, model, type_description,
         default_speed_kmh, default_speed_knots, default_climb_fpm,
         default_ceiling_fl, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """
        params = (icao_code, iata_code, manufacturer, model, type_description,
                  default_speed_kmh, default_speed_knots, default_climb_fpm,
                  default_ceiling_fl, notes)
        return self.execute_insert(query, params)

    def update_aircraft_profile(self, icao_code, **kwargs):
        """
        항공기 기종 프로필 업데이트

        Args:
            icao_code: ICAO 코드
            **kwargs: 업데이트할 필드들
                - iata_code, manufacturer, model, type_description
                - default_speed_kmh, default_speed_knots
                - default_climb_fpm, default_ceiling_fl, notes
        """
        allowed_fields = {
            'iata_code', 'manufacturer', 'model', 'type_description',
            'default_speed_kmh', 'default_speed_knots',
            'default_climb_fpm', 'default_ceiling_fl', 'notes'
        }

        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not update_fields:
            raise ValueError("No valid fields to update")

        # Add updated_at
        update_fields['updated_at'] = 'datetime("now")'

        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys() if k != 'updated_at'])
        set_clause += ", updated_at = datetime('now')"

        query = f"""
        UPDATE aircraft_profiles
        SET {set_clause}
        WHERE icao_code = ?
        """

        params = list(v for k, v in update_fields.items() if k != 'updated_at') + [icao_code]
        return self.execute_update(query, params)

    def delete_aircraft_profile(self, icao_code):
        """
        항공기 기종 프로필 삭제

        Args:
            icao_code: ICAO 코드
        """
        query = "DELETE FROM aircraft_profiles WHERE icao_code = ?"
        return self.execute_delete(query, (icao_code,))

    # ========================================================================
    # 고도 상승 계산 비교 (Climb Calculations)
    # ========================================================================

    def get_climb_calculations(self, flight_id):
        """
        지정된 항공편의 고도 상승 계산 결과 조회

        Args:
            flight_id: 항공편 ID

        Returns:
            list: 지점별 계산 결과
        """
        query = """
        SELECT * FROM climb_calculations
        WHERE flight_id = ?
        ORDER BY waypoint_sequence
        """
        results = self.execute_query(query, (flight_id,))
        return [dict(row) for row in results]

    def get_climb_calculation_statistics(self, flight_id):
        """
        항공편의 고도 상승 계산 통계

        Args:
            flight_id: 항공편 ID

        Returns:
            dict: 평균 시간차, 평균 고도차, 최대 차이 등
        """
        query = """
        SELECT
            COUNT(*) as total_waypoints,
            AVG(time_difference_seconds) as avg_time_diff_seconds,
            MAX(time_difference_seconds) as max_time_diff_seconds,
            AVG(altitude_difference_ft) as avg_alt_diff_ft,
            MAX(altitude_difference_ft) as max_alt_diff_ft
        FROM climb_calculations
        WHERE flight_id = ?
        """
        results = self.execute_query(query, (flight_id,))
        rows = list(results)
        if rows:
            return dict(rows[0])
        return None
