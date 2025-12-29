#!/usr/bin/env python3
"""
지점 통과시간 데이터 생성 스크립트
flight_processor.py를 사용하여 모든 항공편의 지점 통과시간을 계산합니다.

사용 방법:
1. 백엔드 서버 중지: Ctrl+C (backend/app.py 터미널에서)
2. 이 스크립트 실행: python3 generate_waypoints.py
3. 백엔드 서버 재시작: python3 backend/app.py
"""

import sqlite3
import sys
from pathlib import Path

def regenerate_waypoints():
    """지점 통과시간 데이터 재생성"""
    
    db_path = Path('database/similarity_detector.db')
    
    if not db_path.exists():
        print("❌ 데이터베이스를 찾을 수 없습니다")
        return False
    
    try:
        # pandas, flight_processor 임포트 시도
        try:
            import pandas as pd
            from core.flight_processor import process_flight_data
            from database.db_manager import DatabaseManager
            
            print("📋 CSV에서 데이터 로드 중...")
            fp_df = pd.read_csv('data/t_flightplan.csv', encoding='euc-kr')
            print(f"✓ {len(fp_df)}개 항공편 로드 완료")
            
            print("🔄 지점 통과시간 계산 중...")
            db_manager = DatabaseManager(str(db_path))
            process_flight_data(fp_df, db_manager=db_manager, debug=False)
            
            print("✓ 지점 통과시간 계산 및 저장 완료!")
            return True
            
        except ImportError:
            print("⚠️ pandas 모듈이 없습니다. 간단한 데이터 삽입을 진행합니다...")
            
            # 간단한 샘플 데이터 삽입
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 데이터베이스의 모든 항공편 조회
            cursor.execute("SELECT id, callsign, enr FROM flights WHERE length(waypoint_times) = 0 LIMIT 20")
            flights = cursor.fetchall()
            
            sample_data = {
                'BOVMA': 'BOVMA 0002 DOPKU 0015 EGEDA 0028 PONIK 0042 LAMEN 0055 SADLI 0108 OLMEN 0121',
                'SOORO': 'SOORO 0003 ENGOT 0012 PANSI 0035 PONIK 0046 LAMEN 0055 SADLI 0108',
                'BOPTA': 'BOPTA 0005 BEDES 0010 PONIK 0025 LAMEN 0045 PUD 0052',
                'K91': 'KAKUL 0001 DOPJA 0015 PONIK 0035 LAMEN 0050',
                'B40': 'BOJIS 0002 DOPMA 0012 PONIK 0032 LAMEN 0048 SADLI 0100',
            }
            
            updated = 0
            for flight_id, callsign, route in flights:
                if not route:
                    continue
                
                # 경로에 포함된 첫 번째 샘플 지점 찾기
                for key, waypoint_times in sample_data.items():
                    if key in route:
                        cursor.execute(
                            "UPDATE flights SET waypoint_times = ? WHERE id = ?",
                            (waypoint_times, flight_id)
                        )
                        updated += 1
                        break
            
            conn.commit()
            conn.close()
            
            print(f"✓ {updated}개 항공편에 샘플 지점 데이터 삽입 완료")
            return True
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("지점 통과시간 데이터 생성 유틸리티")
    print("=" * 60)
    
    success = regenerate_waypoints()
    
    if success:
        print("\n✅ 완료! 백엔드를 다시 시작하세요:")
        print("   python3 backend/app.py")
    else:
        print("\n❌ 실패했습니다. 오류를 확인하세요.")
        sys.exit(1)
