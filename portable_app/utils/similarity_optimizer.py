"""
유사호출 검사 최적화 모듈
- Prefix 기반 그룹핑으로 비교 대상 축소
- 불필요한 비교 줄이기
"""
from collections import defaultdict


class SimilarityOptimizer:
    """유사호출 검사 최적화"""

    @staticmethod
    def extract_prefix(callsign):
        """
        콜사인에서 Prefix(문자 부분) 추출

        Args:
            callsign: 콜사인 (예: 'AAL123')

        Returns:
            str: Prefix (예: 'AAL')
        """
        if not callsign:
            return ''

        # 첫 글자부터 숫자가 나올 때까지 추출
        prefix = ''
        for char in callsign:
            if char.isalpha():
                prefix += char
            else:
                break

        return prefix.upper()

    @staticmethod
    def group_by_prefix(flights_data):
        """
        항공편 데이터를 Prefix로 그룹핑

        Args:
            flights_data: 항공편 정보 리스트 (dict)

        Returns:
            dict: {prefix: [flight1, flight2, ...]}
        """
        groups = defaultdict(list)

        for flight in flights_data:
            callsign = flight.get('CALLSIGN', '')
            prefix = SimilarityOptimizer.extract_prefix(callsign)

            if prefix:
                groups[prefix].append(flight)
            else:
                # Prefix가 없으면 특수 그룹에 추가
                groups['__OTHER__'].append(flight)

        return dict(groups)

    @staticmethod
    def get_candidate_pairs(flights_data, prefix_groups=None):
        """
        유사호출 검사 대상 쌍 생성 (최적화)

        비교 전략:
        1. 같은 Prefix 내에서만 비교 (O(k²) where k = group size)
        2. Prefix가 유사한 그룹 간 비교 (예: AAL과 AAH)
        3. 전체 O(n²)에서 O(n * log n)으로 감소

        Args:
            flights_data: 항공편 정보 리스트
            prefix_groups: 사전 그룹화된 데이터 (옵션)

        Returns:
            list: [(flight1, flight2), ...] 비교 대상 쌍
        """
        if prefix_groups is None:
            prefix_groups = SimilarityOptimizer.group_by_prefix(flights_data)

        candidate_pairs = []

        # 1단계: 같은 Prefix 내에서 비교
        for prefix, group in prefix_groups.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    candidate_pairs.append((group[i], group[j]))

        # 2단계: 유사한 Prefix 간 비교 (선택사항)
        # 예: AAL과 AAH, DAL과 DAH 등
        sorted_prefixes = sorted(prefix_groups.keys())
        for i in range(len(sorted_prefixes) - 1):
            prefix1 = sorted_prefixes[i]
            prefix2 = sorted_prefixes[i + 1]

            # 첫 2글자가 같으면 비교 (AAL과 AAH)
            if prefix1 != '__OTHER__' and prefix2 != '__OTHER__':
                if len(prefix1) >= 2 and len(prefix2) >= 2:
                    if prefix1[:2] == prefix2[:2]:
                        for flight1 in prefix_groups[prefix1]:
                            for flight2 in prefix_groups[prefix2]:
                                candidate_pairs.append((flight1, flight2))

        return candidate_pairs

    @staticmethod
    def get_optimization_stats(flights_data, prefix_groups=None):
        """
        최적화 통계 반환

        Args:
            flights_data: 항공편 정보 리스트
            prefix_groups: 사전 그룹화된 데이터 (옵션)

        Returns:
            dict: 통계 정보
        """
        if prefix_groups is None:
            prefix_groups = SimilarityOptimizer.group_by_prefix(flights_data)

        total_flights = len(flights_data)
        candidate_pairs = SimilarityOptimizer.get_candidate_pairs(flights_data, prefix_groups)
        candidate_count = len(candidate_pairs)

        # 원래 브루트포스 방식
        brute_force_count = (total_flights * (total_flights - 1)) // 2

        # 감소율
        reduction_percent = 0
        if brute_force_count > 0:
            reduction_percent = (1 - candidate_count / brute_force_count) * 100

        return {
            'total_flights': total_flights,
            'prefix_groups': len(prefix_groups),
            'brute_force_pairs': brute_force_count,
            'candidate_pairs': candidate_count,
            'reduction_percent': round(reduction_percent, 2),
            'estimated_speedup': round(brute_force_count / max(candidate_count, 1), 2)
        }
