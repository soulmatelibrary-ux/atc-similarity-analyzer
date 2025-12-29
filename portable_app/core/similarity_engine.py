"""
유사호출 판정 엔진
- Oracle 함수를 Python으로 완전히 재구현
- 13가지 유사도 판정 규칙 + LEVEL_3-8 (3자리 연속 같음)
- LRU(Least Recently Used) 캐싱 메커니즘 포함
"""
import re
from collections import OrderedDict
from utils.logger import setup_logger
from utils.constants import SIMILARITY_LEVELS

logger = setup_logger(__name__)


class SimilarityEngine:
    """유사호출 판정 엔진"""

    def __init__(self, max_cache_size=10000):
        """
        초기화

        Args:
            max_cache_size: 최대 캐시 크기 (LRU 정책 적용)
        """
        # OrderedDict를 사용한 LRU 캐시 구현
        self.cache = OrderedDict()
        self.max_cache_size = max_cache_size

    @staticmethod
    def _normalize_visual(callsign):
        """
        시각적 정규화 (I,L→1, O→0, S→5)

        Args:
            callsign: 콜사인 문자열

        Returns:
            str: 정규화된 콜사인
        """
        normalized = str(callsign).upper().strip()
        normalized = normalized.replace(' ', '')
        normalized = normalized.replace('L', '1')
        normalized = normalized.replace('I', '1')
        normalized = normalized.replace('O', '0')
        normalized = normalized.replace('S', '5')
        return normalized

    @staticmethod
    def _extract_prefix(callsign):
        """
        콜사인에서 prefix(문자 부분) 추출

        Args:
            callsign: 콜사인 문자열

        Returns:
            str: prefix 또는 None
        """
        match = re.search(r'^[A-Z]+', str(callsign).upper())
        return match.group(0) if match else None

    @staticmethod
    def _extract_digits(callsign):
        """
        콜사인에서 숫자 부분만 추출

        Args:
            callsign: 콜사인 문자열

        Returns:
            str: 숫자 문자열 또는 빈 문자열
        """
        digits = re.sub(r'[^0-9]', '', str(callsign))
        return digits

    @staticmethod
    def _extract_final_digits(callsign, count=2):
        """
        콜사인에서 마지막 N자리 숫자 추출

        Args:
            callsign: 콜사인 문자열
            count: 추출할 자리수

        Returns:
            str: 마지막 N자리 숫자 또는 None
        """
        digits = SimilarityEngine._extract_digits(callsign)
        if len(digits) >= count:
            return digits[-count:]
        return None

    @staticmethod
    def _edit_distance(str1, str2):
        """
        Edit Distance (Levenshtein distance) 계산
        두 문자열이 얼마나 다른지를 나타내는 거리

        Args:
            str1: 첫 번째 문자열
            str2: 두 번째 문자열

        Returns:
            int: 편집 거리
        """
        s1 = str(str1).upper()
        s2 = str(str2).upper()

        if len(s1) < len(s2):
            s1, s2 = s2, s1

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def _count_consecutive_matches(str1, str2):
        """
        두 문자열의 연속된 일치 개수 계산

        Args:
            str1: 첫 번째 문자열
            str2: 두 번째 문자열

        Returns:
            int: 최대 연속 일치 개수
        """
        s1 = str(str1)
        s2 = str(str2)

        if len(s1) != len(s2):
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def check_similarity(self, callsign1, callsign2):
        """
        두 콜사인의 유사도 판정 (메인 함수)

        Args:
            callsign1: 첫 번째 콜사인
            callsign2: 두 번째 콜사인

        Returns:
            tuple: (similarity_level, edit_distance) 또는 ('', 0)

        Raises:
            ValueError: 입력값이 유효하지 않은 경우
        """
        # 입력값 검증
        if callsign1 is None or callsign2 is None:
            raise ValueError(f"콜사인은 None이 될 수 없습니다: {callsign1}, {callsign2}")

        # 문자열로 변환 및 정제
        c1 = str(callsign1).upper().strip()
        c2 = str(callsign2).upper().strip()

        # 빈 문자열 또는 너무 짧은 콜사인 체크
        if not c1 or not c2:
            raise ValueError(f"콜사인은 빈 문자열이 될 수 없습니다: '{c1}', '{c2}'")

        if len(c1) < 2 or len(c2) < 2:
            raise ValueError(f"콜사인은 최소 2자 이상이어야 합니다: '{c1}' ({len(c1)}자), '{c2}' ({len(c2)}자)")

        # 동일한 경우 제외
        if c1 == c2:
            return '', 0

        # 캐시 확인 (정규화된 키: 순서 무관)
        # 두 콜사인을 정렬해서 캐시 키 생성 (AB와 BA를 같은 캐시로 인식)
        sorted_calls = sorted([c1, c2])
        cache_key = f"{sorted_calls[0]}|{sorted_calls[1]}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 추가 전처리
        vis1 = self._normalize_visual(c1)
        vis2 = self._normalize_visual(c2)

        p1 = self._extract_prefix(c1)
        p2 = self._extract_prefix(c2)

        n1 = self._extract_digits(c1)
        n2 = self._extract_digits(c2)

        f1 = self._extract_final_digits(c1, 2)
        f2 = self._extract_final_digits(c2, 2)

        last1 = c1[-1] if c1 else None
        last2 = c2[-1] if c2 else None

        ed = self._edit_distance(c1, c2)

        # 규칙 검사 (우선순위가 높은 것부터)

        # LEVEL_2-1: 같은 prefix + 시각적 유사 (시각적 정규화 적용)
        if p1 == p2 and p1 is not None and vis1 == vis2 and ed <= 2:
            result = ('LEVEL_2-1', ed)
            self._store_in_cache(cache_key, result)
            return result

        # LEVEL_2-2: 다른 prefix + 시각적 유사 (시각적 정규화 적용)
        if p1 and p2 and p1 != p2 and vis1 == vis2 and ed <= 3:
            result = ('LEVEL_2-2', ed)
            self._store_in_cache(cache_key, result)
            return result

        # LEVEL_4-1: 다른 prefix + 숫자 완전 동일 (가장 심각함)
        if p1 and p2 and p1 != p2 and n1 and n1 == n2 and ed <= 2:
            result = ('LEVEL_4-1', ed)
            self._store_in_cache(cache_key, result)
            return result

        # LEVEL_5-1: 같은 prefix + Leading Zero
        if p1 == p2 and p1 is not None and n1 and n2:
            try:
                if int(n1) == int(n2) and (n1.startswith('0') or n2.startswith('0')):
                    result = ('LEVEL_5-1', ed)
                    self._store_in_cache(cache_key, result)
                    return result
            except ValueError:
                pass

        # LEVEL_5-2: 다른 prefix + Leading Zero
        if p1 and p2 and p1 != p2 and n1 and n2:
            try:
                if int(n1) == int(n2) and (n1.startswith('0') or n2.startswith('0')):
                    result = ('LEVEL_5-2', ed)
                    self._store_in_cache(cache_key, result)
                    return result
            except ValueError:
                pass

        # LEVEL_3-8: Prefix 동일 + 숫자 3자리 연속 같음 (신규, 매우 위험)
        if p1 == p2 and p1 is not None and n1 and n2:
            if len(n1) == len(n2) and len(n1) >= 3:
                consecutive = self._count_consecutive_matches(n1, n2)
                if consecutive >= 3:
                    result = ('LEVEL_3-8', ed)
                    self._store_in_cache(cache_key, result)
                    return result

        # LEVEL_3-1: 마지막 2자리 숫자 동일
        if f1 and f1 == f2 and ed <= 2:
            result = ('LEVEL_3-1', ed)
            self._store_in_cache(cache_key, result)
            return result

        # LEVEL_4-2: Prefix 동일 + 4자리 이상 중 3자리 같음
        if p1 == p2 and p1 is not None and n1 and n2:
            if len(n1) >= 4 and len(n1) == len(n2):
                same_count = sum(1 for c1, c2 in zip(n1, n2) if c1 == c2)
                if same_count >= len(n1) - 1:  # 3자리 이상 같음
                    result = ('LEVEL_4-2', ed)
                    self._store_in_cache(cache_key, result)
                    return result

        # LEVEL_3-4: Prefix 동일 + 숫자 2자리 이상 같음
        if p1 == p2 and p1 is not None and n1 and n2:
            if len(n1) == len(n2):
                same_count = sum(1 for c1, c2 in zip(n1, n2) if c1 == c2)
                if same_count >= 2:
                    result = ('LEVEL_3-4', ed)
                    self._store_in_cache(cache_key, result)
                    return result

        # LEVEL_3-3: 연속된 숫자 블록 동일 (접두사/접미사 포함)
        if p1 == p2 and p1 is not None and n1 and n2:
            # n1이 n2의 접두사이거나 그 반대
            if n1.startswith(n2) or n2.startswith(n1):
                if len(min(n1, n2, key=len)) >= 2:
                    result = ('LEVEL_3-3', ed)
                    self._store_in_cache(cache_key, result)
                    return result

        # LEVEL_3-5: Prefix 동일 + 숫자 부분 일치
        if p1 == p2 and p1 is not None and n1 and n2:
            # 한쪽이 다른 쪽의 일부인 경우
            if n1 in n2 or n2 in n1:
                result = ('LEVEL_3-5', ed)
                self._store_in_cache(cache_key, result)
                return result

        # LEVEL_3-6: 마지막 2자리 같음 (prefix가 다른 경우)
        if len(c1) >= 2 and len(c2) >= 2:
            if c1[-2:] == c2[-2:]:
                result = ('LEVEL_3-6', ed)
                self._store_in_cache(cache_key, result)
                return result

        # LEVEL_3-7: 마지막 글자 동일
        if last1 and last1 == last2 and last1.isalpha():
            result = ('LEVEL_3-7', ed)
            self._store_in_cache(cache_key, result)
            return result

        # 유사도 없음
        result = ('', 0)
        self._store_in_cache(cache_key, result)
        return result

    def get_risk_level(self, similarity_level):
        """
        유사도 레벨에 따른 위험도 반환

        Args:
            similarity_level: 유사도 레벨 (예: 'LEVEL_2-1')

        Returns:
            str: 위험도 ('HIGH', 'MEDIUM', 'LOW')
        """
        if similarity_level in SIMILARITY_LEVELS:
            return SIMILARITY_LEVELS[similarity_level]['risk']
        return 'LOW'

    def get_similarity_score(self, similarity_level):
        """
        유사도 점수 반환 (0-100)

        Args:
            similarity_level: 유사도 레벨

        Returns:
            int: 점수 (0-100)
        """
        if similarity_level in SIMILARITY_LEVELS:
            return SIMILARITY_LEVELS[similarity_level]['score']
        return 0

    def _store_in_cache(self, cache_key, result):
        """
        LRU 캐시에 저장 (가장 오래된 항목 제거)

        Args:
            cache_key: 캐시 키
            result: 저장할 결과
        """
        # 기존 키가 있으면 최근 사용으로 이동
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            self.cache[cache_key] = result
            return

        # 새 항목 추가
        if len(self.cache) >= self.max_cache_size:
            # 가장 오래된 항목 제거 (첫 번째 항목)
            removed_key, _ = self.cache.popitem(last=False)
            logger.debug(f"LRU 캐시: 가장 오래된 항목 제거 ({removed_key}), 현재 크기: {len(self.cache)}")

        self.cache[cache_key] = result

    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logger.info("유사호출 판정 엔진 캐시 초기화")


# 전역 인스턴스
_engine = SimilarityEngine()


def check_similarity(callsign1, callsign2):
    """
    유사호출 판정 함수 (편의 함수)

    Args:
        callsign1: 첫 번째 콜사인
        callsign2: 두 번째 콜사인

    Returns:
        tuple: (similarity_level, edit_distance)
    """
    return _engine.check_similarity(callsign1, callsign2)


def get_risk_level(similarity_level):
    """위험도 반환 (편의 함수)"""
    return _engine.get_risk_level(similarity_level)


def get_similarity_score(similarity_level):
    """유사도 점수 반환 (편의 함수)"""
    return _engine.get_similarity_score(similarity_level)
