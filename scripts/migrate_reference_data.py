#!/usr/bin/env python3
"""
참조 데이터 마이그레이션 스크립트
enroute.xlsx와 sector1.xlsx 데이터를 데이터베이스로 이전
"""
import os
import sys
import sqlite3
import pandas as pd
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "database" / "similarity_detector.db"
ENROUTE_PATH = PROJECT_ROOT / "data" / "enroute" / "enroute.xlsx"
SECTOR_PATH = PROJECT_ROOT / "data" / "sectors" / "sector1.xlsx"
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema_update.sql"


def migrate_waypoints(conn):
    """enroute.xlsx 데이터를 waypoints 테이블로 마이그레이션"""
    print(f"📍 경유지점 데이터 마이그레이션 시작: {ENROUTE_PATH}")
    
    if not ENROUTE_PATH.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {ENROUTE_PATH}")
        return False
    
    try:
        # Excel 파일 읽기
        df = pd.read_excel(ENROUTE_PATH)
        print(f"   - 총 {len(df)}개 레코드 발견")
        
        # 기존 데이터 삭제
        conn.execute("DELETE FROM waypoints")
        print("   - 기존 데이터 삭제 완료")
        
        # 데이터 삽입
        inserted = 0
        for _, row in df.iterrows():
            try:
                conn.execute("""
                    INSERT INTO waypoints (enr_nm, seq, fixpnt, lat, lon, stat, sector)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row.get('ENR_NM', '') or ''),
                    int(row.get('SEQ', 0)) if pd.notna(row.get('SEQ')) else None,
                    str(row.get('FIXPNT', '') or '').strip().upper(),
                    float(row.get('LAT', 0)),
                    float(row.get('LON', 0)),
                    str(row.get('STAT', '') or ''),
                    str(row.get('SECTOR', '') or '')
                ))
                inserted += 1
            except Exception as e:
                print(f"   ⚠️  레코드 삽입 실패: {e}")
                continue
        
        conn.commit()
        print(f"   ✅ {inserted}개 경유지점 데이터 마이그레이션 완료")
        return True
        
    except Exception as e:
        print(f"❌ 경유지점 마이그레이션 실패: {e}")
        return False


def migrate_sector_boundaries(conn):
    """sector1.xlsx 데이터를 sector_boundaries 테이블로 마이그레이션"""
    print(f"\n🗺️  섹터 경계 데이터 마이그레이션 시작: {SECTOR_PATH}")
    
    if not SECTOR_PATH.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {SECTOR_PATH}")
        return False
    
    try:
        # Excel 파일 읽기 (첫 행이 헤더)
        df = pd.read_excel(SECTOR_PATH)
        
        # 첫 행이 실제 헤더인 경우 처리
        if df.iloc[0, 0] == 'SECTOR_ID':
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
        
        print(f"   - 총 {len(df)}개 레코드 발견")
        
        # 기존 데이터 삭제
        conn.execute("DELETE FROM sector_boundaries")
        print("   - 기존 데이터 삭제 완료")
        
        # 데이터 삽입
        inserted = 0
        for _, row in df.iterrows():
            try:
                sector_id = str(row.get('SECTOR_ID', '') or '').strip()
                if not sector_id or sector_id == 'nan':
                    continue
                    
                conn.execute("""
                    INSERT INTO sector_boundaries (sector_id, seq, lat, lon, alt, alt2)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    sector_id,
                    int(row.get('SEQ', 0)) if pd.notna(row.get('SEQ')) else None,
                    float(row.get('LAT', 0)),
                    float(row.get('LON', 0)),
                    int(row.get('ALT', 0)) if pd.notna(row.get('ALT')) else 0,
                    int(row.get('ALT2', 99999)) if pd.notna(row.get('ALT2')) else 99999
                ))
                inserted += 1
            except Exception as e:
                print(f"   ⚠️  레코드 삽입 실패: {e}")
                continue
        
        conn.commit()
        print(f"   ✅ {inserted}개 섹터 경계 데이터 마이그레이션 완료")
        return True
        
    except Exception as e:
        print(f"❌ 섹터 경계 마이그레이션 실패: {e}")
        return False


def main():
    """메인 마이그레이션 함수"""
    print("=" * 60)
    print("참조 데이터 마이그레이션 시작")
    print("=" * 60)
    print(f"데이터베이스: {DB_PATH}\n")
    
    if not DB_PATH.exists():
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {DB_PATH}")
        print("   먼저 데이터베이스를 초기화하세요.")
        return 1
    
    try:
        # 1. 스키마 먼저 적용
        print("\n📋 데이터베이스 스키마 적용 중...")
        if SCHEMA_PATH.exists():
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            conn = sqlite3.connect(str(DB_PATH))
            conn.executescript(schema_sql)
            conn.close()
            print("   ✅ 스키마 적용 완료")
        else:
            print(f"   ⚠️  스키마 파일을 찾을 수 없습니다: {SCHEMA_PATH}")

        # 2. 데이터베이스 연결
        conn = sqlite3.connect(str(DB_PATH))

        # 3. 마이그레이션 실행
        waypoints_ok = migrate_waypoints(conn)
        sectors_ok = migrate_sector_boundaries(conn)
        
        conn.close()
        
        # 결과 출력
        print("\n" + "=" * 60)
        if waypoints_ok and sectors_ok:
            print("✅ 모든 참조 데이터 마이그레이션 완료!")
            print("=" * 60)
            return 0
        else:
            print("⚠️  일부 마이그레이션 실패")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print(f"\n❌ 마이그레이션 중 오류 발생: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
