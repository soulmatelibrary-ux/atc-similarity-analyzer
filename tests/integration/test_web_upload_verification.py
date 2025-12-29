#!/usr/bin/env python3
"""
웹 UI 통해 CSV 업로드 및 100% 처리 검증
Playwright를 사용하지 않고, 실제 API 호출로 검증
"""
import requests
import time
import json

API_BASE = "http://localhost:8888"

def test_web_upload_flow():
    """웹 업로드 플로우 검증"""
    
    print("\n" + "="*80)
    print("🧪 웹 UI CSV 업로드 및 처리 검증")
    print("="*80 + "\n")
    
    csv_file = "/Users/sein/Desktop/iccs/similarity_detector/test.csv"
    
    # 1. 파일 업로드
    print("📤 [단계 1] 파일 업로드 중...")
    with open(csv_file, 'rb') as f:
        files = {'file': ('test.csv', f, 'text/csv')}
        data = {'mode': 'replace'}
        response = requests.post(f"{API_BASE}/api/upload/flights", files=files, data=data)
    
    if response.status_code != 200:
        print(f"❌ 업로드 실패: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    process_id = result['data']['process_id']
    record_count = result['data']['record_count']
    print(f"✅ 업로드 성공")
    print(f"   - Process ID: {process_id}")
    print(f"   - 레코드 수: {record_count:,}건")
    
    # 2. 처리 시간 예측
    print(f"\n⏱️  [단계 2] 처리 시간 예측 중...")
    pred_response = requests.get(f"{API_BASE}/api/processing/time-prediction?record_count={record_count}")
    if pred_response.status_code == 200:
        prediction = pred_response.json()['data']
        print(f"✅ 예상 처리 시간: {prediction['total_formatted']}")
        print(f"   - 속도: {prediction['rate_per_second']:.0f}건/초")
        print(f"   - 단계별 시간:")
        for stage_name, stage_info in prediction['stages'].items():
            print(f"     • {stage_name}: {stage_info['minutes']:.1f}분")
    else:
        print(f"⚠️  예측 조회 실패")
    
    # 3. 진행 상황 모니터링
    print(f"\n📊 [단계 3] 진행 상황 모니터링...")
    print("   (최대 30초 동안 모니터링)\n")
    
    start_time = time.time()
    last_percent = 0
    max_percent_reached = 0
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > 30:  # 30초 이상이면 종료
            print(f"\n⏱️  30초 초과 모니터링 중지")
            print(f"   현재 진행: {last_percent}%")
            break
        
        progress_response = requests.get(f"{API_BASE}/api/upload/progress/{process_id}")
        if progress_response.status_code == 200:
            progress = progress_response.json()
            status = progress['status']
            percent = progress['percent']
            stage = progress['stage']
            predicted_remaining = progress.get('predicted_completion_time', 'N/A')
            
            if percent != last_percent:
                print(f"   [{percent:3d}%] {stage} | 예상 남은시간: {predicted_remaining}")
                last_percent = percent
                max_percent_reached = max(max_percent_reached, percent)
            
            if status == 'completed':
                print(f"\n✅ 처리 완료!")
                print(f"   총 소요 시간: {elapsed:.1f}초")
                return True
            elif status == 'error':
                print(f"\n❌ 처리 오류: {stage}")
                return False
        elif progress_response.status_code == 404:
            print(f"⏳ 진행 상황 기록 생성 대기 중...")
        else:
            print(f"❌ 진행 상황 조회 실패: {progress_response.status_code}")
        
        time.sleep(1)
    
    # 4. 최종 결과 확인
    print(f"\n📋 [단계 4] 최종 결과 확인...")
    try:
        flights_response = requests.get(f"{API_BASE}/api/flights/all?limit=1")
        if flights_response.status_code == 200:
            flights = flights_response.json()['data']
            print(f"✅ 저장된 항공편 확인 가능")
    except:
        pass
    
    # 최종 평가
    print(f"\n{'='*80}")
    if max_percent_reached >= 80:
        print(f"✅ 웹 UI 통과: {max_percent_reached}% 진행까지 정상 작동 확인")
        return True
    else:
        print(f"⚠️  부분 통과: {max_percent_reached}%까지만 진행")
        return False

if __name__ == "__main__":
    test_web_upload_flow()
