"""
섹터 시간 파싱 및 겹침 계산 유틸리티
- 비행계획서의 섹터 진입/진출 시간 문자열을 파싱
- 구조화된 datetime 딕셔너리로 변환
- 두 항공편의 섹터 겹침 시간 계산
"""
import re
from datetime import datetime, time, timedelta


def parse_sector_times(sector_str, eobd_str='2024-01-01'):
    """
    섹터 진입/진출 시간 문자열을 파싱하여 datetime 딕셔너리로 변환

    Input: 'JH 08:15-08:35 JN 08:36-09:05'
    Output: {
        'JH': {'entry': datetime(...), 'exit': datetime(...)},
        'JN': {'entry': datetime(...), 'exit': datetime(...)}
    }

    Args:
        sector_str: 섹터 진입/진출 시간 문자열
        eobd_str: 날짜 문자열 (YYYY-MM-DD 형식)

    Returns:
        dict: 섹터별 진입/진출 시간 딕셔너리
    """
    sectors = {}
    if not sector_str:
        return sectors

    try:
        # Parse formats:
        # "SECTOR_NAME HH:MM-HH:MM" (with colon)
        # "SECTOR_NAME HHMM-HHMM" (without colon)
        pattern = r'(\w+)\s+(\d{2}):?(\d{2})-(\d{2}):?(\d{2})'

        for match in re.finditer(pattern, str(sector_str)):
            sector_name = match.group(1)
            entry_hh = int(match.group(2))
            entry_mm = int(match.group(3))
            exit_hh = int(match.group(4))
            exit_mm = int(match.group(5))

            try:
                base_date = datetime.strptime(eobd_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                base_date = datetime.now().date()

            sectors[sector_name] = {
                'entry': datetime.combine(base_date, time(entry_hh, entry_mm)),
                'exit': datetime.combine(base_date, time(exit_hh, exit_mm))
            }

    except Exception as e:
        print(f"Error parsing sector times: {e}")
        return {}

    return sectors


def calculate_sector_overlaps(sectors1, sectors2, min_overlap_minutes=2):
    """
    두 항공편의 섹터 겹침 시간을 계산

    Args:
        sectors1: 항공편1의 섹터 시간 딕셔너리 (parse_sector_times 결과)
        sectors2: 항공편2의 섹터 시간 딕셔너리
        min_overlap_minutes: 최소 겹침 시간 (분, 기본값: 2분)

    Returns:
        list: [
            {
                'sector': 'JH',
                'entry1': '08:15',
                'exit1': '08:35',
                'entry2': '08:20',
                'exit2': '08:40',
                'overlap_minutes': 15
            },
            ...
        ]
    """
    overlaps = []

    if not sectors1 or not sectors2:
        return overlaps

    try:
        # 공통 섹터 찾기
        common_sectors = set(sectors1.keys()) & set(sectors2.keys())

        for sector in common_sectors:
            s1_entry = sectors1[sector]['entry']
            s1_exit = sectors1[sector]['exit']
            s2_entry = sectors2[sector]['entry']
            s2_exit = sectors2[sector]['exit']

            # 겹침 시간 계산
            overlap_start = max(s1_entry, s2_entry)
            overlap_end = min(s1_exit, s2_exit)

            # 겹침이 있는지 확인
            if overlap_start < overlap_end:
                overlap_duration = overlap_end - overlap_start
                overlap_minutes = int(overlap_duration.total_seconds() / 60)

                # 최소 겹침 시간 필터링
                if overlap_minutes >= min_overlap_minutes:
                    overlaps.append({
                        'sector': sector,
                        'entry1': s1_entry.strftime('%H:%M'),
                        'exit1': s1_exit.strftime('%H:%M'),
                        'entry2': s2_entry.strftime('%H:%M'),
                        'exit2': s2_exit.strftime('%H:%M'),
                        'overlap_start': overlap_start.strftime('%H:%M'),
                        'overlap_end': overlap_end.strftime('%H:%M'),
                        'overlap_minutes': overlap_minutes
                    })

    except Exception as e:
        print(f"Error calculating sector overlaps: {e}")
        return []

    return overlaps


def get_sector_overlap_summary(overlaps):
    """
    섹터 겹침 정보를 요약 문자열로 변환

    Args:
        overlaps: calculate_sector_overlaps 결과

    Returns:
        str: "JH(15분), KH(8분)" 형식
    """
    if not overlaps:
        return ""

    return ", ".join([f"{o['sector']}({o['overlap_minutes']}분)" for o in overlaps])
