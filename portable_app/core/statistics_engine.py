"""
통계 분석 엔진
- 시간대별 통계 (hourly/6-hourly/daily)
- 섹터별 통계 및 분석
- 콜사인 패턴 분석
- 위험도별 통계
"""
from datetime import datetime, timedelta
from collections import defaultdict
import json
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StatisticsEngine:
    """통계 분석 엔진"""

    def __init__(self):
        """초기화"""
        self.coexistences = []
        self.similarity_events = []

    def add_coexistence_data(self, coexistences):
        """
        공존 데이터 추가

        Args:
            coexistences: 공존 정보 리스트
        """
        self.coexistences = coexistences
        logger.info(f"공존 데이터 추가: {len(coexistences)}개")

    def add_similarity_events(self, events):
        """
        유사호출 이벤트 데이터 추가

        Args:
            events: 유사호출 이벤트 리스트
                {
                    'callsign1': str,
                    'callsign2': str,
                    'similarity_level': str,
                    'risk_level': str,
                    'sector': str,
                    'time': datetime
                }
        """
        self.similarity_events = events
        logger.info(f"유사호출 이벤트 추가: {len(events)}개")

    def hourly_statistics(self):
        """
        시간대별 통계 생성 (시간 단위)

        Returns:
            dict: 시간대별 통계
                {
                    'HH': {
                        'event_count': int,
                        'high_risk': int,
                        'medium_risk': int,
                        'low_risk': int,
                        'critical_risk': int,
                        'avg_coexist_minutes': float
                    }
                }
        """
        stats = {}

        for coexist in self.coexistences:
            try:
                hour = coexist['entry_time'].strftime('%H')
            except (TypeError, AttributeError):
                continue

            if hour not in stats:
                stats[hour] = {
                    'event_count': 0,
                    'critical_risk': 0,
                    'high_risk': 0,
                    'medium_risk': 0,
                    'low_risk': 0,
                    'total_coexist_minutes': 0
                }

            stats[hour]['event_count'] += 1
            stats[hour][f"{coexist['risk_level'].lower()}_risk"] += 1
            stats[hour]['total_coexist_minutes'] += coexist['coexist_minutes']

        # 평균 계산
        for hour in stats:
            count = stats[hour]['event_count']
            if count > 0:
                stats[hour]['avg_coexist_minutes'] = round(
                    stats[hour]['total_coexist_minutes'] / count, 1
                )
            else:
                stats[hour]['avg_coexist_minutes'] = 0

        # 정렬
        sorted_stats = {k: stats[k] for k in sorted(stats.keys())}
        logger.info(f"시간대별 통계 생성: {len(sorted_stats)}개 시간대")

        return sorted_stats

    def sector_statistics(self):
        """
        섹터별 통계 생성

        Returns:
            dict: 섹터별 통계
                {
                    'sector_code': {
                        'event_count': int,
                        'high_risk_ratio': float,
                        'avg_coexist_minutes': float,
                        'top_callsign_pairs': list,
                        'risk_distribution': dict
                    }
                }
        """
        stats = {}

        for coexist in self.coexistences:
            sector = coexist['sector']

            if sector not in stats:
                stats[sector] = {
                    'event_count': 0,
                    'critical_risk': 0,
                    'high_risk': 0,
                    'medium_risk': 0,
                    'low_risk': 0,
                    'total_coexist_minutes': 0,
                    'callsign_pairs': defaultdict(int)
                }

            stats[sector]['event_count'] += 1
            stats[sector][f"{coexist['risk_level'].lower()}_risk"] += 1
            stats[sector]['total_coexist_minutes'] += coexist['coexist_minutes']

            # 콜사인 쌍 추적
            pair = tuple(sorted([coexist['callsign1'], coexist['callsign2']]))
            stats[sector]['callsign_pairs'][pair] += 1

        # 최종 처리
        for sector in stats:
            data = stats[sector]
            count = data['event_count']

            # 위험도 비율 계산
            stats[sector]['high_risk_ratio'] = round(
                (data['critical_risk'] + data['high_risk']) / count, 2
            ) if count > 0 else 0

            # 평균 공존시간
            stats[sector]['avg_coexist_minutes'] = round(
                data['total_coexist_minutes'] / count, 1
            ) if count > 0 else 0

            # 상위 콜사인 쌍 (빈도순)
            top_pairs = sorted(
                data['callsign_pairs'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            stats[sector]['top_callsign_pairs'] = [
                {'pair': f"{p[0][0]}-{p[0][1]}", 'count': p[1]}
                for p in top_pairs
            ]

            # 위험도 분포 저장
            stats[sector]['risk_distribution'] = {
                'CRITICAL': data['critical_risk'],
                'HIGH': data['high_risk'],
                'MEDIUM': data['medium_risk'],
                'LOW': data['low_risk']
            }

            # 불필요한 필드 제거
            del stats[sector]['callsign_pairs']
            del stats[sector]['total_coexist_minutes']

        logger.info(f"섹터별 통계 생성: {len(stats)}개 섹터")

        return stats

    def callsign_statistics(self):
        """
        콜사인별 통계 생성

        Returns:
            dict: 콜사인별 통계
                {
                    'callsign': {
                        'coexistence_count': int,
                        'avg_risk_level': str,
                        'most_common_partner': str,
                        'sectors': list,
                        'high_risk_percentage': float
                    }
                }
        """
        stats = {}

        for coexist in self.coexistences:
            for callsign in [coexist['callsign1'], coexist['callsign2']]:
                if callsign not in stats:
                    stats[callsign] = {
                        'coexistence_count': 0,
                        'critical_risk': 0,
                        'high_risk': 0,
                        'medium_risk': 0,
                        'low_risk': 0,
                        'partners': defaultdict(int),
                        'sectors': set()
                    }

                stats[callsign]['coexistence_count'] += 1
                stats[callsign][f"{coexist['risk_level'].lower()}_risk"] += 1
                stats[callsign]['sectors'].add(coexist['sector'])

                # 파트너 추적
                partner = coexist['callsign2'] if callsign == coexist['callsign1'] else coexist['callsign1']
                stats[callsign]['partners'][partner] += 1

        # 최종 처리
        for callsign in stats:
            data = stats[callsign]
            count = data['coexistence_count']

            # 고위험 비율
            stats[callsign]['high_risk_percentage'] = round(
                (data['critical_risk'] + data['high_risk']) / count * 100, 1
            ) if count > 0 else 0

            # 가장 흔한 파트너
            if data['partners']:
                most_common_partner = max(
                    data['partners'].items(),
                    key=lambda x: x[1]
                )
                stats[callsign]['most_common_partner'] = most_common_partner[0]
            else:
                stats[callsign]['most_common_partner'] = None

            # 섹터 리스트로 변환
            stats[callsign]['sectors'] = sorted(list(data['sectors']))

            # 위험도 분포
            stats[callsign]['risk_distribution'] = {
                'CRITICAL': data['critical_risk'],
                'HIGH': data['high_risk'],
                'MEDIUM': data['medium_risk'],
                'LOW': data['low_risk']
            }

            # 평균 위험도
            if count > 0:
                if data['critical_risk'] > 0:
                    stats[callsign]['avg_risk_level'] = 'CRITICAL'
                elif data['high_risk'] > 0:
                    stats[callsign]['avg_risk_level'] = 'HIGH'
                elif data['medium_risk'] > 0:
                    stats[callsign]['avg_risk_level'] = 'MEDIUM'
                else:
                    stats[callsign]['avg_risk_level'] = 'LOW'
            else:
                stats[callsign]['avg_risk_level'] = 'UNKNOWN'

            # 불필요한 필드 제거
            del stats[callsign]['partners']
            del stats[callsign]['critical_risk']
            del stats[callsign]['high_risk']
            del stats[callsign]['medium_risk']
            del stats[callsign]['low_risk']

        logger.info(f"콜사인별 통계 생성: {len(stats)}개 콜사인")

        return stats

    def risk_level_statistics(self):
        """
        위험도별 통계 생성

        Returns:
            dict: 위험도별 통계
                {
                    'risk_level': {
                        'count': int,
                        'percentage': float,
                        'avg_coexist_minutes': float,
                        'sectors': list
                    }
                }
        """
        stats = {
            'CRITICAL': {'count': 0, 'total_coexist': 0, 'sectors': set()},
            'HIGH': {'count': 0, 'total_coexist': 0, 'sectors': set()},
            'MEDIUM': {'count': 0, 'total_coexist': 0, 'sectors': set()},
            'LOW': {'count': 0, 'total_coexist': 0, 'sectors': set()}
        }

        total_count = len(self.coexistences)

        for coexist in self.coexistences:
            risk = coexist['risk_level']
            stats[risk]['count'] += 1
            stats[risk]['total_coexist'] += coexist['coexist_minutes']
            stats[risk]['sectors'].add(coexist['sector'])

        # 최종 처리
        for risk in stats:
            count = stats[risk]['count']
            stats[risk]['percentage'] = round(
                (count / total_count * 100), 1
            ) if total_count > 0 else 0

            stats[risk]['avg_coexist_minutes'] = round(
                stats[risk]['total_coexist'] / count, 1
            ) if count > 0 else 0

            stats[risk]['sectors'] = sorted(list(stats[risk]['sectors']))

            # 불필요한 필드 제거
            del stats[risk]['total_coexist']

        logger.info("위험도별 통계 생성 완료")

        return stats

    def generate_summary(self):
        """
        전체 요약 통계 생성

        Returns:
            dict: 요약 통계
        """
        total_coexistences = len(self.coexistences)
        total_events = len(self.similarity_events)

        if total_coexistences > 0:
            critical_count = sum(1 for c in self.coexistences if c['risk_level'] == 'CRITICAL')
            high_count = sum(1 for c in self.coexistences if c['risk_level'] == 'HIGH')
            medium_count = sum(1 for c in self.coexistences if c['risk_level'] == 'MEDIUM')
            low_count = sum(1 for c in self.coexistences if c['risk_level'] == 'LOW')

            # coexist_minutes 필드가 있으면 사용, 없으면 0으로 기본값
            avg_coexist = sum(c.get('coexist_minutes', 0) for c in self.coexistences) / total_coexistences
        else:
            critical_count = high_count = medium_count = low_count = 0
            avg_coexist = 0

        summary = {
            'total_coexistences': total_coexistences,
            'total_similarity_events': total_events,
            'total_sectors': len(set(c.get('sector', 'UNKNOWN') for c in self.coexistences if c.get('sector'))),
            'total_callsigns': len(set(
                c['callsign1'] for c in self.coexistences
            ) | set(
                c['callsign2'] for c in self.coexistences
            )),
            'risk_distribution': {
                'CRITICAL': critical_count,
                'HIGH': high_count,
                'MEDIUM': medium_count,
                'LOW': low_count
            },
            'avg_coexist_minutes': round(avg_coexist, 1),
            'critical_percentage': round(critical_count / total_coexistences * 100, 1) if total_coexistences > 0 else 0,
            'high_risk_percentage': round((critical_count + high_count) / total_coexistences * 100, 1) if total_coexistences > 0 else 0,
            'hourly_distribution': {}
        }

        logger.info("요약 통계 생성 완료")

        return summary

    def export_to_json(self, data, filename='statistics.json'):
        """
        통계를 JSON으로 내보내기

        Args:
            data: 통계 데이터 (dict)
            filename: 저장할 파일명
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"통계 JSON 저장: {filename}")

    def export_all_statistics(self, output_dir='.'):
        """
        모든 통계를 파일로 내보내기

        Args:
            output_dir: 출력 디렉토리
        """
        import os

        os.makedirs(output_dir, exist_ok=True)

        # 시간대별 통계
        hourly = self.hourly_statistics()
        self.export_to_json(hourly, os.path.join(output_dir, 'statistics_hourly.json'))

        # 섹터별 통계
        sector = self.sector_statistics()
        self.export_to_json(sector, os.path.join(output_dir, 'statistics_sector.json'))

        # 콜사인별 통계
        callsign = self.callsign_statistics()
        self.export_to_json(callsign, os.path.join(output_dir, 'statistics_callsign.json'))

        # 위험도별 통계
        risk = self.risk_level_statistics()
        self.export_to_json(risk, os.path.join(output_dir, 'statistics_risk.json'))

        # 요약 통계
        summary = self.generate_summary()
        self.export_to_json(summary, os.path.join(output_dir, 'statistics_summary.json'))

        logger.info(f"모든 통계 저장 완료: {output_dir}")


# 테스트용 함수
def create_sample_statistics():
    """샘플 통계 생성"""
    from datetime import datetime

    engine = StatisticsEngine()

    # 샘플 공존 데이터
    coexistences = [
        {
            'callsign1': 'GIA878',
            'callsign2': 'AIA878',
            'sector': 'JH',
            'coexist_minutes': 10.0,
            'risk_level': 'LOW',
            'entry_time': datetime(2025, 12, 14, 14, 30),
            'exit_time': datetime(2025, 12, 14, 14, 40)
        },
        {
            'callsign1': 'KAL123',
            'callsign2': 'AAL123',
            'sector': 'JN',
            'coexist_minutes': 15.0,
            'risk_level': 'HIGH',
            'entry_time': datetime(2025, 12, 14, 15, 0),
            'exit_time': datetime(2025, 12, 14, 15, 15)
        },
        {
            'callsign1': 'GIA878',
            'callsign2': 'BIA870',
            'sector': 'JH',
            'coexist_minutes': 8.0,
            'risk_level': 'MEDIUM',
            'entry_time': datetime(2025, 12, 14, 16, 0),
            'exit_time': datetime(2025, 12, 14, 16, 8)
        }
    ]

    engine.add_coexistence_data(coexistences)
    engine.export_all_statistics()

    return engine


if __name__ == '__main__':
    engine = create_sample_statistics()
    print("✓ 통계 분석 엔진 완료")
    print("  - statistics_hourly.json")
    print("  - statistics_sector.json")
    print("  - statistics_callsign.json")
    print("  - statistics_risk.json")
    print("  - statistics_summary.json")
