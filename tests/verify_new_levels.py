#!/usr/bin/env python3
"""
재정의된 유사도 레벨 검증 스크립트 (5=고위험, 4=중위험, 3=저위험)
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.similarity_engine import check_similarity

def test_case(name, c1, c2, expected_level):
    level, ed = check_similarity(c1, c2)
    result = "PASS" if level == expected_level else "FAIL"
    print(f"[{result}] {name}")
    print(f"  {c1} vs {c2} -> Expected: {expected_level or 'None'}, Actual: {level or 'None'}")
    return level == expected_level

if __name__ == "__main__":
    print("=" * 80)
    print("재정의된 유사도 레벨 검증 (5=고위험, 4=중위험, 3=저위험)")
    print("=" * 80)
    
    results = []
    
    # ============================================================================
    # LEVEL 5: 고위험 (High Risk)
    # ============================================================================
    print("\n[LEVEL 5: 고위험 (High Risk)]")
    
    # LEVEL 5-1: 알파벳 2글자 이상 일치 + 숫자 완전 동일
    results.append(test_case(
        "LEVEL 5-1 (알파벳 2자+ + 숫자 동일)",
        "KAL123", "KAE123", "LEVEL_5-1"
    ))
    results.append(test_case(
        "LEVEL 5-1 (알파벳 2자+ + 숫자 동일)",
        "AAL456", "AAR456", "LEVEL_5-1"
    ))
    
    # LEVEL 5-2: 같은 항공사 + 시각적 유사
    results.append(test_case(
        "LEVEL 5-2 (같은 항공사 + 시각적 유사)",
        "KAL0I1", "KAL011", "LEVEL_5-2"
    ))
    
    # LEVEL 5-3: 같은 항공사 + 3자리 연속 일치
    results.append(test_case(
        "LEVEL 5-3 (3자리 연속 일치)",
        "KAL1234", "KAL1239", "LEVEL_5-3"
    ))
    
    # LEVEL 5-4: 같은 항공사 + 4자리 중 3자리 일치
    results.append(test_case(
        "LEVEL 5-4 (4자리 중 3자리 일치)",
        "KAL1234", "KAL1254", "LEVEL_5-4"
    ))
    
    # ============================================================================
    # LEVEL 4: 중위험 (Medium Risk)
    # ============================================================================
    print("\n[LEVEL 4: 중위험 (Medium Risk)]")
    
    # LEVEL 4-1: 다른 항공사 + 시각적 유사
    results.append(test_case(
        "LEVEL 4-1 (다른 항공사 + 시각적 유사)",
        "ABC1", "ABCL", "LEVEL_4-1"
    ))
    
    # LEVEL 4-2: 항공사 2자+ 일치 + 마지막 2자리 일치
    results.append(test_case(
        "LEVEL 4-2 (항공사 2자+ + 마지막 2자리)",
        "KAL123", "KAE423", "LEVEL_4-2"
    ))
    
    # LEVEL 4-3: 마지막 2자리 숫자 일치
    results.append(test_case(
        "LEVEL 4-3 (마지막 2자리 일치)",
        "A156", "B256", "LEVEL_4-3"
    ))
    
    # LEVEL 4-4: 같은 항공사 + 첫/마지막 숫자 일치
    results.append(test_case(
        "LEVEL 4-4 (첫/마지막 숫자 일치)",
        "KAL123", "KAL153", "LEVEL_4-4"
    ))
    
    # LEVEL 4-5: 같은 항공사 + 숫자 위치 바뀜 (Transposition)
    results.append(test_case(
        "LEVEL 4-5 (숫자 위치 바뀜)",
        "KAL123", "KAL132", "LEVEL_4-5"
    ))
    
    # ============================================================================
    # LEVEL 3: 저위험 (Low Risk)
    # ============================================================================
    print("\n[LEVEL 3: 저위험 (Low Risk)]")
    
    # LEVEL 3-1: 같은 항공사 + Leading Zero
    results.append(test_case(
        "LEVEL 3-1 (Leading Zero)",
        "KAL02", "KAL2", "LEVEL_3-1"
    ))

    # ============================================================================
    # 결과 요약
    # ============================================================================
    print("\n" + "=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"검증 결과: {passed}/{total} 통과")
    print("=" * 80)
    
    if passed == total:
        print("\n✅ 모든 테스트 통과!")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed}개 테스트 실패")
        sys.exit(1)
