"""
섹터 공존 계산 엔진
- 두 항공편이 동일 섹터에서 겹치는 시간 계산
- 수평/수직 분리 거리 계산 (Haversine)
- 충돌 위험도 판정
"""
import math
from datetime import datetime, timedelta
from utils.logger import setup_logger
from utils.constants import SEPARATION_STANDARDS

logger = setup_logger(__name__)


class SectorCalculator:
    """섹터 공존 계산 엔진"""

    def __init__(self):
        """초기화"""
        self.coexistence_data = []
        self.earth_radius_km = 6371

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        """
        Haversine 공식으로 두 지점 간 거리 계산

        Args:
            lat1: 첫 번째 위도
            lon1: 첫 번째 경도
            lat2: 두 번째 위도
            lon2: 두 번째 경도

        Returns:
            float: 거리 (km)
        """
        R = 6371  # 지구 반지름 (km)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon / 2) * math.sin(dlon / 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    @staticmethod
    def calculate_vertical_separation(alt1, alt2):
        """
        수직 분리 거리 계산 (feet 단위)

        Args:
            alt1: 첫 번째 항공편 고도 (Flight Level, e.g., 370)
            alt2: 두 번째 항공편 고도 (Flight Level)

        Returns:
            int: 수직 분리 거리 (feet)
        """
        try:
            # Flight Level을 feet로 변환 (FL370 = 37,000 feet)
            alt1_feet = int(alt1) * 100 if isinstance(alt1, (int, float)) else 0
            alt2_feet = int(alt2) * 100 if isinstance(alt2, (int, float)) else 0
            return abs(alt1_feet - alt2_feet)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def time_overlap(start1, end1, start2, end2):
        """
        두 시간 범위의 겹침 시간 계산

        Args:
            start1: 첫 번째 시작 시간 (datetime)
            end1: 첫 번째 종료 시간 (datetime)
            start2: 두 번째 시작 시간 (datetime)
            end2: 두 번째 종료 시간 (datetime)

        Returns:
            timedelta: 겹침 시간, 없으면 timedelta(0)
        """
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start < overlap_end:
            return overlap_end - overlap_start
        return timedelta(0)

    def calculate_coexistence(self, flight1, flight2):
        """
        두 항공편의 공존 정보 계산

        Args:
            flight1: 첫 번째 항공편 정보 (dict)
                - callsign: 콜사인
                - sector: 섹터 코드
                - entry_time: 섹터 진입 시간 (datetime)
                - exit_time: 섹터 진출 시간 (datetime)
                - lat: 섹터 중심 위도
                - lon: 섹터 중심 경도
                - altitude: 고도 (Flight Level)
                - speed: 속도 (km/h)

            flight2: 두 번째 항공편 정보 (dict)

        Returns:
            dict: 공존 정보
                {
                    'callsign1': str,
                    'callsign2': str,
                    'sector': str,
                    'coexist_minutes': float,
                    'horizontal_separation_km': float,
                    'vertical_separation_feet': int,
                    'risk_level': str,
                    'entry_time': datetime,
                    'exit_time': datetime
                }
        """
        # 동일 섹터 확인
        if flight1.get('sector') != flight2.get('sector'):
            return None

        sector = flight1.get('sector')

        # 시간 겹침 계산
        try:
            overlap = self.time_overlap(
                flight1.get('entry_time'),
                flight1.get('exit_time'),
                flight2.get('entry_time'),
                flight2.get('exit_time')
            )
            coexist_minutes = overlap.total_seconds() / 60
        except (TypeError, AttributeError):
            coexist_minutes = 0

        if coexist_minutes <= 0:
            return None

        # 수평 분리 거리 계산
        try:
            horizontal_sep = self.haversine(
                flight1.get('lat', 0),
                flight1.get('lon', 0),
                flight2.get('lat', 0),
                flight2.get('lon', 0)
            )
        except (TypeError, ValueError):
            horizontal_sep = 0

        # 수직 분리 거리 계산
        try:
            vertical_sep = self.calculate_vertical_separation(
                flight1.get('altitude', 0),
                flight2.get('altitude', 0)
            )
        except (TypeError, ValueError):
            vertical_sep = 0

        # 위험도 판정
        risk_level = self._assess_risk(coexist_minutes, horizontal_sep, vertical_sep)

        # 겹침 시간 범위 계산
        entry_time = max(flight1.get('entry_time'), flight2.get('entry_time'))
        exit_time = min(flight1.get('exit_time'), flight2.get('exit_time'))

        result = {
            'callsign1': flight1.get('callsign'),
            'callsign2': flight2.get('callsign'),
            'sector': sector,
            'coexist_minutes': round(coexist_minutes, 1),
            'horizontal_separation_km': round(horizontal_sep, 2),
            'vertical_separation_feet': int(vertical_sep),
            'risk_level': risk_level,
            'entry_time': entry_time,
            'exit_time': exit_time,
        }

        return result

    def _assess_risk(self, coexist_minutes, horizontal_sep_km, vertical_sep_feet):
        """
        공존 정보로부터 충돌 위험도 판정

        Args:
            coexist_minutes: 공존 시간 (분)
            horizontal_sep_km: 수평 분리 (km)
            vertical_sep_feet: 수직 분리 (feet)

        Returns:
            str: 위험도 ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
        """
        min_horizontal = SEPARATION_STANDARDS.get('min_horizontal_separation_km', 3)
        min_vertical = SEPARATION_STANDARDS.get('min_vertical_separation_feet', 1000)

        # 수평 분리 기준 미충족
        if horizontal_sep_km < min_horizontal:
            if vertical_sep_feet < min_vertical:
                # 둘 다 미충족 -> CRITICAL
                if coexist_minutes > 10:
                    return 'CRITICAL'
                return 'HIGH'
            else:
                # 수평만 미충족 -> HIGH
                if coexist_minutes > 15:
                    return 'HIGH'
                return 'MEDIUM'
        elif vertical_sep_feet < min_vertical:
            # 수직만 미충족 -> MEDIUM (공존 시간과 무관하게)
            return 'MEDIUM'
        else:
            # 모두 충족 -> LOW
            return 'LOW'

    def calculate_all_coexistences(self, flights):
        """
        모든 항공편 쌍의 공존 정보 계산

        Args:
            flights: 항공편 정보 리스트 (list of dict)

        Returns:
            list: 공존 정보 리스트
        """
        coexistences = []

        for i in range(len(flights)):
            for j in range(i + 1, len(flights)):
                coexist_info = self.calculate_coexistence(flights[i], flights[j])
                if coexist_info:
                    coexistences.append(coexist_info)

        self.coexistence_data = coexistences
        logger.info(f"공존 정보 계산 완료: {len(coexistences)}개 쌍")

        return coexistences

    def filter_coexistences(self, coexistences, min_coexist_minutes=0,
                           max_coexist_minutes=None, min_horizontal_sep=0,
                           min_vertical_sep=0, risk_levels=None):
        """
        공존 정보 필터링

        Args:
            coexistences: 공존 정보 리스트
            min_coexist_minutes: 최소 공존 시간 (분)
            max_coexist_minutes: 최대 공존 시간 (분)
            min_horizontal_sep: 최소 수평 분리 (km)
            min_vertical_sep: 최소 수직 분리 (feet)
            risk_levels: 위험도 필터 (list)

        Returns:
            list: 필터링된 공존 정보 리스트
        """
        filtered = coexistences

        # 공존 시간 필터
        if min_coexist_minutes > 0:
            filtered = [c for c in filtered if c['coexist_minutes'] >= min_coexist_minutes]

        if max_coexist_minutes is not None:
            filtered = [c for c in filtered if c['coexist_minutes'] <= max_coexist_minutes]

        # 분리 거리 필터
        if min_horizontal_sep > 0:
            filtered = [c for c in filtered if c['horizontal_separation_km'] >= min_horizontal_sep]

        if min_vertical_sep > 0:
            filtered = [c for c in filtered if c['vertical_separation_feet'] >= min_vertical_sep]

        # 위험도 필터
        if risk_levels:
            filtered = [c for c in filtered if c['risk_level'] in risk_levels]

        logger.info(f"필터링 결과: {len(coexistences)} -> {len(filtered)}")

        return filtered

    def get_sector_statistics(self, coexistences):
        """
        섹터별 공존 통계 생성

        Args:
            coexistences: 공존 정보 리스트

        Returns:
            dict: 섹터별 통계
                {
                    'sector_code': {
                        'event_count': int,
                        'avg_coexist_minutes': float,
                        'risk_distribution': {'CRITICAL': int, 'HIGH': int, ...},
                        'high_risk_ratio': float
                    }
                }
        """
        stats = {}

        for coexist in coexistences:
            sector = coexist['sector']

            if sector not in stats:
                stats[sector] = {
                    'event_count': 0,
                    'total_coexist_minutes': 0,
                    'risk_counts': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
                }

            stats[sector]['event_count'] += 1
            stats[sector]['total_coexist_minutes'] += coexist['coexist_minutes']
            stats[sector]['risk_counts'][coexist['risk_level']] += 1

        # 평균 및 비율 계산
        for sector in stats:
            data = stats[sector]
            count = data['event_count']

            stats[sector]['avg_coexist_minutes'] = round(
                data['total_coexist_minutes'] / count, 1) if count > 0 else 0

            total_risk = count
            stats[sector]['high_risk_ratio'] = round(
                (data['risk_counts']['CRITICAL'] + data['risk_counts']['HIGH']) / total_risk, 2
            ) if total_risk > 0 else 0

        return stats

    def export_to_csv(self, coexistences, filename='coexistence.csv'):
        """
        공존 정보를 CSV로 내보내기

        Args:
            coexistences: 공존 정보 리스트
            filename: 저장할 파일명
        """
        try:
            import pandas as pd

            df = pd.DataFrame(coexistences)
            df.to_csv(filename, index=False, encoding='utf-8')
            logger.info(f"공존 정보 CSV 저장: {filename}")
        except ImportError:
            logger.error("pandas 라이브러리 필요")

    def export_to_json(self, coexistences, filename='coexistence.json'):
        """
        공존 정보를 JSON으로 내보내기

        Args:
            coexistences: 공존 정보 리스트
            filename: 저장할 파일명
        """
        import json

        # datetime 객체를 문자열로 변환
        json_data = []
        for coexist in coexistences:
            data = coexist.copy()
            data['entry_time'] = data['entry_time'].isoformat() if data['entry_time'] else None
            data['exit_time'] = data['exit_time'].isoformat() if data['exit_time'] else None
            json_data.append(data)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        logger.info(f"공존 정보 JSON 저장: {filename}")


# 테스트용 함수
def create_sample_coexistences():
    """샘플 공존 정보 생성"""
    calculator = SectorCalculator()

    # 샘플 항공편 데이터
    flights = [
        {
            'callsign': 'GIA878',
            'sector': 'JH',
            'entry_time': datetime(2025, 12, 14, 14, 30),
            'exit_time': datetime(2025, 12, 14, 14, 45),
            'lat': 37.2,
            'lon': 127.1,
            'altitude': 370,
            'speed': 473
        },
        {
            'callsign': 'AIA878',
            'sector': 'JH',
            'entry_time': datetime(2025, 12, 14, 14, 35),
            'exit_time': datetime(2025, 12, 14, 14, 50),
            'lat': 37.25,
            'lon': 127.05,
            'altitude': 350,
            'speed': 470
        },
        {
            'callsign': 'KAL456',
            'sector': 'JN',
            'entry_time': datetime(2025, 12, 14, 15, 0),
            'exit_time': datetime(2025, 12, 14, 15, 20),
            'lat': 37.5,
            'lon': 127.5,
            'altitude': 280,
            'speed': 450
        }
    ]

    # 공존 계산
    coexistences = calculator.calculate_all_coexistences(flights)

    # 통계 생성
    stats = calculator.get_sector_statistics(coexistences)

    # 내보내기
    calculator.export_to_csv(coexistences)
    calculator.export_to_json(coexistences)

    return calculator, coexistences, stats


if __name__ == '__main__':
    calc, coexist, stats = create_sample_coexistences()
    print("✓ 섹터 공존 계산 완료")
    print(f"  - 공존 쌍: {len(coexist)}")
    print(f"  - 섹터: {list(stats.keys())}")
    for sector, data in stats.items():
        print(f"    {sector}: {data['event_count']}건, 고위험: {data['high_risk_ratio']*100:.1f}%")
