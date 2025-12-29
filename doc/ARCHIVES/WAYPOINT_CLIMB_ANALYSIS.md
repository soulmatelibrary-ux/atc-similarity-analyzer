# 웨이포인트 계산 로직 상세 분석 및 개선안

**Date:** December 26, 2025
**Status:** 기존 코드 검토 완료

## 현재 구현 상태 분석

### 1. 기존 Stateful Climb Logic (v2.1) 검토

**위치:** `/core/flight_processor.py` (lines 305-414)

#### ✅ 현재 구현의 우수한 점

```python
# 1. 항공 기종별 climb_rate 사용
climb_rate_fpm = profile_climb if profile_climb and profile_climb > 0 else DEFAULT_CLIMB_FPM
# → B77L: 2000 fpm, B744: 1800 fpm 등 기종별로 다른 값 사용

# 2. Departure 공항 좌표로 정확한 거리 계산
AIRPORT_COORDS = {
    'RKSI': (37.4606, 126.4407),  # Incheon
    'RKSS': (37.5583, 126.7906),  # Gimpo
    ...
}
dist_to_wp1 = haversine(dept_loc[0], dept_loc[1], first_wp['lat'], first_wp['lon'])

# 3. 상승/순항 페이즈 구분
if dist_to_toc <= segment_dist:
    # 이 구간에서 순항 고도에 도달
else:
    # 이 구간에서 계속 상승

# 4. 각 웨이포인트마다 현재 고도 추적
current_altitude_ft += altitude_gain  # 각 구간마다 누적
```

#### ⚠️ 개선 필요한 점

**문제 1: Climb Speed 고정값 (70%)**
```python
# 현재 코드 (line 335)
climb_speed_kmh = speed_kmh * 0.7 if speed_kmh else 500
```

**문제점:**
- 모든 항공기에 동일하게 순항 속도의 70%만 사용
- 실제로는 항공기 기종별로 다름:
  - 대형 항공기(B747, A380): 상승 속도 느림
  - 중형 항공기(B777, A330): 중간
  - 소형 항공기(B757, A320): 상승 속도 빠름

**권장 개선:**
```python
# 항공 기종별 상승 속도 비율
AIRCRAFT_CLIMB_SPEED_RATIO = {
    'B74': 0.65,   # B747: 65% (매우 무거움)
    'B77': 0.70,   # B777: 70%
    'B78': 0.75,   # B787: 75% (더 효율적)
    'A33': 0.68,   # A330: 68%
    'A35': 0.65,   # A350: 65%
    'A32': 0.72,   # A320: 72%
    'B75': 0.75,   # B757: 75%
    'B76': 0.74,   # B767: 74%
}

# ICAO 코드의 처음 3글자로 매칭
aircraft_prefix = aircraft_type[:3].upper()
climb_speed_ratio = AIRCRAFT_CLIMB_SPEED_RATIO.get(aircraft_prefix, 0.70)
climb_speed_kmh = speed_kmh * climb_speed_ratio
```

---

**문제 2: Cruise Speed 파싱 미흡**
```python
# 현재 코드 (lines 195-205)
speed_kmh = convert_icao_speed(speed_str, aircraft_type)
if not speed_kmh and profile_speed:
    speed_kmh = profile_speed
if not speed_kmh:
    speed_kmh = DEFAULT_SPEED_KMH
```

**문제점:**
- ICAO Speed Format 파싱 오류 가능성
  - `K0900` (900 knots) → 1667 km/h
  - `N0500` (500 knots) → 926 km/h
  - `M0.80` (Mach 0.80) → 약 850 km/h (고도에 따라 다름)
- Mach number 변환 시 기준 고도 미설정

**권장 개선:**
```python
def convert_icao_speed_improved(speed_str, altitude_fl):
    """ICAO Speed Format 정확한 파싱"""
    if not speed_str:
        return None

    speed_str = str(speed_str).strip().upper()

    # Knots 형식: K0900, N0500
    if speed_str[0] in ['K', 'N']:
        try:
            knots = int(speed_str[1:])
            return knots * 1.852  # knots to km/h
        except:
            return None

    # Mach 형식: M0.80
    if speed_str[0] == 'M':
        try:
            mach = float(speed_str[1:])
            # ISA 표준 대기에서 음속 계산
            if altitude_fl:
                temp_c = 15 - (2 * altitude_fl / 100)
            else:
                temp_c = 15  # sea level
            speed_of_sound = 661.5 * (1 + temp_c / 273.15) ** 0.5
            return mach * speed_of_sound * 1.852
        except:
            return None

    return None
```

---

**문제 3: 첫 지점 도달 시간 계산 로직**

```python
# 현재 코드 (lines 354-374)
if current_altitude_ft < target_altitude_ft:
    needed_alt = target_altitude_ft - current_altitude_ft
    time_to_toc_min = needed_alt / climb_rate if climb_rate > 0 else 999
    dist_to_toc = (time_to_toc_min / 60) * climb_speed_kmh

    if dist_to_toc <= segment_dist:
        # 이 구간에서 순항 고도 도달
        segment_time_seconds = time_climb + time_cruise
    else:
        # 이 구간에서 계속 상승
        segment_time_seconds = (segment_dist / climb_speed_kmh) * 3600
```

**개선 사항:**
- 로직은 맞지만 가독성이 낮음
- Climb phase와 cruise phase 계산이 섞여있음

**권장 개선:**
```python
def calculate_segment_time(segment_dist_km, current_alt_ft, target_alt_ft,
                          climb_rate_fpm, climb_speed_kmh, cruise_speed_kmh):
    """웨이포인트까지의 시간을 정확히 계산"""

    if current_alt_ft >= target_alt_ft:
        # 이미 순항 고도
        return {
            'time_seconds': (segment_dist_km / cruise_speed_kmh) * 3600,
            'final_altitude_ft': current_alt_ft,
            'phase': 'cruise'
        }

    # 상승 필요
    altitude_gain_needed = target_alt_ft - current_alt_ft
    time_to_toc_min = altitude_gain_needed / climb_rate_fpm
    distance_to_toc_km = (time_to_toc_min / 60) * climb_speed_kmh

    if distance_to_toc_km < segment_dist_km:
        # 이 구간에서 순항 고도 도달
        climb_time_sec = time_to_toc_min * 60
        cruise_dist_km = segment_dist_km - distance_to_toc_km
        cruise_time_sec = (cruise_dist_km / cruise_speed_kmh) * 3600

        return {
            'time_seconds': climb_time_sec + cruise_time_sec,
            'final_altitude_ft': target_alt_ft,
            'phase': 'climb_and_cruise'
        }
    else:
        # 이 구간에서는 아직 순항 고도 미도달
        segment_time_sec = (segment_dist_km / climb_speed_kmh) * 3600
        altitude_gained = (segment_time_sec / 60) * climb_rate_fpm

        return {
            'time_seconds': segment_time_sec,
            'final_altitude_ft': current_alt_ft + altitude_gained,
            'phase': 'climbing'
        }
```

---

**문제 4: EET 기반 계산과 Climb 기반 계산의 우선순위**

```python
# 현재 코드 (lines 266-304 vs 305-414)
if match:
    # EET 기반 계산 사용
    ...
else:
    # Climb 기반 계산 사용 (v2.1)
    ...
```

**개선 사항:**
- 두 방식을 비교하여 더 정확한 결과를 선택하는 로직 부재
- EET가 있더라도 climb-based validation 필요

**권장 개선:**
```python
def validate_climb_vs_eet(climb_result, eet_result):
    """두 계산 방식의 결과를 비교하고 더 정확한 것 선택"""
    climb_time = climb_result['time_seconds']
    eet_time = eet_result['time_seconds']

    difference_percent = abs(climb_time - eet_time) / eet_time * 100

    if difference_percent > 20:  # 20% 이상 차이
        # 경고 로그
        logger.warning(
            f"EET vs Climb 시간 차이 {difference_percent:.1f}% - "
            f"EET: {eet_time}s, Climb: {climb_time}s"
        )

    # climb-based가 더 정확하므로 climb 결과 우선
    return climb_result
```

---

## 2. 권장 개선 구현

### Phase 1: 항공 기종 프로필 확장

**Database Schema 개선:**
```sql
ALTER TABLE aircraft_profiles ADD COLUMN climb_speed_ratio REAL DEFAULT 0.70;
ALTER TABLE aircraft_profiles ADD COLUMN cruise_speed_kmh INTEGER;
ALTER TABLE aircraft_profiles ADD COLUMN optimum_altitude_fl INTEGER;
```

**데이터 예시:**
```sql
UPDATE aircraft_profiles SET
    climb_speed_ratio = 0.65,
    cruise_speed_kmh = 905,
    optimum_altitude_fl = 430
WHERE icao_code = 'B77L';
```

### Phase 2: 정밀 계산 함수 작성

**새로운 모듈:** `/core/waypoint_calculator.py`
```python
class WaypointCalculator:
    def __init__(self, aircraft_profile, departure_airport, route_waypoints):
        self.profile = aircraft_profile
        self.dept_airport = departure_airport
        self.route_wps = route_waypoints
        self.climb_speed_ratio = aircraft_profile.get('climb_speed_ratio', 0.70)

    def calculate_first_waypoint_time(self, dept_time, cruise_altitude_fl, cruise_speed_kmh):
        """한국 출발 첫 웨이포인트까지의 시간 정확히 계산"""
        # 구현 내용...

    def calculate_segment_times(self, segment, current_alt_fl):
        """각 구간별 시간 계산"""
        # 구현 내용...
```

---

## 3. 테스트 케이스

### Test 1: Incheon 출발, B777
```
출발: RKSI (인천)
첫 지점: BEDES (Yellow Sea, 약 100km)
기종: B77L (Climb Rate: 2000 fpm, Cruise Speed: 905 km/h)
순항 고도: FL370 (37,000 ft)
```

**예상 결과:**
- TOC 필요 고도: 37,000 ft
- 상승 시간: 37,000 / 2000 = 18.5분
- 상승 중 거리: 18.5분 / 60 × (905 × 0.70) = 약 180 km
- 100 km < 180 km이므로 순항 고도 미도달
- 총 시간: 약 8분

### Test 2: Gimpo 출발, B747
```
출발: RKSS (김포)
첫 지점: SADLI (약 150km)
기종: B744 (Climb Rate: 1800 fpm, Cruise Speed: 920 km/h)
순항 고도: FL350 (35,000 ft)
```

**예상 결과:**
- 상승 필요 시간: 35,000 / 1800 = 19.4분
- 상승 중 거리: 19.4 / 60 × (920 × 0.65) = 약 193 km
- 150 km < 193 km이므로 순항 고도 미도달
- 실제 거리로 시간 계산: 150 km / (920 × 0.65 km/h) ≈ 11분

---

## 4. 구현 체크리스트

- [ ] `aircraft_profiles` 테이블에 `climb_speed_ratio` 추가
- [ ] 항공 기종별 상승 속도 비율 데이터 입력
- [ ] `/core/waypoint_calculator.py` 모듈 생성
- [ ] `calculate_segment_time()` 함수 구현
- [ ] EET vs Climb 비교 로직 추가
- [ ] 테스트 케이스 실행
- [ ] 기존 결과와 신규 결과 비교
- [ ] 데이터베이스에 결과 저장

---

## 5. 예상 개선 효과

| 항목 | 현재 | 개선 후 |
|------|------|--------|
| Climb Speed 정확도 | 고정 70% | 기종별 최적값 (65-75%) |
| 첫 지점 도달 시간 오차 | ±5-10분 | ±1-2분 |
| 순항 고도 도달 판단 | 개략적 | 정밀 |
| EET 검증 | 미흡 | 강화 |

---

## 요약

현재 구현된 **Stateful Climb Logic (v2.1)**은 이미 매우 우수하지만:
1. **Climb Speed**를 항공 기종별로 최적화 필요
2. **ICAO Speed** 파싱 정확도 개선 필요
3. **계산 로직** 모듈화 및 검증 강화 필요
4. **EET vs Climb** 비교 검증 추가 필요

이러한 개선을 통해 **한국 출발 항공편의 첫 웨이포인트 도달 시간을 항공 기종과 고도 상승을 정확히 감안하여 계산**할 수 있습니다.
