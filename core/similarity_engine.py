"""
유사호출 판정 엔진 v2.1
- level.txt 표준 기반 강화된 유사도 탐지 로직
- 시각적/청각적 혼동 패턴(Visual/Auditory Confusion) 반영
- 항공사 코드 유사성(전치/샌드위치) 반영
- 동일 일자/동일 섹터 내 유사호출 감지 최적화
"""
import re
from collections import OrderedDict
from utils.logger import setup_logger
from utils.constants import SIMILARITY_LEVELS, CONFUSION_PAIRS

logger = setup_logger(__name__)


class SimilarityEngine:
    """유사호출 판정 엔진"""

    def __init__(self, max_cache_size=10000):
        self.cache = OrderedDict()
        self.max_cache_size = max_cache_size

    def _is_char_similar(self, c1, c2, pattern_type='visual'):
        """두 문자가 시각적 또는 청각적으로 유사한지 확인 (v2.1 그룹화 대응)"""
        if c1 == c2: return True
        
        # 'both'인 경우 시각/청각 모두 확인
        if pattern_type == 'both':
            return self._is_char_similar(c1, c2, 'visual') or self._is_char_similar(c1, c2, 'auditory')
            
        groups = CONFUSION_PAIRS.get(pattern_type, [])
        for group in groups:
            if c1 in group and c2 in group:
                return True
        return False

    def _is_string_similar(self, s1, s2, pattern_type='visual'):
        """문자열 전체가 특정 패턴에 따라 유사한지 확인"""
        if len(s1) != len(s2) or not s1: return False
        for c1, c2 in zip(s1, s2):
            if not self._is_char_similar(c1, c2, pattern_type):
                return False
        return True

    def _is_airline_similar(self, air1, air2):
        """항공사 코드의 유사성 확인 (v2.1)"""
        if not air1 or not air2: return False
        if air1 == air2: return True
        
        # 전치 (Transposition) 및 샌드위치 (Sandwich) 로직
        if len(air1) == 3 and len(air2) == 3:
            # Transposition (KAL vs KLA)
            if air1[0] == air2[0] and air1[1] == air2[2] and air1[2] == air2[1]:
                return True
            # Sandwich (KAL vs KBL)
            if air1[0] == air2[0] and air1[2] == air2[2]:
                return True
        return False

    @staticmethod
    def _extract_prefix(callsign):
        match = re.search(r'^[A-Z]+', str(callsign).upper())
        return match.group(0) if match else ""

    @staticmethod
    def _extract_digits(callsign):
        return re.sub(r'[^0-9]', '', str(callsign))

    @staticmethod
    def _edit_distance(s1, s2):
        s1, s2 = s1.upper(), s2.upper()
        if len(s1) < len(s2): s1, s2 = s2, s1
        if not s2: return len(s1)
        prev = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
            prev = curr
        return prev[-1]

    @staticmethod
    def _count_consecutive_matches(s1, s2):
        if not s1 or not s2: return 0
        max_c, curr_c = 0, 0
        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                curr_c += 1
                max_c = max(max_c, curr_c)
            else:
                curr_c = 0
        return max_c

    def check_similarity(self, callsign1, callsign2):
        """두 콜사인의 유사도 판정 (v2.1)"""
        c1, c2 = str(callsign1).upper().strip(), str(callsign2).upper().strip()
        if not c1 or not c2:
            return '', 0

        # 캐시 확인
        cache_key = "|".join(sorted([c1, c2]))
        if cache_key in self.cache: return self.cache[cache_key]

        air1, air2 = self._extract_prefix(c1), self._extract_prefix(c2)
        num1, num2 = self._extract_digits(c1), self._extract_digits(c2)
        ed = self._edit_distance(c1, c2)

        # Exact callsign match
        if c1 == c2:
            return self._store_and_return(cache_key, ('LEVEL_5-1', 0))

        # ========== LEVEL 3 (Notice) - 먼저 확인하는 기본 규칙 ==========

        # 3-1: Leading Zero Difference (최우선: 숫자값이 같으면 먼저 처리)
        if num1 != num2 and num1.isdigit() and num2.isdigit():
            try:
                if int(num1) == int(num2):
                    return self._store_and_return(cache_key, ('LEVEL_3-1', ed))
            except:
                pass

        # ========== LEVEL 4 (Caution) - 더 구체적인 규칙 ==========

        # 4-1: Number Transposition (숫자 위치 바뀜)
        if air1 == air2 and air1 != "" and len(num1) == len(num2) and sorted(num1) == sorted(num2) and num1 != num2:
            return self._store_and_return(cache_key, ('LEVEL_4-1', ed))

        # 4-2: First/Last Match + Middle Similar (양끝 일치 + 가운데 시각유사)
        if air1 == air2 and air1 != "" and len(num1) == len(num2) and len(num1) >= 3:
            if num1[0] == num2[0] and num1[-1] == num2[-1]:
                mid1 = num1[1:-1]
                mid2 = num2[1:-1]
                if self._is_string_similar(mid1, mid2, 'visual'):
                     return self._store_and_return(cache_key, ('LEVEL_4-2', ed))

        # 4-3: Single Digit Confusion (한 자리 혼동)
        if air1 == air2 and air1 != "" and len(num1) == len(num2):
            if self._edit_distance(num1, num2) == 1:
                for c1_digit, c2_digit in zip(num1, num2):
                    if c1_digit != c2_digit:
                        if self._is_char_similar(c1_digit, c2_digit, 'auditory') or self._is_char_similar(c1_digit, c2_digit, 'visual'):
                            return self._store_and_return(cache_key, ('LEVEL_4-3', ed))
                        break

        # ========== LEVEL 5 (Critical) - 숫자 동일 우선 (숫자 일치는 높은 우선순위) ==========

        # 5-1: Airline Similar (Trans/Sandwich) + Numbers Identical
        if self._is_airline_similar(air1, air2) and num1 == num2 and num1 != "":
            return self._store_and_return(cache_key, ('LEVEL_5-1', ed))

        # 4-5: Different Airline + Identical Numbers (LEVEL_5-1 후에)
        if air1 != air2 and num1 == num2 and num1 != "":
            return self._store_and_return(cache_key, ('LEVEL_4-5', ed))

        # 4-4: Airline Similar + Number Similar (마지막 LEVEL 4)
        if self._is_airline_similar(air1, air2) and (self._is_string_similar(num1, num2, 'visual') or self._is_string_similar(num1, num2, 'auditory')):
            return self._store_and_return(cache_key, ('LEVEL_4-4', ed))

        # ========== LEVEL 5 나머지 ==========

        # 5-2: Same Airline + Suffix 3 Match
        if air1 == air2 and air1 != "" and len(num1) >= 3 and len(num2) >= 3:
            if num1[-3:] == num2[-3:]:
                return self._store_and_return(cache_key, ('LEVEL_5-2', ed))

        # 5-3: Same Airline + Visual/Auditory Confusion (Entire Number)
        if air1 == air2 and air1 != "" and self._is_string_similar(num1, num2, 'both'):
             return self._store_and_return(cache_key, ('LEVEL_5-3', ed))

        return self._store_and_return(cache_key, ('', 0))

    def _store_and_return(self, key, result):
        if len(self.cache) >= self.max_cache_size:
            self.cache.popitem(last=False)
        self.cache[key] = result
        return result

    def get_risk_level(self, level):
        return SIMILARITY_LEVELS.get(level, {}).get('risk', 'LOW')

    def get_similarity_score(self, level):
        """유사도 점수 조회 (평균값 반환)"""
        level_info = SIMILARITY_LEVELS.get(level, {})
        return level_info.get('score_avg', level_info.get('score', 0))


_engine = SimilarityEngine()
def check_similarity(c1, c2): return _engine.check_similarity(c1, c2)
def get_risk_level(lvl): return _engine.get_risk_level(lvl)
def get_similarity_score(lvl): return _engine.get_similarity_score(lvl)
