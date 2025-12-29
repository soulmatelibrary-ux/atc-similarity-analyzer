#!/usr/bin/env python3
"""
항공기 프로필 CSV 파일을 데이터베이스에 로드하는 스크립트
data/aircraft_profiles_commercial.csv → aircraft_profiles 테이블
"""

import csv
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CSV_FILE = PROJECT_ROOT / 'data' / 'aircraft_profiles_commercial.csv'
DB_FILE = PROJECT_ROOT / 'database' / 'similarity_detector.db'


def load_aircraft_csv(csv_path, db_path, mode='replace'):
    """
    CSV 파일에서 항공기 프로필을 읽어 데이터베이스에 로드

    Args:
        csv_path: CSV 파일 경로
        db_path: 데이터베이스 파일 경로
        mode: 'replace' (기존 데이터 삭제 후 로드) 또는 'merge' (중복 제외하고 추가)
    """

    if not csv_path.exists():
        logger.error(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
        return False

    if not db_path.exists():
        logger.error(f"데이터베이스를 찾을 수 없습니다: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        logger.info(f"CSV 파일 읽기: {csv_path}")

        # CSV 파일 읽기
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                logger.error("CSV 파일이 비어있습니다")
                return False

            logger.info(f"CSV 컬럼: {reader.fieldnames}")

            for row in reader:
                # 필수 필드 검증
                if not row.get('icao_code'):
                    logger.warning(f"ICAO 코드 누락: {row}")
                    continue

                rows.append(row)

        logger.info(f"CSV에서 {len(rows)}개의 항공기 프로필 읽음")

        if not rows:
            logger.error("CSV 파일에 데이터가 없습니다")
            return False

        # 모드에 따라 처리
        if mode == 'replace':
            logger.info("기존 항공기 프로필 데이터 삭제 중...")
            cursor.execute("DELETE FROM aircraft_profiles")
            conn.commit()
            logger.info("✓ 기존 데이터 삭제 완료")

        # 데이터베이스에 삽입
        now = datetime.now().isoformat()
        inserted = 0
        updated = 0
        skipped = 0

        for row in rows:
            icao_code = row['icao_code'].upper()

            # 기존 데이터 확인
            cursor.execute(
                "SELECT id FROM aircraft_profiles WHERE icao_code = ?",
                (icao_code,)
            )
            existing = cursor.fetchone()

            if existing:
                if mode == 'merge':
                    # 업데이트
                    cursor.execute("""
                        UPDATE aircraft_profiles SET
                            iata_code = ?,
                            manufacturer = ?,
                            model = ?,
                            type_description = ?,
                            default_speed_kmh = ?,
                            default_speed_knots = ?,
                            default_climb_fpm = ?,
                            default_ceiling_fl = ?,
                            notes = ?,
                            updated_at = ?
                        WHERE icao_code = ?
                    """, (
                        row.get('iata_code', ''),
                        row.get('manufacturer', ''),
                        row.get('model', ''),
                        row.get('type_description', ''),
                        int(row.get('default_speed_kmh', 0)) or None,
                        int(row.get('default_speed_knots', 0)) or None,
                        int(row.get('default_climb_fpm', 0)) or None,
                        int(row.get('default_ceiling_fl', 0)) or None,
                        row.get('notes', ''),
                        now,
                        icao_code
                    ))
                    updated += 1
                else:
                    skipped += 1
                    continue
            else:
                # 삽입
                cursor.execute("""
                    INSERT INTO aircraft_profiles
                    (icao_code, iata_code, manufacturer, model, type_description,
                     default_speed_kmh, default_speed_knots, default_climb_fpm,
                     default_ceiling_fl, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    icao_code,
                    row.get('iata_code', ''),
                    row.get('manufacturer', ''),
                    row.get('model', ''),
                    row.get('type_description', ''),
                    int(row.get('default_speed_kmh', 0)) or None,
                    int(row.get('default_speed_knots', 0)) or None,
                    int(row.get('default_climb_fpm', 0)) or None,
                    int(row.get('default_ceiling_fl', 0)) or None,
                    row.get('notes', ''),
                    now,
                    now
                ))
                inserted += 1

        conn.commit()
        conn.close()

        logger.info(f"\n✓ 로드 완료!")
        logger.info(f"  - 삽입: {inserted}개")
        logger.info(f"  - 업데이트: {updated}개")
        logger.info(f"  - 스킵: {skipped}개")
        logger.info(f"  - 총계: {inserted + updated + skipped}개")

        return True

    except sqlite3.Error as e:
        logger.error(f"데이터베이스 오류: {e}")
        return False
    except Exception as e:
        logger.error(f"오류: {e}")
        return False


def list_loaded_aircraft(db_path):
    """로드된 항공기 프로필 목록 출력"""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT icao_code, manufacturer, model, default_speed_kmh, default_climb_fpm, default_ceiling_fl
            FROM aircraft_profiles
            ORDER BY icao_code
            LIMIT 20
        """)

        profiles = cursor.fetchall()
        conn.close()

        if not profiles:
            logger.info("로드된 항공기 프로필이 없습니다")
            return

        logger.info("\n로드된 항공기 프로필 (처음 20개):")
        logger.info(f"{'ICAO':<6} {'제조사':<15} {'모델':<25} {'속도':<8} {'상승':<8} {'천장':<6}")
        logger.info("-" * 80)

        for profile in profiles:
            icao, mfg, model, speed, climb, ceiling = profile
            logger.info(
                f"{icao:<6} {(mfg or '')[:15]:<15} {(model or '')[:25]:<25} "
                f"{speed or 0:>6} {climb or 0:>6} {ceiling or 0:>4}"
            )

    except Exception as e:
        logger.error(f"목록 조회 오류: {e}")


if __name__ == '__main__':
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else 'replace'

    if mode not in ['replace', 'merge']:
        logger.error(f"잘못된 모드: {mode} (replace 또는 merge)")
        sys.exit(1)

    logger.info(f"\n{'='*60}")
    logger.info("항공기 프로필 CSV 로드")
    logger.info(f"{'='*60}\n")

    success = load_aircraft_csv(CSV_FILE, DB_FILE, mode)

    if success:
        list_loaded_aircraft(DB_FILE)
        logger.info(f"\n✓ 완료!")
    else:
        logger.error("\n✗ 로드 실패!")
        sys.exit(1)
