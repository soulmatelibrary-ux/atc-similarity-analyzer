#!/usr/bin/env python3
"""
항공기 기종 프로필을 CSV에서 데이터베이스에 로드하는 스크립트
"""
import os
import sys
import csv
import sqlite3
from pathlib import Path

# 프로젝트 경로 설정
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / 'data'
DB_PATH = DATA_DIR / 'similarity_detector.db'
CSV_FILE = DATA_DIR / 'aircraft_profiles_commercial.csv'

def load_aircraft_profiles():
    """CSV 파일에서 항공기 기종을 읽어 데이터베이스에 저장"""
    
    if not CSV_FILE.exists():
        print(f"❌ CSV 파일을 찾을 수 없습니다: {CSV_FILE}")
        return False
    
    if not DB_PATH.exists():
        print(f"❌ 데이터베이스를 찾을 수 없습니다: {DB_PATH}")
        return False
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # 테이블이 존재하는지 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aircraft_profiles'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("⚠️  테이블이 없습니다. 생성 중...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aircraft_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    icao_code TEXT UNIQUE NOT NULL,
                    iata_code TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    type_description TEXT,
                    default_speed_kmh REAL,
                    default_speed_knots REAL,
                    default_climb_fpm REAL,
                    default_ceiling_fl REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        
        # CSV 파일 읽기
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        print(f"📂 CSV 파일에서 {len(rows)}개의 레코드를 읽었습니다.")
        
        # 기존 데이터 개수 확인
        cursor.execute("SELECT COUNT(*) FROM aircraft_profiles")
        existing_count = cursor.fetchone()[0]
        print(f"💾 현재 데이터베이스에 {existing_count}개의 레코드가 있습니다.")
        
        # 데이터베이스에 삽입
        inserted_count = 0
        skipped_count = 0
        
        for row in rows:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO aircraft_profiles 
                    (icao_code, iata_code, manufacturer, model, type_description, 
                     default_speed_kmh, default_speed_knots, default_climb_fpm, 
                     default_ceiling_fl, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['icao_code'],
                    row['iata_code'],
                    row['manufacturer'],
                    row['model'],
                    row['type_description'],
                    float(row['default_speed_kmh']) if row['default_speed_kmh'] else None,
                    float(row['default_speed_knots']) if row['default_speed_knots'] else None,
                    float(row['default_climb_fpm']) if row['default_climb_fpm'] else None,
                    float(row['default_ceiling_fl']) if row['default_ceiling_fl'] else None,
                    row['notes']
                ))
                inserted_count += 1
            except Exception as e:
                print(f"⚠️  {row['icao_code']} 삽입 실패: {e}")
                skipped_count += 1
        
        conn.commit()
        
        # 최종 개수 확인
        cursor.execute("SELECT COUNT(*) FROM aircraft_profiles")
        final_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ 완료!")
        print(f"   - 삽입된 레코드: {inserted_count}개")
        print(f"   - 스킵된 레코드: {skipped_count}개")
        print(f"   - 데이터베이스 총 레코드: {final_count}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

if __name__ == '__main__':
    success = load_aircraft_profiles()
    sys.exit(0 if success else 1)
