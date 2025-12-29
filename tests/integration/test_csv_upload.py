#!/usr/bin/env python3
"""
CSV 업로드 API 테스트 스크립트
t_flightplan_QUICK_org.csv 파일을 업로드하고 진행 상황을 모니터링합니다.
"""
import requests
import time
import os

# API 서버 주소
API_BASE = "http://localhost:8888"

def upload_csv_file(filepath, mode='replace'):
    """CSV 파일을 업로드하고 process_id를 반환"""
    print(f"\n{'='*80}")
    print(f"📤 CSV 파일 업로드 시작: {os.path.basename(filepath)}")
    print(f"   모드: {mode}")
    print(f"{'='*80}\n")
    
    url = f"{API_BASE}/api/upload/flights"
    
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'text/csv')}
        data = {'mode': mode}
        
        response = requests.post(url, files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 업로드 요청 성공!")
        print(f"   파일명: {result['data']['file_name']}")
        print(f"   레코드 수: {result['data']['record_count']:,}건")
        print(f"   Process ID: {result['data']['process_id']}")
        
        if result['data'].get('warnings'):
            print(f"   ⚠️  경고: {result['data']['warnings']}")
        
        return result['data']['process_id']
    else:
        print(f"❌ 업로드 실패: {response.status_code}")
        print(f"   응답: {response.text}")
        return None

def monitor_progress(process_id, check_interval=2):
    """업로드 진행 상황을 모니터링"""
    print(f"\n{'='*80}")
    print(f"📊 진행 상황 모니터링 시작 (Process ID: {process_id})")
    print(f"{'='*80}\n")
    
    url = f"{API_BASE}/api/upload/progress/{process_id}"
    
    last_stage = ""
    start_time = time.time()
    
    while True:
        try:
            response = requests.get(url)
            
            if response.status_code != 200:
                print(f"❌ 진행 상황 조회 실패: {response.status_code}")
                break
            
            progress = response.json()
            status = progress.get('status')
            stage = progress.get('stage', '')
            percent = progress.get('percent', 0)
            
            # 스테이지가 변경되었을 때만 출력
            if stage != last_stage:
                elapsed = time.time() - start_time
                print(f"[{elapsed:6.1f}초] {percent:3d}% - {stage}")
                last_stage = stage
            
            if status == 'completed':
                print(f"\n{'='*80}")
                print(f"✅ 처리 완료!")
                print(f"   총 소요 시간: {elapsed:.1f}초")
                print(f"{'='*80}\n")
                return True
            
            elif status == 'error':
                print(f"\n{'='*80}")
                print(f"❌ 처리 중 오류 발생: {stage}")
                print(f"{'='*80}\n")
                return False
            
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"❌ 모니터링 오류: {e}")
            time.sleep(check_interval)

def check_results():
    """업로드 결과 확인"""
    print(f"\n{'='*80}")
    print(f"📋 업로드 결과 확인")
    print(f"{'='*80}\n")
    
    # 항공편 수 조회
    try:
        response = requests.get(f"{API_BASE}/api/flights/count")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 저장된 항공편: {result.get('count', 0):,}건")
    except Exception as e:
        print(f"❌ 항공편 수 조회 실패: {e}")
    
    # 유사도 조회
    try:
        response = requests.get(f"{API_BASE}/api/similarities/count")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 감지된 유사호출: {result.get('count', 0):,}건")
    except Exception as e:
        print(f"❌ 유사도 조회 실패: {e}")
    
    # 섹터 통과 시간 조회 (샘플)
    try:
        response = requests.get(f"{API_BASE}/api/flights?limit=1")
        if response.status_code == 200:
            result = response.json()
            if result.get('data') and len(result['data']) > 0:
                flight = result['data'][0]
                print(f"\n📌 샘플 항공편: {flight.get('callsign', 'N/A')}")
                print(f"   출발: {flight.get('dept', 'N/A')} → 도착: {flight.get('dest', 'N/A')}")
                print(f"   경로: {flight.get('route', 'N/A')[:50]}...")
    except Exception as e:
        print(f"❌ 샘플 조회 실패: {e}")
    
    print(f"\n{'='*80}\n")

def main():
    """메인 실행 함수"""
    csv_file = "/Users/sein/Desktop/iccs/similarity_detector/t_flightplan_QUICK_org.csv"
    
    if not os.path.exists(csv_file):
        print(f"❌ 파일을 찾을 수 없습니다: {csv_file}")
        return
    
    # 1. CSV 파일 업로드
    process_id = upload_csv_file(csv_file, mode='replace')
    
    if not process_id:
        print("❌ 업로드 실패")
        return
    
    # 2. 진행 상황 모니터링
    success = monitor_progress(process_id, check_interval=3)
    
    if not success:
        print("❌ 처리 실패")
        return
    
    # 3. 결과 확인
    time.sleep(2)  # DB 쓰기 완료 대기
    check_results()

if __name__ == "__main__":
    main()
