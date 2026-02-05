"""
FIX 이동시간 변환기
fixtime.txt 파일을 파싱하여 fix_travel_times_lookup.json으로 변환

fixtime.txt 형식:
    RUGMA-2146|ANROD-2212|ENGOT-2214|SARAM-2217|MASTA-2221|RKTN-2226
    각 라인은 하나의 비행 경로, FIX명-HHMM 형식으로 | 구분

fix_travel_times_lookup.json 형식:
    {
        "RUGMA": {"ANROD": 26.0, "PAPLU": 10.0},
        "ANROD": {"ENGOT": 2.0, ...},
        ...
    }
"""

import json
import os
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


def parse_hhmm_to_minutes(time_str: str) -> int:
    """
    HHMM 형식 시간을 분 단위로 변환

    Args:
        time_str: "2146", "0110" 등의 HHMM 형식 문자열

    Returns:
        총 분 (0~1439)
    """
    time_str = time_str.strip()
    if len(time_str) != 4:
        raise ValueError(f"Invalid time format: {time_str}. Expected HHMM format.")

    hours = int(time_str[:2])
    minutes = int(time_str[2:])

    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(f"Invalid time value: {time_str}")

    return hours * 60 + minutes


def calculate_time_diff(from_hhmm: str, to_hhmm: str) -> float:
    """
    두 시간의 분 차이 계산 (날짜 경계 고려)

    Args:
        from_hhmm: 출발 시간 (HHMM)
        to_hhmm: 도착 시간 (HHMM)

    Returns:
        분 단위 시간 차이

    Examples:
        calculate_time_diff("2146", "2212") → 26.0
        calculate_time_diff("2305", "0110") → 125.0 (날짜 경계 넘음)
    """
    from_min = parse_hhmm_to_minutes(from_hhmm)
    to_min = parse_hhmm_to_minutes(to_hhmm)

    diff = to_min - from_min

    # 날짜 경계 처리: 음수면 다음 날로 넘어간 것
    if diff < 0:
        diff += 24 * 60  # +1440분 (24시간)

    # 비정상적으로 큰 값 체크 (12시간 이상이면 경고)
    if diff > 720:
        logger.warning(f"Large time diff detected: {from_hhmm} → {to_hhmm} = {diff} minutes")

    return float(diff)


def parse_fixtime_line(line: str) -> List[Tuple[str, str]]:
    """
    fixtime.txt의 한 라인을 파싱하여 (FIX명, 시간) 리스트 반환

    Args:
        line: "RUGMA-2146|ANROD-2212|ENGOT-2214" 형식

    Returns:
        [("RUGMA", "2146"), ("ANROD", "2212"), ("ENGOT", "2214")]
    """
    result = []
    segments = line.strip().split('|')

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        # FIX명-시간 분리 (마지막 - 기준)
        if '-' not in segment:
            logger.warning(f"Invalid segment format (no hyphen): {segment}")
            continue

        # 마지막 '-' 위치 찾기 (FIX명에 -가 포함될 수 있음)
        last_dash = segment.rfind('-')
        fix_name = segment[:last_dash].strip()
        time_str = segment[last_dash + 1:].strip()

        if not fix_name or not time_str:
            logger.warning(f"Invalid segment: {segment}")
            continue

        # 시간 형식 검증
        if len(time_str) != 4 or not time_str.isdigit():
            logger.warning(f"Invalid time format in segment: {segment}")
            continue

        result.append((fix_name, time_str))

    return result


def parse_fixtime_file(file_content: str) -> Dict[str, Dict[str, List[float]]]:
    """
    fixtime.txt 전체 내용을 파싱하여 FIX 쌍별 시간 리스트 생성

    Args:
        file_content: fixtime.txt 파일 내용

    Returns:
        {
            "RUGMA": {"ANROD": [26.0, 25.5, 27.0], "PAPLU": [10.0, 9.5]},
            ...
        }
        각 FIX 쌍에 대해 여러 샘플의 시간값 리스트
    """
    # 중첩 defaultdict: fix_times[from_fix][to_fix] = [시간들]
    fix_times: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    lines = file_content.strip().split('\n')
    processed_lines = 0
    error_lines = 0

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):  # 빈 줄, 주석 스킵
            continue

        try:
            waypoints = parse_fixtime_line(line)

            if len(waypoints) < 2:
                logger.debug(f"Line {line_num}: Not enough waypoints")
                continue

            # 연속된 FIX 쌍의 시간차 계산
            for i in range(len(waypoints) - 1):
                from_fix, from_time = waypoints[i]
                to_fix, to_time = waypoints[i + 1]

                # 동일 FIX 연속은 스킵
                if from_fix == to_fix:
                    continue

                time_diff = calculate_time_diff(from_time, to_time)

                # 0분인 경우 스킵 (동시 통과는 비정상)
                if time_diff == 0:
                    continue

                fix_times[from_fix][to_fix].append(time_diff)

            processed_lines += 1

        except Exception as e:
            logger.error(f"Line {line_num} parse error: {e}")
            error_lines += 1

    logger.info(f"Parsed {processed_lines} lines, {error_lines} errors")

    # defaultdict를 일반 dict로 변환
    return {k: dict(v) for k, v in fix_times.items()}


def aggregate_fix_times(fix_times_raw: Dict[str, Dict[str, List[float]]],
                        method: str = 'average') -> Dict[str, Dict[str, float]]:
    """
    여러 샘플의 시간값을 하나로 집계

    Args:
        fix_times_raw: parse_fixtime_file의 결과
        method: 집계 방법 ('average', 'median', 'min', 'max')

    Returns:
        {
            "RUGMA": {"ANROD": 26.0, "PAPLU": 10.0},
            ...
        }
    """
    result = {}

    for from_fix, destinations in fix_times_raw.items():
        result[from_fix] = {}

        for to_fix, time_list in destinations.items():
            if not time_list:
                continue

            if method == 'average':
                value = sum(time_list) / len(time_list)
            elif method == 'median':
                sorted_list = sorted(time_list)
                mid = len(sorted_list) // 2
                if len(sorted_list) % 2 == 0:
                    value = (sorted_list[mid - 1] + sorted_list[mid]) / 2
                else:
                    value = sorted_list[mid]
            elif method == 'min':
                value = min(time_list)
            elif method == 'max':
                value = max(time_list)
            else:
                value = sum(time_list) / len(time_list)  # default: average

            # 소수점 첫째 자리까지 반올림
            result[from_fix][to_fix] = round(value, 1)

    return result


def convert_fixtime_to_json(file_content: str, method: str = 'average') -> Dict[str, Dict[str, float]]:
    """
    fixtime.txt 내용을 JSON 형식으로 변환 (메인 함수)

    Args:
        file_content: fixtime.txt 파일 내용
        method: 집계 방법 ('average', 'median', 'min', 'max')

    Returns:
        JSON으로 저장할 수 있는 딕셔너리
    """
    # 1. 파싱하여 FIX 쌍별 시간 리스트 생성
    raw_times = parse_fixtime_file(file_content)

    # 2. 집계하여 단일 값으로 변환
    aggregated = aggregate_fix_times(raw_times, method)

    # 3. FIX명 기준 정렬
    sorted_result = {k: dict(sorted(v.items())) for k, v in sorted(aggregated.items())}

    return sorted_result


def get_conversion_statistics(file_content: str) -> Dict:
    """
    변환 통계 정보 반환

    Args:
        file_content: fixtime.txt 파일 내용

    Returns:
        {
            "total_lines": 전체 라인 수,
            "total_fix_pairs": FIX 쌍 수,
            "total_samples": 총 샘플 수,
            "unique_fixes": 고유 FIX 수
        }
    """
    raw_times = parse_fixtime_file(file_content)

    total_pairs = 0
    total_samples = 0
    all_fixes = set()

    for from_fix, destinations in raw_times.items():
        all_fixes.add(from_fix)
        for to_fix, time_list in destinations.items():
            all_fixes.add(to_fix)
            total_pairs += 1
            total_samples += len(time_list)

    lines = [l for l in file_content.strip().split('\n') if l.strip() and not l.startswith('#')]

    return {
        "total_lines": len(lines),
        "total_fix_pairs": total_pairs,
        "total_samples": total_samples,
        "unique_fixes": len(all_fixes),
        "fix_list": sorted(all_fixes)
    }


def save_json_file(data: Dict, output_path: str) -> bool:
    """
    JSON 파일 저장

    Args:
        data: 저장할 딕셔너리
        output_path: 출력 파일 경로

    Returns:
        성공 여부
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")
        return False


def load_json_file(input_path: str) -> Optional[Dict]:
    """
    JSON 파일 로드

    Args:
        input_path: 입력 파일 경로

    Returns:
        딕셔너리 또는 None
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        return None


def update_fix_time(data: Dict[str, Dict[str, float]],
                    from_fix: str, to_fix: str, new_time: float) -> Dict[str, Dict[str, float]]:
    """
    특정 FIX 쌍의 이동시간 수정

    Args:
        data: 기존 데이터
        from_fix: 출발 FIX
        to_fix: 도착 FIX
        new_time: 새 이동시간 (분)

    Returns:
        수정된 데이터
    """
    if from_fix not in data:
        data[from_fix] = {}

    data[from_fix][to_fix] = round(new_time, 1)

    return data


def delete_fix_time(data: Dict[str, Dict[str, float]],
                    from_fix: str, to_fix: str) -> Dict[str, Dict[str, float]]:
    """
    특정 FIX 쌍 삭제

    Args:
        data: 기존 데이터
        from_fix: 출발 FIX
        to_fix: 도착 FIX

    Returns:
        수정된 데이터
    """
    if from_fix in data and to_fix in data[from_fix]:
        del data[from_fix][to_fix]

        # from_fix에 더 이상 목적지가 없으면 삭제
        if not data[from_fix]:
            del data[from_fix]

    return data


def add_fix_time(data: Dict[str, Dict[str, float]],
                 from_fix: str, to_fix: str, time_minutes: float) -> Dict[str, Dict[str, float]]:
    """
    새 FIX 쌍 추가

    Args:
        data: 기존 데이터
        from_fix: 출발 FIX
        to_fix: 도착 FIX
        time_minutes: 이동시간 (분)

    Returns:
        수정된 데이터
    """
    return update_fix_time(data, from_fix, to_fix, time_minutes)


def flatten_fix_times(data: Dict[str, Dict[str, float]]) -> List[Dict]:
    """
    중첩 딕셔너리를 플랫 리스트로 변환 (UI 테이블용)

    Args:
        data: {"RUGMA": {"ANROD": 26.0, ...}, ...}

    Returns:
        [
            {"from_fix": "RUGMA", "to_fix": "ANROD", "time_minutes": 26.0},
            ...
        ]
    """
    result = []

    for from_fix in sorted(data.keys()):
        for to_fix in sorted(data[from_fix].keys()):
            result.append({
                "from_fix": from_fix,
                "to_fix": to_fix,
                "time_minutes": data[from_fix][to_fix]
            })

    return result


def unflatten_fix_times(flat_list: List[Dict]) -> Dict[str, Dict[str, float]]:
    """
    플랫 리스트를 중첩 딕셔너리로 변환

    Args:
        flat_list: [{"from_fix": "RUGMA", "to_fix": "ANROD", "time_minutes": 26.0}, ...]

    Returns:
        {"RUGMA": {"ANROD": 26.0, ...}, ...}
    """
    result = {}

    for item in flat_list:
        from_fix = item.get("from_fix", "").strip().upper()
        to_fix = item.get("to_fix", "").strip().upper()
        time_minutes = item.get("time_minutes", 0)

        if not from_fix or not to_fix:
            continue

        if from_fix not in result:
            result[from_fix] = {}

        result[from_fix][to_fix] = round(float(time_minutes), 1)

    return result


# CLI 테스트용
if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO)

    # 테스트: 시간 차이 계산
    print("=== Time Diff Test ===")
    print(f"2146 → 2212: {calculate_time_diff('2146', '2212')} min (expected: 26)")
    print(f"2305 → 0110: {calculate_time_diff('2305', '0110')} min (expected: 125)")
    print(f"2359 → 0001: {calculate_time_diff('2359', '0001')} min (expected: 2)")

    # 테스트 데이터
    test_content = """RUGMA-2146|ANROD-2212|ENGOT-2214|SARAM-2217|MASTA-2221|RKTN-2226
RUGMA-2135|ANROD-2201|ENGOT-2203|SARAM-2206|MASTA-2210|RKTN-2215
LAMEN-2305|SADLI-2312|IKEDO-0005|ELGEP-0010"""

    print("\n=== Conversion Test ===")
    result = convert_fixtime_to_json(test_content)
    print(json.dumps(result, indent=2))

    print("\n=== Statistics ===")
    stats = get_conversion_statistics(test_content)
    print(json.dumps(stats, indent=2))
