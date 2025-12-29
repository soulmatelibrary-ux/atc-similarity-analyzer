#!/usr/bin/env python3
"""
데이터베이스 스키마 마이그레이션 스크립트
Day 2 구현에서 추가된 컬럼들을 기존 데이터베이스에 적용
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / 'database' / 'similarity_detector.db'

def migrate_flights_table():
    """flights 테이블에 새 컬럼 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 기존 컬럼 확인
    cursor.execute("PRAGMA table_info(flights)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ('calculated_speed_kmh', 'INTEGER'),
        ('speed_source', 'TEXT'),
        ('climb_rate_fpm', 'INTEGER'),
        ('cruise_flight_level', 'INTEGER'),
        ('is_climbing', 'BOOLEAN DEFAULT 0'),
    ]

    migrated = []
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE flights ADD COLUMN {col_name} {col_type}")
                conn.commit()
                migrated.append(col_name)
                print(f"✅ Added column to flights: {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                print(f"❌ Failed to add {col_name}: {e}")
        else:
            print(f"⏭️  Column already exists in flights: {col_name}")

    conn.close()
    return migrated

def migrate_waypoint_times_table():
    """waypoint_times 테이블에 새 컬럼 추가"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 기존 컬럼 확인
    cursor.execute("PRAGMA table_info(waypoint_times)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ('altitude_ft', 'INTEGER'),
        ('is_climbing', 'BOOLEAN DEFAULT 0'),
        ('time_method', 'TEXT'),
    ]

    migrated = []
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE waypoint_times ADD COLUMN {col_name} {col_type}")
                conn.commit()
                migrated.append(col_name)
                print(f"✅ Added column to waypoint_times: {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                print(f"❌ Failed to add {col_name}: {e}")
        else:
            print(f"⏭️  Column already exists in waypoint_times: {col_name}")

    conn.close()
    return migrated

def verify_climb_calculations_table():
    """climb_calculations 테이블 존재 확인"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM climb_calculations")
        count = cursor.fetchone()[0]
        print(f"✅ climb_calculations table exists with {count} rows")
    except sqlite3.OperationalError as e:
        print(f"❌ climb_calculations table not found: {e}")

    conn.close()

def verify_aircraft_profiles_table():
    """aircraft_profiles 테이블 존재 확인"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM aircraft_profiles")
        count = cursor.fetchone()[0]
        print(f"✅ aircraft_profiles table exists with {count} rows")
    except sqlite3.OperationalError as e:
        print(f"❌ aircraft_profiles table not found: {e}")

    conn.close()

def main():
    print("=" * 70)
    print("🔄 데이터베이스 스키마 마이그레이션")
    print("=" * 70)
    print(f"Database: {DB_PATH}\n")

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    print("📋 flights 테이블 마이그레이션")
    print("-" * 70)
    migrate_flights_table()

    print("\n📋 waypoint_times 테이블 마이그레이션")
    print("-" * 70)
    migrate_waypoint_times_table()

    print("\n📋 climb_calculations 테이블 검증")
    print("-" * 70)
    verify_climb_calculations_table()

    print("\n📋 aircraft_profiles 테이블 검증")
    print("-" * 70)
    verify_aircraft_profiles_table()

    # 최종 검증
    print("\n" + "=" * 70)
    print("✅ 마이그레이션 완료! 스키마 검증 중...")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(flights)")
    flights_cols = {row[1] for row in cursor.fetchall()}

    cursor.execute("PRAGMA table_info(waypoint_times)")
    waypoint_cols = {row[1] for row in cursor.fetchall()}

    required_flights = {'calculated_speed_kmh', 'speed_source', 'climb_rate_fpm', 'cruise_flight_level'}
    required_waypoint = {'altitude_ft', 'is_climbing', 'time_method'}

    flights_ok = required_flights.issubset(flights_cols)
    waypoint_ok = required_waypoint.issubset(waypoint_cols)

    if flights_ok:
        print("✅ flights 테이블: 모든 컬럼 추가됨")
    else:
        missing = required_flights - flights_cols
        print(f"❌ flights 테이블: 누락된 컬럼 {missing}")

    if waypoint_ok:
        print("✅ waypoint_times 테이블: 모든 컬럼 추가됨")
    else:
        missing = required_waypoint - waypoint_cols
        print(f"❌ waypoint_times 테이블: 누락된 컬럼 {missing}")

    conn.close()

    if flights_ok and waypoint_ok:
        print("\n🎉 마이그레이션 성공!")
        return 0
    else:
        print("\n⚠️  일부 마이그레이션이 실패했습니다.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
