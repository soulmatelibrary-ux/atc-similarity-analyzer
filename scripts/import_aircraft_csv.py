#!/usr/bin/env python3
"""
항공기 기종 CSV 파일을 데이터베이스에 로드하는 스크립트
Loads aircraft profiles from CSV to database
"""
import sys
import os
import csv
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager

def import_aircraft_csv(csv_file_path: str, mode: str = 'replace') -> dict:
    """
    CSV 파일에서 항공기 기종을 읽고 데이터베이스에 로드합니다.

    Args:
        csv_file_path: CSV 파일 경로
        mode: 'replace' (기존 데이터 삭제 후 교체) 또는 'merge' (기존 데이터 유지하고 추가)

    Returns:
        dict: 가져오기 결과 통계
    """

    # 파일 존재 확인
    if not os.path.exists(csv_file_path):
        return {
            'success': False,
            'error': f'파일을 찾을 수 없습니다: {csv_file_path}',
            'inserted': 0,
            'updated': 0,
            'skipped': 0
        }

    # 데이터베이스 초기화
    db = DatabaseManager()

    stats = {
        'success': False,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'total': 0
    }

    try:
        # replace 모드인 경우 기존 데이터 삭제
        if mode == 'replace':
            print("기존 항공기 기종 데이터를 삭제하는 중...")
            deleted_count = db.execute_delete("DELETE FROM aircraft_profiles")
            print(f"✓ 기존 데이터 삭제 완료 ({deleted_count}건)")

        # CSV 파일 읽기
        print(f"\nCSV 파일을 읽는 중: {csv_file_path}")

        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                return {
                    **stats,
                    'error': 'CSV 파일이 비어있습니다.',
                    'success': False
                }

            for row_num, row in enumerate(reader, start=2):  # 2부터 시작 (헤더는 1줄)
                try:
                    # ICAO 코드는 필수
                    icao_code = (row.get('icao_code', '') or '').strip().upper()
                    if not icao_code:
                        print(f"  ⊘ 줄 {row_num}: ICAO 코드가 비어있습니다. 스킵합니다.")
                        stats['skipped'] += 1
                        continue

                    stats['total'] += 1

                    # 데이터 준비
                    payload = {
                        'icao_code': icao_code,
                        'iata_code': (row.get('iata_code', '') or '').strip().upper() or None,
                        'manufacturer': (row.get('manufacturer', '') or '').strip() or None,
                        'model': (row.get('model', '') or '').strip() or None,
                        'type_description': (row.get('type_description', '') or '').strip() or None,
                        'default_speed_kmh': parse_int(row.get('default_speed_kmh', '')),
                        'default_speed_knots': parse_int(row.get('default_speed_knots', '')),
                        'default_climb_fpm': parse_int(row.get('default_climb_fpm', '')),
                        'default_ceiling_fl': parse_int(row.get('default_ceiling_fl', '')),
                        'notes': (row.get('notes', '') or '').strip() or None,
                    }

                    # 기존 기종 확인
                    existing = db.get_aircraft_profile(icao_code)

                    if existing:
                        # 업데이트
                        if mode == 'replace' or mode == 'merge':
                            db.update_aircraft_profile(icao_code, payload)
                            stats['updated'] += 1
                            print(f"  ✓ 줄 {row_num}: {icao_code} 업데이트됨")
                    else:
                        # 신규 등록
                        db.create_aircraft_profile(payload)
                        stats['inserted'] += 1
                        print(f"  ✓ 줄 {row_num}: {icao_code} 등록됨")

                except Exception as e:
                    print(f"  ✗ 줄 {row_num}: 오류 발생 - {str(e)}")
                    stats['skipped'] += 1
                    continue

        stats['success'] = True

        # 결과 출력
        print("\n" + "="*60)
        print("가져오기 완료!")
        print("="*60)
        print(f"총 처리: {stats['total']:,}건")
        print(f"신규 등록: {stats['inserted']:,}건")
        print(f"업데이트: {stats['updated']:,}건")
        print(f"스킵됨: {stats['skipped']:,}건")
        print("="*60 + "\n")

        return stats

    except Exception as e:
        print(f"\n✗ 오류: {str(e)}")
        return {
            **stats,
            'success': False,
            'error': str(e)
        }


def parse_int(value: str) -> int | None:
    """문자열을 정수로 변환, 실패시 None 반환"""
    if not value or not str(value).strip():
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='항공기 기종 CSV 파일을 데이터베이스에 로드합니다.'
    )
    parser.add_argument(
        'csv_file',
        help='로드할 CSV 파일 경로'
    )
    parser.add_argument(
        '--mode',
        choices=['replace', 'merge'],
        default='replace',
        help='가져오기 모드: replace (기존 데이터 삭제 후 교체) 또는 merge (기존 데이터 유지하고 추가)'
    )

    args = parser.parse_args()

    result = import_aircraft_csv(args.csv_file, args.mode)

    # 실패시 종료 코드 1 반환
    sys.exit(0 if result['success'] else 1)
