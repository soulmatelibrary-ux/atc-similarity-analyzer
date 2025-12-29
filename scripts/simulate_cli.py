#!/usr/bin/env python3
"""
CSV 파일을 입력받아 데이터베이스에 저장하고 유사호출 감지 시뮬레이션을 실행하는 CLI 도구

사용법:
    python simulate_cli.py /path/to/flightplan.csv
"""

import sys
import os
import argparse
import json
from datetime import datetime
import time

# 프로젝트 루트 경로 설정
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from database.db_manager import DatabaseManager
from core.flight_service import FlightService
from core import flight_processor
from utils.file_validator import FileValidator
from utils.logger import setup_logger
from utils.constants import SIMILARITY_LEVELS

# 로거 설정
logger = setup_logger(__name__)


class CLISimulator:
    """CSV 기반 유사호출 감지 시뮬레이션 도구"""

    def __init__(self, db_path=None):
        """
        초기화

        Args:
            db_path: 데이터베이스 경로 (None이면 기본 경로)
        """
        if db_path is None:
            db_path = os.path.join(PROJECT_DIR, 'database', 'similarity_detector.db')

        self.db = DatabaseManager(db_path)
        self.flight_service = FlightService(self.db)
        self.validator = FileValidator()

    def print_header(self, text):
        """헤더 출력"""
        print(f"\n{'=' * 80}")
        print(f"  {text}")
        print(f"{'=' * 80}")

    def print_level_definitions(self):
        """유사도 레벨 정의 출력 (v2.1)"""
        print("\n[유사도 레벨 정의 (v2.1)]")
        print("-" * 80)
        # 레벨 순서대로 정렬하여 출력
        for level, info in sorted(SIMILARITY_LEVELS.items()):
            print(f"  • {level:10s} [{info['risk']:6s}] {info['description']}")
        print("-" * 80)

    def print_step(self, step_num, text):
        """단계 출력"""
        print(f"\n[단계 {step_num}] {text}")
        print(f"{'-' * 80}")

    def print_progress(self, current, total, stage="진행 중"):
        """진행 상황 출력"""
        if total == 0:
            return
        percent = int((current / total) * 100)
        filled = int(percent / 5)
        bar = "█" * filled + "░" * (20 - filled)
        print(f"  [{bar}] {percent:3d}% ({current:,} / {total:,}) - {stage}", end='\r')

    def validate_and_load_csv(self, csv_path):
        """
        CSV 파일 검증 및 로드

        Args:
            csv_path: CSV 파일 경로

        Returns:
            list: 검증된 항공편 데이터
        """
        self.print_step(1, f"CSV 파일 검증 및 로드: {csv_path}")

        if not os.path.exists(csv_path):
            print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
            return None

        file_size = os.path.getsize(csv_path)
        print(f"  📄 파일명: {os.path.basename(csv_path)}")
        print(f"  📦 파일 크기: {file_size / (1024*1024):.2f} MB")

        try:
            # 파일 검증
            result = self.validator.validate_file(csv_path)
            if result['status'] != 'valid':
                print(f"❌ 파일 검증 실패:")
                for error in result.get('errors', []):
                    print(f"   - {error}")
                return None

            # 검증된 데이터 가져오기
            df = result.get('data')
            if df is None or len(df) == 0:
                print("❌ CSV 파일에서 항공편 데이터를 찾을 수 없습니다")
                return None

            # DataFrame을 딕셔너리 리스트로 변환
            flights_data = df.to_dict('records')

            print(f"✅ CSV 파일 검증 완료")
            print(f"  📍 로드된 항공편: {len(flights_data):,}개")

            return flights_data

        except Exception as e:
            print(f"❌ CSV 로드 중 오류: {e}")
            logger.error(f"CSV load error: {e}", exc_info=True)
            return None

    def insert_flights(self, flights_data, csv_filename):
        """
        항공편 데이터를 데이터베이스에 삽입

        Args:
            flights_data: 항공편 데이터 리스트
            csv_filename: CSV 파일명

        Returns:
            bool: 성공 여부
        """
        self.print_step(2, "데이터베이스에 항공편 데이터 삽입")

        file_size = 0  # CLI에서는 크기 추적 안 함
        start_time = time.time()

        try:
            result = self.flight_service.insert_flights_bulk(
                flights_data,
                csv_filename,
                file_size,
                process_id=None
            )

            if result['status'] != 'success':
                print(f"❌ 항공편 삽입 실패: {result['message']}")
                return False

            elapsed = time.time() - start_time
            inserted = result.get('inserted_count', 0)

            print(f"✅ 항공편 삽입 완료")
            print(f"  📍 삽입된 항공편: {inserted:,}개")
            print(f"  ⏱️  소요시간: {elapsed:.1f}초")

            return True

        except Exception as e:
            print(f"❌ 항공편 삽입 중 오류: {e}")
            logger.error(f"Flight insert error: {e}", exc_info=True)
            return False

    def process_waypoints(self):
        """
        지점별 통과시간 및 섹터 정보 계산

        Returns:
            bool: 성공 여부
        """
        self.print_step(3, "지점별 통과시간 및 섹터 정보 계산")

        start_time = time.time()

        try:
            flight_processor.process_flight_plans(self.db)

            elapsed = time.time() - start_time
            print(f"✅ 지점별 통과시간 계산 완료")
            print(f"  ⏱️  소요시간: {elapsed:.1f}초")

            return True

        except Exception as e:
            print(f"❌ 지점별 통과시간 계산 중 오류: {e}")
            logger.error(f"Waypoint processing error: {e}", exc_info=True)
            return False

    def detect_similarities(self):
        """
        유사호출 감지 시뮬레이션 실행

        Returns:
            dict: 시뮬레이션 결과
        """
        self.print_step(4, "유사호출 감지 시뮬레이션 실행")

        start_time = time.time()

        try:
            # 시뮬레이션 실행
            result = self.flight_service.detect_similarities(min_overlap_minutes=2)

            elapsed = time.time() - start_time

            if result['status'] != 'success':
                print(f"\n❌ 시뮬레이션 실패: {result['message']}")
                return result

            print(f"\n✅ 유사호출 감지 완료")
            print(f"  📍 검출된 유사호출 쌍: {result.get('count', 0):,}개")
            print(f"  ⏱️  소요시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")

            # 성능 정보
            if result.get('count', 0) > 0:
                time_per_pair = (elapsed * 1000) / result['count']
                print(f"  📊 쌍당 처리시간: {time_per_pair:.2f}ms")

            return result

        except Exception as e:
            print(f"\n❌ 시뮬레이션 중 오류: {e}")
            logger.error(f"Similarity detection error: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    def _progress_callback(self, processed, total, stage="처리 중"):
        """진행 상황 콜백"""
        self.print_progress(processed, total, stage)

    def get_statistics(self):
        """
        시뮬레이션 결과 통계 조회

        Returns:
            dict: 통계 정보
        """
        try:
            stats = self.db.get_statistics()
            return stats
        except Exception as e:
            logger.error(f"Statistics retrieval error: {e}")
            return None

    def print_statistics(self, stats):
        """통계 결과 출력"""
        self.print_step(5, "시뮬레이션 결과 통계")

        if not stats:
            print("❌ 통계 정보를 조회할 수 없습니다")
            return

        print(f"  📊 총 항공편: {stats.get('total_flights', 0):,}개")
        print(f"  📊 검출된 유사호출 쌍: {stats.get('total_similarities', 0):,}개")

        # 레벨별 분포 출력
        print("\n  [위험도 레벨별 분포]")
        dist = stats.get('level_distribution', {})
        for level, count in sorted(dist.items()):
            if level:
                print(f"  • {level:10s}: {count:,}쌍")
        print("")

        print(f"  📊 다중 섹터 겹침 쌍: {stats.get('cross_sector_overlap_pairs', 0):,}개")

        # 최다 빈도 섹터
        top_sector = stats.get('top_sector')
        if top_sector:
            print(f"  📍 최다 빈도 섹터: {top_sector['name']} ({top_sector['count']:,}회)")

        # 평균 공존 시간
        avg_coexist = stats.get('avg_coexistence_time_minutes', 0)
        print(f"  ⏱️  평균 공존 시간: {avg_coexist:.1f}분")

    def run_simulation(self, csv_path):
        """
        전체 시뮬레이션 프로세스 실행

        Args:
            csv_path: CSV 파일 경로

        Returns:
            bool: 성공 여부
        """
        self.print_header("🚀 유사호출 감지 시뮬레이션 시작")
        self.print_level_definitions()

        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        overall_start = time.time()

        # 1단계: CSV 로드
        flights_data = self.validate_and_load_csv(csv_path)
        if flights_data is None:
            return False

        # 2단계: DB에 삽입
        csv_filename = os.path.basename(csv_path)
        if not self.insert_flights(flights_data, csv_filename):
            return False

        # 3단계: 지점별 통과시간 계산
        if not self.process_waypoints():
            return False

        # 4단계: 유사호출 감지
        sim_result = self.detect_similarities()
        if sim_result['status'] != 'success':
            return False

        # 5단계: 통계 출력
        stats = self.get_statistics()
        self.print_statistics(stats)

        # 최종 요약
        overall_elapsed = time.time() - overall_start

        self.print_header("✅ 시뮬레이션 완료!")
        print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"총 소요시간: {overall_elapsed:.1f}초 ({overall_elapsed/60:.1f}분)\n")

        return True


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='CSV 파일을 이용한 유사호출 감지 시뮬레이션',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python simulate_cli.py data/t_flightplan.csv
  python simulate_cli.py /path/to/flights.csv
        """
    )

    parser.add_argument(
        'csv_file',
        help='처리할 CSV 파일 경로'
    )

    parser.add_argument(
        '--db',
        default=None,
        help='데이터베이스 경로 (기본값: database/similarity_detector.db)'
    )

    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='시뮬레이션 전에 데이터베이스를 초기화 (기존 데이터 삭제)'
    )

    args = parser.parse_args()

    # CSV 파일 경로 확인
    csv_path = args.csv_file
    if not os.path.isabs(csv_path):
        # 상대 경로인 경우 프로젝트 루트 기준
        csv_path = os.path.join(PROJECT_DIR, csv_path)

    csv_path = os.path.abspath(csv_path)

    if not os.path.exists(csv_path):
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        sys.exit(1)

    # 시뮬레이터 실행
    simulator = CLISimulator(db_path=args.db)

    # 데이터베이스 초기화 (--reset-db 옵션)
    if args.reset_db:
        # 비대화형 환경(Pipe 등)에서는 자동으로 'yes' 처리
        is_interactive = sys.stdin.isatty()
        if is_interactive:
            print("🔄 데이터베이스를 초기화하시겠습니까?")
            print("   기존의 모든 항공편, 유사호출, 통계 데이터가 삭제됩니다.")
            response = input("   계속하려면 'yes'를 입력하세요: ").strip().lower()
        else:
            response = 'yes'
            
        if response == 'yes':
            try:
                db_path = args.db or os.path.join(PROJECT_DIR, 'database', 'similarity_detector.db')
                if os.path.exists(db_path):
                    os.remove(db_path)
                    print("✅ 데이터베이스가 초기화되었습니다 (기존 파일 삭제 완료)\n")
                
                # 새 DatabaseManager 인스턴스 생성 및 시뮬레이터 갱신
                simulator = CLISimulator(db_path=args.db)
            except Exception as e:
                print(f"❌ 데이터베이스 초기화 실패: {e}\n")
                sys.exit(1)
        else:
            print("❌ 초기화가 취소되었습니다\n")
            sys.exit(1)

    try:
        success = simulator.run_simulation(csv_path)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
