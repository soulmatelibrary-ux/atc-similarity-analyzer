#!/usr/bin/env python3
"""
데이터 일관성 검증 도구
데이터베이스의 검출된 유사호출 건수와 대시보드 표시 건수를 비교
"""

import sys
from pathlib import Path
import json

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DataConsistencyChecker:
    """데이터 일관성 검증"""

    def __init__(self):
        self.db = DatabaseManager()

    def get_db_total_similarities(self, eobd=None):
        """DB의 전체 유사호출 건수 조회"""
        if eobd:
            query = """
                SELECT COUNT(DISTINCT s.id) as count
                FROM similarities s
                JOIN flights f1 ON s.flight_id_1 = f1.id
                WHERE f1.eobd = ?
            """
            result = self.db.execute_query(query, [eobd])
        else:
            query = "SELECT COUNT(*) as count FROM similarities"
            result = self.db.execute_query(query)

        return result[0][0] if result else 0

    def get_db_hourly_distribution(self, eobd=None):
        """DB의 시간대별 유사호출 분포 조회"""
        if eobd:
            query = """
                SELECT
                    strftime('%H', so.overlap_start) as hour,
                    COUNT(*) as count
                FROM sector_overlaps so
                JOIN similarities s ON so.similarity_id = s.id
                JOIN flights f1 ON s.flight_id_1 = f1.id
                WHERE f1.eobd = ?
                GROUP BY hour
                ORDER BY hour
            """
            results = self.db.execute_query(query, [eobd])
        else:
            query = """
                SELECT
                    strftime('%H', so.overlap_start) as hour,
                    COUNT(*) as count
                FROM sector_overlaps so
                GROUP BY hour
                ORDER BY hour
            """
            results = self.db.execute_query(query)

        distribution = {}
        for row in results:
            hour, count = dict(row)['hour'], dict(row)['count']
            distribution[f"{hour}:00"] = count

        return distribution

    def get_similarity_details(self, eobd=None):
        """유사호출 상세 정보"""
        if eobd:
            query = """
                SELECT
                    s.id,
                    f1.callsign as callsign_1,
                    f2.callsign as callsign_2,
                    s.similarity_level,
                    COUNT(DISTINCT so.id) as overlap_count,
                    GROUP_CONCAT(DISTINCT so.sector_name) as sectors,
                    MIN(so.overlap_start) as first_overlap_start,
                    MAX(so.overlap_end) as last_overlap_end
                FROM similarities s
                JOIN flights f1 ON s.flight_id_1 = f1.id
                JOIN flights f2 ON s.flight_id_2 = f2.id
                LEFT JOIN sector_overlaps so ON s.id = so.similarity_id
                WHERE f1.eobd = ?
                GROUP BY s.id
                ORDER BY s.id
            """
            results = self.db.execute_query(query, [eobd])
        else:
            query = """
                SELECT
                    s.id,
                    f1.callsign as callsign_1,
                    f2.callsign as callsign_2,
                    s.similarity_level,
                    COUNT(DISTINCT so.id) as overlap_count,
                    GROUP_CONCAT(DISTINCT so.sector_name) as sectors,
                    MIN(so.overlap_start) as first_overlap_start,
                    MAX(so.overlap_end) as last_overlap_end
                FROM similarities s
                JOIN flights f1 ON s.flight_id_1 = f1.id
                JOIN flights f2 ON s.flight_id_2 = f2.id
                LEFT JOIN sector_overlaps so ON s.id = so.similarity_id
                GROUP BY s.id
                ORDER BY s.id
            """
            results = self.db.execute_query(query)

        details = []
        for row in results:
            row_dict = dict(row)
            details.append({
                'similarity_id': row_dict['id'],
                'flight_1': row_dict['callsign_1'],
                'flight_2': row_dict['callsign_2'],
                'level': row_dict['similarity_level'],
                'overlap_count': row_dict['overlap_count'],
                'sectors': row_dict['sectors'],
                'first_overlap': row_dict['first_overlap_start'],
                'last_overlap': row_dict['last_overlap_end']
            })

        return details

    def get_hourly_from_similarities(self, eobd=None):
        """유사호출 기준으로 시간대별 카운트 (중복 제거)"""
        if eobd:
            query = """
                SELECT
                    strftime('%H', so.overlap_start) as hour,
                    COUNT(DISTINCT s.id) as count
                FROM sector_overlaps so
                JOIN similarities s ON so.similarity_id = s.id
                JOIN flights f1 ON s.flight_id_1 = f1.id
                WHERE f1.eobd = ?
                GROUP BY hour
                ORDER BY hour
            """
            results = self.db.execute_query(query, [eobd])
        else:
            query = """
                SELECT
                    strftime('%H', so.overlap_start) as hour,
                    COUNT(DISTINCT s.id) as count
                FROM sector_overlaps so
                JOIN similarities s ON so.similarity_id = s.id
                GROUP BY hour
                ORDER BY hour
            """
            results = self.db.execute_query(query)

        distribution = {}
        for row in results:
            hour, count = dict(row)['hour'], dict(row)['count']
            distribution[f"{hour}:00"] = count

        return distribution

    def check_consistency(self, eobd=None):
        """데이터 일관성 검증"""
        print("\n" + "="*80)
        print("📊 데이터 일관성 검증")
        print("="*80)

        if eobd:
            print(f"\n🔍 검증 대상: {eobd}")
        else:
            print(f"\n🔍 검증 대상: 전체 데이터")

        # 1. 전체 유사호출 건수
        print("\n" + "-"*80)
        print("1️⃣  전체 유사호출 건수")
        print("-"*80)

        total_similarities = self.get_db_total_similarities(eobd)
        print(f"✅ 데이터베이스 (similarities 테이블): {total_similarities}건")

        # 2. 상세 정보
        print("\n" + "-"*80)
        print("2️⃣  유사호출 상세 정보")
        print("-"*80)

        similarity_details = self.get_similarity_details(eobd)
        if similarity_details:
            for i, detail in enumerate(similarity_details, 1):
                print(f"\n[{i}] ID: {detail['similarity_id']}")
                print(f"    항공편: {detail['flight_1']} ↔ {detail['flight_2']}")
                print(f"    유사도 레벨: {detail['level']}")
                print(f"    섹터 겹침: {detail['overlap_count']}개")
                print(f"    섹터: {detail['sectors']}")
                print(f"    시간: {detail['first_overlap']} ~ {detail['last_overlap']}")
        else:
            print("⚠️  유사호출 데이터 없음")

        # 3. 시간대별 분포 (sector_overlaps 기준)
        print("\n" + "-"*80)
        print("3️⃣  시간대별 분포 (sector_overlaps 기준)")
        print("-"*80)

        hourly_by_overlaps = self.get_db_hourly_distribution(eobd)
        total_overlaps = sum(hourly_by_overlaps.values())

        print(f"\n전체 합계: {total_overlaps}건 (sector_overlaps)")
        print("\n시간대별 분포:")
        for hour in sorted(hourly_by_overlaps.keys()):
            count = hourly_by_overlaps[hour]
            bar = "█" * count
            print(f"  {hour}: {bar} {count}건")

        # 4. 시간대별 분포 (similarities 기준 - 중복 제거)
        print("\n" + "-"*80)
        print("4️⃣  시간대별 분포 (similarities 기준 - 중복 제거)")
        print("-"*80)

        hourly_by_similarities = self.get_hourly_from_similarities(eobd)
        total_by_sim = sum(hourly_by_similarities.values())

        print(f"\n전체 합계: {total_by_sim}건 (각 유사호출 1회만 카운트)")
        print("\n시간대별 분포:")
        for hour in sorted(hourly_by_similarities.keys()):
            count = hourly_by_similarities[hour]
            bar = "█" * count
            print(f"  {hour}: {bar} {count}건")

        # 5. 대시보드 비교
        print("\n" + "-"*80)
        print("5️⃣  대시보드 데이터 비교")
        print("-"*80)

        print("\n📈 대시보드에서 표시되는 값:")
        print(f"  • 검출된 유사호출: {total_similarities}건 (similarities 테이블)")
        print(f"  • 시간대별 차트: {total_overlaps}건 (sector_overlaps 테이블)")

        # 6. 불일치 분석
        print("\n" + "-"*80)
        print("6️⃣  불일치 원인 분석")
        print("-"*80)

        if total_similarities == total_overlaps:
            print("\n✅ 일치함! 데이터가 정상입니다.")
        else:
            print(f"\n❌ 불일치 발생!")
            print(f"   • similarities (유사호출): {total_similarities}건")
            print(f"   • sector_overlaps (겹침): {total_overlaps}건")
            print(f"   • 차이: {total_overlaps - total_similarities}건")

            print("\n🔍 원인 분석:")

            if total_overlaps > total_similarities:
                print(f"\n   ⚠️  시간대별 차트가 더 많은 이유:")
                print(f"   • 한 유사호출이 여러 섹터에서 겹칠 수 있음")
                print(f"   • 각 섹터의 겹침이 별도로 카운트됨")
                print(f"   • 예) 항공편 A-B가 4개 섹터에서 겹치면:")
                print(f"        - similarities: 1건 (유사호출 1개)")
                print(f"        - sector_overlaps: 4건 (겹침 4개)")
            elif total_overlaps < total_similarities:
                print(f"\n   ⚠️  유사호출이 더 많은 이유:")
                print(f"   • 유사호출이 감지되었지만 섹터 겹침이 없음")
                print(f"   • 겹침 기준이 다를 수 있음 (예: 2분 미만)")

            print("\n💡 권장사항:")
            print("   • 대시보드 차트는 'sector_overlaps' 기반")
            print("   • 통계 카드는 'similarities' 기반")
            print("   • 두 지표는 다른 의미를 가짐:")
            print("     - 검출된 유사호출: 유사한 항공편 쌍의 개수")
            print("     - 시간대별 차트: 겹치는 섹터의 개수")

        # 7. API 응답 비교
        print("\n" + "-"*80)
        print("7️⃣  예상되는 API 응답 구조")
        print("-"*80)

        print("\n📡 /api/statistics/detailed 응답:")
        print(json.dumps({
            "status": "success",
            "data": {
                "total_similarities": total_similarities,
                "hourly_distribution_by_date": hourly_by_overlaps,
                "recent_similarities": len(similarity_details)
            }
        }, indent=2, ensure_ascii=False))

        print("\n" + "="*80)

def main():
    """메인 함수"""
    checker = DataConsistencyChecker()

    # 전체 데이터 검증
    checker.check_consistency()

    # 특정 날짜 검증
    print("\n\n")
    print("="*80)
    print("특정 날짜 데이터 검증")
    print("="*80)

    target_date = "2025-12-20"
    print(f"\n🔍 날짜: {target_date}")

    checker.check_consistency(target_date)

if __name__ == '__main__':
    main()
