"""
경유점 간 거리 계산 모듈 (옵션)
실제 waypoint 좌표를 기반으로 대원거리(Great Circle Distance) 계산
"""

import math

# 주요 waypoint 좌표 데이터베이스 (위도, 경도)
WAYPOINT_DATABASE = {
    # 인천/금포공항 주변
    'RKSI': (37.4692, 126.4494),   # 인천국제공항
    'RKSN': (37.1397, 127.0136),   # 서울기지

    # 한반도 주요 waypoint
    'BEDES': (36.1511, 126.8119),  # 서해상
    'ELPOS': (35.9028, 126.7853),  # 서해상
    'MANGI': (35.5028, 126.7419),  # 남해상
    'DALSU': (35.1253, 126.7017),  # 남해상
    'NULDI': (34.4206, 126.6275),  # 남해상
    'DOTOL': (34.2542, 126.6103),  # 남해상
    'KIDOS': (33.8411, 126.5672),  # 남해상
    'REMOS': (33.4347, 126.3914),  # 제주해협
    'PANSI': (33.0036, 126.2069),  # 제주
    'DOMKO': (32.4800, 125.9828),  # 동중국해
    'PONIK': (32.0058, 125.7828),  # 동중국해
    'IKEDO': (31.7206, 125.6633),  # 동중국해
    'KANKA': (31.5319, 125.5844),  # 동중국해
    'BONSO': (30.4778, 125.1475),  # 동중국해
    'MUGUS': (30.0017, 124.9533),  # 동중국해

    # 기타 주요 공항
    'VHHH': (22.3080, 113.9185),   # 홍콩
    'ZJSA': (30.2282, 120.4357),   # 상하이
    'RJTT': (35.5494, 139.7798),   # 도쿄 나리타
    'RJAA': (35.7653, 140.3859),   # 도쿄 성田
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    두 지점 간의 대원거리(Great Circle Distance) 계산

    Args:
        lat1, lon1: 시작점 위도, 경도
        lat2, lon2: 도착점 위도, 경도

    Returns:
        거리 (킬로미터)
    """
    R = 6371  # 지구 반경 (km)

    # 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine 공식
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    distance = R * c
    return distance

def calculate_route_distance(waypoint_list):
    """
    경로의 총 거리 계산

    Args:
        waypoint_list: waypoint 이름 리스트 (예: ['RKSI', 'BEDES', 'ELPOS'])

    Returns:
        총 거리 (km)
    """
    total_distance = 0

    for i in range(len(waypoint_list) - 1):
        current = waypoint_list[i].upper()
        next_wp = waypoint_list[i + 1].upper()

        # 좌표 조회
        if current not in WAYPOINT_DATABASE or next_wp not in WAYPOINT_DATABASE:
            # 데이터가 없으면 근사값 사용 (60km/leg)
            total_distance += 60
            continue

        lat1, lon1 = WAYPOINT_DATABASE[current]
        lat2, lon2 = WAYPOINT_DATABASE[next_wp]

        leg_distance = haversine_distance(lat1, lon1, lat2, lon2)
        total_distance += leg_distance

    return total_distance

# 테스트
if __name__ == '__main__':
    # 예시 1: RKSI → BEDES → ELPOS
    route1 = ['RKSI', 'BEDES', 'ELPOS']
    dist1 = calculate_route_distance(route1)
    print(f"Route {route1}: {dist1:.1f}km")

    # 예시 2: RKSI → VHHH (인천 → 홍콩)
    route2 = ['RKSI', 'VHHH']
    dist2 = calculate_route_distance(route2)
    print(f"Route {route2}: {dist2:.1f}km")

    # 예시 3: RKSI → BEDES → MANGI → MUGUS
    route3 = ['RKSI', 'BEDES', 'MANGI', 'MUGUS']
    dist3 = calculate_route_distance(route3)
    print(f"Route {route3}: {dist3:.1f}km")
