
import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.similarity_engine import check_similarity

def test_case(c1, c2, expected_level):
    level, ed = check_similarity(c1, c2)
    result = "PASS" if level == expected_level else "FAIL"
    print(f"[{result}] {c1} vs {c2} -> Expected: {expected_level or 'None'}, Actual: {level or 'None'}")
    return level == expected_level

if __name__ == "__main__":
    print("Verifying LEVEL_3-6 modification...")
    
    # 1. Matching prefix (2+ chars) and matching last two digits
    s1 = test_case("KAL123", "KAE423", "LEVEL_3-6") # KA matches, 23 matches
    
    # 2. Non-matching prefix
    s2 = test_case("KAL123", "AAL123", "LEVEL_4-1") # AA != KA, but n1 == n2 (123 == 123) is LEVEL_4-1
    s2_alt = test_case("KAL123", "AAL423", "LEVEL_3-1") # AA != KA, 23 matches, ed=2, so it's LEVEL_3-1
    
    # 3. Short prefix (length 1)
    s4 = test_case("K123", "K423", "LEVEL_3-1") # Prefix is 'K' (len 1), doesn't trigger LEVEL_3-6, but 23 matches and ed=1
    
    # 4. Exactly 2 matching prefix characters
    s5 = test_case("KA123", "KA423", "LEVEL_3-6") # KA matches, 23 matches
    
    # 5. Last two digits not matching
    s6 = test_case("KAL123", "KAE124", "") # KA matches, but 23 != 24. Wait, "level 3-8" is 3 consecutive digits. 
    # Let's check KAL123 vs KAE456
    s7 = test_case("KAL123", "KAE456", "") # KA matches, but 23 != 56
    
    if all([s1, s2, s2_alt, s4, s5, s7]):
        print("\nAll LEVEL_3-6 verification tests passed!")
    else:
        print("\nSome tests failed!")
        sys.exit(1)
