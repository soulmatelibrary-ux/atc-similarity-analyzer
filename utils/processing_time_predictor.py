#!/usr/bin/env python3
"""
CSV 처리 시간 예측 모듈
실제 처리 데이터를 기반으로 행 수에 따른 처리 시간을 예측합니다.
"""

class ProcessingTimePredictor:
    """
    처리 시간 예측 클래스
    
    베이스라인 데이터 (2025-12-25 기준):
    - 입력: 36,014건 CSV
    - 처리 단계: 4단계 (DB 저장 + 섹터 계산 + 지점별 시간 + 유사도 감지)
    - 총 소요 시간: 9분 40초 (580초)
    - 처리 속도: 약 3,730건/분 (62건/초)
    """
    
    # 실제 측정값 기반 단계별 처리 시간 (초 단위)
    PROCESSING_STEPS = {
        '단계1_db저장': {'건수': 35996, '시간': 30, '명칭': 'DB 저장'},
        '단계2_섹터계산': {'건수': 68280, '시간': 15, '명칭': '섹터 통과시간'},
        '단계3_지점시간': {'건수': 35996, '시간': 352, '명칭': '지점별 통과시간'},
        '단계4_유사도': {'건수': 35996, '시간': 183, '명칭': '유사호출 감지'},
    }
    
    # 실제 측정값
    BASELINE_RECORD_COUNT = 36014
    BASELINE_TOTAL_TIME = 580  # 초 (9분 40초)
    
    # 단계별 비율 (자동 계산)
    STEP_RATIOS = {
        '단계1_db저장': 30 / 580,      # 5.2%
        '단계2_섹터계산': 15 / 580,    # 2.6%
        '단계3_지점시간': 352 / 580,   # 60.7%
        '단계4_유사도': 183 / 580,     # 31.6%
    }
    
    @classmethod
    def predict_total_time(cls, record_count: int) -> dict:
        """
        지정된 건수에 대한 전체 처리 시간 예측
        
        Args:
            record_count: CSV 파일의 항공편 건수
            
        Returns:
            dict: {
                'total_seconds': int,
                'total_minutes': float,
                'total_formatted': str (예: "9분 40초"),
                'stages': dict (단계별 예측 시간),
                'rate': float (건/초)
            }
        """
        # 선형 비례 계산
        ratio = record_count / cls.BASELINE_RECORD_COUNT
        total_seconds = int(cls.BASELINE_TOTAL_TIME * ratio)
        total_minutes = total_seconds / 60
        
        # 단계별 예측 시간
        stages = {}
        for step_key, step_ratio in cls.STEP_RATIOS.items():
            step_seconds = int(cls.BASELINE_TOTAL_TIME * step_ratio * ratio)
            step_name = cls.PROCESSING_STEPS[step_key]['명칭']
            stages[step_name] = {
                'seconds': step_seconds,
                'minutes': step_seconds / 60,
                'percent': int(step_ratio * 100)
            }
        
        # 처리 속도
        rate = record_count / max(total_seconds, 1)
        
        # 포맷팅된 텍스트
        formatted = cls._format_time(total_seconds)
        
        return {
            'total_seconds': total_seconds,
            'total_minutes': round(total_minutes, 1),
            'total_formatted': formatted,
            'stages': stages,
            'rate_per_second': round(rate, 2),
            'rate_per_minute': round(rate * 60, 0),
            'record_count': record_count
        }
    
    @classmethod
    def predict_stage_time(cls, record_count: int, stage_name: str) -> dict:
        """
        특정 단계의 예상 처리 시간 예측
        
        Args:
            record_count: CSV 파일의 항공편 건수
            stage_name: 단계명 ('DB 저장', '섹터 통과시간', '지점별 통과시간', '유사호출 감지')
            
        Returns:
            dict: {'seconds': int, 'minutes': float, 'formatted': str}
        """
        result = cls.predict_total_time(record_count)
        
        if stage_name not in result['stages']:
            return None
        
        stage_info = result['stages'][stage_name]
        return {
            'seconds': stage_info['seconds'],
            'minutes': round(stage_info['minutes'], 1),
            'formatted': cls._format_time(stage_info['seconds']),
            'percent_of_total': stage_info['percent']
        }
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        """초를 "X분 Y초" 형식으로 포맷"""
        if seconds < 60:
            return f"{seconds}초"
        
        minutes = seconds // 60
        secs = seconds % 60
        
        if secs == 0:
            return f"{minutes}분"
        else:
            return f"{minutes}분 {secs}초"
    
    @classmethod
    def get_prediction_table(cls, record_counts: list = None) -> str:
        """
        여러 건수에 대한 예측 시간을 표 형식으로 반환
        
        Args:
            record_counts: 예측할 건수 리스트 (기본값: [5000, 10000, 20000, 30000, 36014, 50000, 100000])
            
        Returns:
            str: 포맷된 예측 테이블
        """
        if record_counts is None:
            record_counts = [5000, 10000, 20000, 30000, 36014, 50000, 100000]
        
        output = []
        output.append("=" * 80)
        output.append("📊 CSV 처리 시간 예측 테이블")
        output.append("=" * 80)
        output.append("")
        output.append(f"{'항공편 수':>12} | {'예상 시간':>12} | {'건/초':>8} | {'건/분':>10}")
        output.append("-" * 80)
        
        for count in record_counts:
            pred = cls.predict_total_time(count)
            marker = " ⭐" if count == cls.BASELINE_RECORD_COUNT else ""
            output.append(
                f"{count:>12,} | {pred['total_formatted']:>12} | "
                f"{pred['rate_per_second']:>8.0f} | {pred['rate_per_minute']:>10.0f}{marker}"
            )
        
        output.append("=" * 80)
        output.append("")
        
        return "\n".join(output)
    
    @classmethod
    def get_detailed_prediction(cls, record_count: int) -> str:
        """
        지정된 건수에 대한 상세 예측 정보 반환
        """
        pred = cls.predict_total_time(record_count)
        
        output = []
        output.append("=" * 80)
        output.append(f"📊 {record_count:,}건 CSV 파일 처리 예측")
        output.append("=" * 80)
        output.append("")
        output.append(f"  📥 입력 항공편 수: {record_count:,}건")
        output.append(f"  ⏱️  예상 총 처리 시간: {pred['total_formatted']}")
        output.append(f"  🔄 처리 속도: {pred['rate_per_second']:.0f}건/초 ({pred['rate_per_minute']:.0f}건/분)")
        output.append("")
        output.append("  📋 단계별 예상 시간:")
        output.append("")
        
        for stage_name, stage_info in pred['stages'].items():
            pct = stage_info['percent']
            formatted_time = cls._format_time(stage_info['seconds'])
            output.append(
                f"    [{pct:3d}%] {stage_name:20} {formatted_time:>12}"
            )
        
        output.append("")
        output.append("=" * 80)
        output.append("")
        
        return "\n".join(output)


if __name__ == "__main__":
    # 테스트 및 출력
    print(ProcessingTimePredictor.get_prediction_table())
    print()
    print(ProcessingTimePredictor.get_detailed_prediction(36014))
    print()
    print(ProcessingTimePredictor.get_detailed_prediction(50000))
    print()
    print(ProcessingTimePredictor.get_detailed_prediction(100000))
