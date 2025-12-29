
import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.similarity_engine import check_similarity

def test_case(name, c1, c2, expected_level):
    level, ed = check_similarity(c1, c2)
    result = "PASS" if level == expected_level else "FAIL"
    print(f"[{result}] {name}: {c1} vs {c2} -> Expected: {expected_level or 'None'}, Actual: {level or 'None'}")
    return level == expected_level

if __name__ == "__main__":
    print("Verifying Reorganized Rules and Modified LEVEL_3-4...")
    
    # Priority Test: LEVEL_4-1 (Group A - High Risk)
    t1 = test_case("LEVEL_4-1 (High)", "KAL123", "AAL123", "LEVEL_4-1")
    
    # Priority Test: LEVEL_2-1 (Group A - High Risk)
    t2 = test_case("LEVEL_2-1 (High)", "KAL0I1", "KAL011", "LEVEL_2-1")
    
    # Priority Test: LEVEL_3-8 (Group A - High Risk)
    t3 = test_case("LEVEL_3-8 (High)", "KAL1234", "KAL1239", "LEVEL_3-8")
    
    # Priority Test: LEVEL_4-2 (Group A - High Risk)
    t4 = test_case("LEVEL_4-2 (High)", "KAL1234", "KAL1254", "LEVEL_4-2") # 3 out of 4 matching: 1, 2, 4. ed=1
    
    # Priority Test: LEVEL_2-2 (Group B - Medium Risk)
    t5 = test_case("LEVEL_2-2 (Medium/Low)", "ABC1", "ABCL", "LEVEL_2-2") # ABC1 vs ABCL (Entirely visual identical after norm)
    
    # Priority Test: LEVEL_3-6 (Group B - Medium Risk)
    t6 = test_case("LEVEL_3-6 (Medium/Low)", "KAL123", "KAE423", "LEVEL_3-6") # KA matches, 23 matches
    
    # Priority Test: LEVEL_3-1 (Group B - Medium Risk)
    t7 = test_case("LEVEL_3-1 (Medium)", "A156", "B256", "LEVEL_3-1") # Prefix length 1, so 3-6 skipped. Last 2 match (56). ed=2.
    
    # Modified Rule: LEVEL_3-4 (Group B - Medium Risk)
    # Requirement: Same Prefix + First and Last Digits Match
    t8 = test_case("LEVEL_3-4 (Modified)", "KAL123", "KAL153", "LEVEL_3-4")
    t8_neg = test_case("LEVEL_3-4 (Negative)", "KAL123", "KAL124", "") # Last digit doesn't match
    
    # Group C - Low Risk
    t9 = test_case("LEVEL_5-1 (Low)", "KAL02", "KAL2", "LEVEL_5-1")
    
    # Final check
    results = [t1, t2, t3, t4, t5, t6, t7, t8, t8_neg, t9]
    if all(results):
        print("\nAll Reorganization and Modification tests passed!")
    else:
        print("\nSome tests failed!")
        sys.exit(1)
