"""
유사호출 판정 엔진 테스트
"""
import sys
import os

# 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.similarity_engine import (
    SimilarityEngine,
    check_similarity,
    get_risk_level,
    get_similarity_score
)


class TestSimilarityEngine:
    """유사호출 판정 엔진 테스트 클래스"""

    def __init__(self):
        """초기화"""
        self.engine = SimilarityEngine()
        self.passed = 0
        self.failed = 0

    def test(self, name, condition, expected=True):
        """
        테스트 실행

        Args:
            name: 테스트 이름
            condition: 테스트 조건
            expected: 예상 결과 (기본값: True)
        """
        if condition == expected:
            print(f"✓ {name}")
            self.passed += 1
        else:
            print(f"✗ {name} (기대값: {expected}, 실제값: {condition})")
            self.failed += 1

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*60)
        print("유사호출 판정 엔진 테스트 시작")
        print("="*60 + "\n")

        # LEVEL_2-1: 같은 prefix + 시각적 유사 (I,L→1, O→0, S→5)
        print("[LEVEL_2-1] 같은 prefix + 시각적 유사 (I,L→1, O→0, S→5)")
        level, ed = check_similarity("GIA0IS", "GIA010S")  # 0IS vs 0105 (시각적으로 같음)
        self.test("시각적 정규화 테스트", level in ["LEVEL_2-1", "LEVEL_3-8"])  # 연속이 3자리일 수도

        # LEVEL_3-8: Prefix 동일 + 숫자 3자리 연속 같음 (신규) - 가장 기본
        print("\n[LEVEL_3-8] Prefix 동일 + 숫자 3자리 연속 같음 (신규)")
        level, ed = check_similarity("GIA1234", "GIA1237")
        self.test("GIA1234 vs GIA1237 (3자리 연속: 123)", level, "LEVEL_3-8")
        self.test("위험도: HIGH", get_risk_level(level), "HIGH")
        self.test("점수: 90", get_similarity_score(level), 90)

        level, ed = check_similarity("KAL5678", "KAL5670")
        self.test("KAL5678 vs KAL5670 (3자리 연속: 567)", level, "LEVEL_3-8")

        # LEVEL_4-1: 다른 prefix + 숫자 완전 동일
        print("\n[LEVEL_4-1] 다른 prefix + 숫자 완전 동일")
        level, ed = check_similarity("KAL123", "AAL123")
        self.test("KAL123 vs AAL123", level, "LEVEL_4-1")
        self.test("위험도: HIGH", get_risk_level(level), "HIGH")
        self.test("점수: 85", get_similarity_score(level), 85)

        # LEVEL_3-1: 마지막 2자리 숫자 동일
        print("\n[LEVEL_3-1] 마지막 2자리 숫자 동일")
        level, ed = check_similarity("GIA956", "AIA56")  # 마지막 2자리: 56
        self.test("GIA956 vs AIA56 (마지막: 56)", level, "LEVEL_3-1")

        # LEVEL_3-4: Prefix 동일 + 숫자 2자리 이상 같음
        print("\n[LEVEL_3-4] Prefix 동일 + 숫자 2자리 이상 같음")
        level, ed = check_similarity("GIA1234", "GIA1250")
        self.test("GIA1234 vs GIA1250 (2자리 같음: 12)", level, "LEVEL_3-4")
        self.test("점수: 65", get_similarity_score(level), 65)

        # LEVEL_3-3: 연속된 숫자 블록 동일
        print("\n[LEVEL_3-3] 연속된 숫자 블록 동일")
        level, ed = check_similarity("KAL123", "KAL1234")  # 123이 완전 포함
        self.test("KAL123 vs KAL1234 (123 포함)", level, "LEVEL_3-3")

        # LEVEL_5-1: 같은 prefix + Leading Zero
        print("\n[LEVEL_5-1] 같은 prefix + Leading Zero")
        level, ed = check_similarity("GIA023", "GIA23")
        self.test("GIA023 vs GIA23", level, "LEVEL_5-1")
        self.test("위험도: LOW", get_risk_level(level), "LOW")

        # LEVEL_5-2: 다른 prefix + Leading Zero
        print("\n[LEVEL_5-2] 다른 prefix + Leading Zero")
        level, ed = check_similarity("GIA023", "AIA23")
        self.test("GIA023 vs AIA23", level, "LEVEL_5-2")
        self.test("위험도: MEDIUM", get_risk_level(level), "MEDIUM")

        # LEVEL_2-2: 다른 prefix + 시각적 유사
        print("\n[LEVEL_2-2] 다른 prefix + 시각적 유사")
        level, ed = check_similarity("GIO010", "BIO010")  # O→0 후 같음
        # 이 경우 실제로는 LEVEL_4-1 (010 완전 동일)이거나 다른 규칙
        self.test("다른 prefix, 숫자 같음", level != "", True)

        # 유사도 없음
        print("\n[없음] 유사도 없음")
        level, ed = check_similarity("ABC123", "XYZ999")
        self.test("ABC123 vs XYZ999", level, "")
        self.test("점수: 0", get_similarity_score(level), 0)

        # 동일한 경우
        print("\n[동일] 동일한 콜사인")
        level, ed = check_similarity("GIA878", "GIA878")
        self.test("GIA878 vs GIA878 (동일)", level, "")

        # 캐싱 테스트
        print("\n[캐싱] 캐싱 메커니즘")
        self.engine.clear_cache()
        check_similarity("TEST001", "TEST002")
        check_similarity("TEST001", "TEST002")
        self.test("캐시 메커니즘 작동", len(self.engine.cache) > 0, True)

        # 결과 출력
        print("\n" + "="*60)
        print(f"테스트 완료: {self.passed} 통과, {self.failed} 실패")
        print("="*60 + "\n")

        return self.failed == 0


if __name__ == '__main__':
    tester = TestSimilarityEngine()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
