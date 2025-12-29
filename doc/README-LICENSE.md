# 📜 라이선스 가이드

이 프로젝트는 **Dual License 모델**을 채택합니다.

## 🆓 개발/테스트 (무료)

### MIT 라이선스
- **대상**: 개인, 학생, 교육기관, 오픈소스 프로젝트
- **가격**: 무료
- **제한사항**:
  - 한 번 업로드: 최대 100항공편
  - 저장 용량: 최대 100MB
  - 데이터 보관: 30일
  - 워터마크 표시
  - 내보내기: 50개까지

### 파일
- `LICENSE-MIT.txt`: MIT 라이선스 전문

### 사용 예시
```python
# 개발 환경에서는 라이선스 파일 없이 자동 적용
python backend/app.py

# 출력:
# Development License (MIT) - Free
```

---

## 💼 상업용/기관용 (유료)

### 대상
- ✓ 정부 기관
- ✓ 기업 (항공사, 공항, 관제 센터)
- ✓ 상용 서비스 제공자
- ✓ 컨설팅 회사

### 포함 내용
- ✓ 무제한 사용
- ✓ 기술 지원 (24시간 이메일, 업무시간 전화)
- ✓ 맞춤 개발
- ✓ 업데이트 및 유지보수
- ✓ SLA 보장

### 가격 (참고)
| 규모 | 요금 | 기간 |
|------|------|------|
| 스타트업 | ₩5,000,000 | 1년 |
| 중소기업 | ₩15,000,000 | 1년 |
| 대형기업 | 협상 | 3년 |
| 정부기관 | 협상 | 3년 |

### 라이선스 신청 프로세스

**1단계: 라이선스 신청**
```
이메일: license@callsign-detector.com
제목: [라이선스 신청] 기관명

내용:
- 기관명
- 사용 목적
- 예상 항공편 수
- 담당자 정보
- 연락처
```

**2단계: 견적서 발급**
- 2~3일 이내 회신
- 맞춤 요청사항 협의

**3단계: 계약서 체결**
- 법무 검토
- 서명

**4단계: 라이선스 키 발급**
```json
{
  "type": "commercial",
  "license_key": "LIC-ABC123XYZ789...",
  "organization": "Korean Airlines",
  "expiry_date": "2026-01-01",
  "signature": "...",
  "support_email": "support@callsign-detector.com"
}
```

**5단계: 설치 및 검증**
```bash
# .license/license.json 에 라이선스 파일 저장
mkdir -p .license
cat > .license/license.json << 'EOF'
{
  "type": "commercial",
  "license_key": "...",
  ...
}
EOF

# 재시작
python backend/app.py

# 출력:
# Commercial License - Valid for 365 more days
```

---

## 🔧 개발자를 위한 라이선스 검증

### 라이선스 확인
```python
from utils.license_manager import get_license_manager

manager = get_license_manager()

# 라이선스 타입 확인
if manager.is_development():
    print("Development mode")
elif manager.is_commercial():
    print("Commercial mode")

# 라이선스 정보 조회
info = manager.get_license_info()
print(f"Type: {info['type']}")
print(f"Valid: {info['is_valid']}")
print(f"Message: {info['message']}")

# 기능 제한 확인
limits = manager.get_limits()
print(f"Max flights: {limits['max_flights_per_upload']}")
print(f"Max storage: {limits['max_storage_mb']}MB")
```

### 기능 제한 확인
```python
# API에서 사용 예시
from utils.license_manager import get_license_manager

manager = get_license_manager()
limits = manager.get_limits()

# 업로드 항공편 수 체크
if len(flights) > limits['max_flights_per_upload']:
    return {"error": "Upload limit exceeded"}

# 저장 용량 체크
if storage_used > limits['max_storage_mb'] * 1024 * 1024:
    return {"error": "Storage limit exceeded"}
```

### 상업용 기능 보호
```python
from utils.license_manager import commercial_only

@commercial_only
def advanced_analytics():
    """상업용 라이선스에서만 사용 가능"""
    return calculate_advanced_metrics()
```

---

## 📋 라이선스 유지보수

### 라이선스 갱신
- 만료 30일 전: 자동 알림
- 만료 후: 기능 제한 (워터마크, 용량 제한)

### 라이선스 이전
- 기관 변경: 라이선스 재발급 필요
- 서버 이전: 무료 (동일 기관)

### 환불 정책
- 30일 이내: 전액 환불
- 30일 초과: 월할 환불

---

## ⚖️ 라이선스 위반 시

### 1단계: 경고 (30일)
- 통지장 발송
- 30일 내 개선 요청

### 2단계: 정지 (90일)
- 시스템 접근 차단
- 데이터 백업 제공

### 3단계: 법적 조치
- 손해배상 청구
- 형사 고발 (심각한 경우)

---

## 📞 라이선스 문의

| 항목 | 정보 |
|------|------|
| **이메일** | license@callsign-detector.com |
| **전화** | +82-2-XXXX-XXXX |
| **웹사이트** | https://callsign-detector.com |
| **업무 시간** | 평일 09:00 ~ 18:00 (한국 표준시) |

---

## 📚 관련 파일

- `LICENSE.md`: 전체 라이선스 정책
- `LICENSE-MIT.txt`: MIT 라이선스 전문
- `utils/license_manager.py`: 라이선스 검증 코드
- `.license/license.json`: 라이선스 파일 (상업용)

---

**마지막 업데이트**: 2025-12-27
