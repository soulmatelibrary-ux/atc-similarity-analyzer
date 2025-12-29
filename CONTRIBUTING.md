# 🤝 기여 가이드 (Contributing Guide)

Airspace-Sim-Station 프로젝트에 기여해주셔서 감사합니다! 이 문서는 협력 방법, 코드 스타일, 제출 프로세스 등을 설명합니다.

## 📋 목차

1. [행동 수칙](#행동-수칙)
2. [기여 방법](#기여-방법)
3. [개발 환경 설정](#개발-환경-설정)
4. [코드 스타일](#코드-스타일)
5. [커밋 메시지](#커밋-메시지)
6. [Pull Request](#pull-request)
7. [테스트](#테스트)
8. [문서작성](#문서작성)

---

## 🎯 행동 수칙

모든 기여자는 다음의 행동 수칙을 따라야 합니다:

- ✅ 존중하고 포용적인 태도 유지
- ✅ 건설적인 피드백 제공
- ✅ 타인의 의견 경청
- ✅ 성과, 능력, 배경과 상관없이 모든 사람 존중

**부적절한 행동**:
- ❌ 괴롭힘, 차별, 폭력적 행동
- ❌ 개인적 공격
- ❌ 무시하는 태도

---

## 🚀 기여 방법

### 버그 리포트

**버그를 발견했나요?** 이슈를 제출해주세요!

```bash
# 1. 기존 이슈 확인
# https://github.com/YOUR_USERNAME/Airspace-Sim-Station/issues 방문

# 2. 새 이슈 생성 (존재하지 않는 경우)
# [Bug Report] 제목
```

**이슈 제출 시 포함사항**:
- 명확한 제목과 설명
- 재현 단계 (Step to reproduce)
- 예상 동작 (Expected behavior)
- 실제 동작 (Actual behavior)
- 스크린샷/로그 (가능한 경우)
- 환경 정보:
  - OS (macOS, Linux, Windows)
  - Python 버전
  - 브라우저 (프론트엔드 관련 시)

**예시**:
```markdown
## 버그 설명
항공편 업로드 중에 "라이선스 제한" 에러가 발생합니다.

## 재현 단계
1. 150개 항공편이 포함된 CSV 파일 준비
2. CSV 관리 탭에서 "파일 업로드" 클릭
3. 파일 선택 후 업로드

## 예상 결과
파일이 정상적으로 업로드됨

## 실제 결과
"라이선스 제한: 한 번에 최대 100개 항공편까지만 업로드할 수 있습니다" 메시지 표시

## 환경
- OS: macOS 14.5
- Python: 3.11
- 라이선스: Development (MIT)
```

### 기능 요청

**새로운 기능을 원하시나요?** 제안해주세요!

```markdown
## [Feature] 원하는 기능 제목

## 설명
이 기능이 필요한 이유와 어떻게 도움이 될지 설명

## 제안된 구현
구현 방법에 대한 아이디어 (선택사항)

## 대안
고려한 다른 방법들 (선택사항)
```

### 문서 개선

문서가 부족하거나 명확하지 않은 부분이 있나요?

- 오타 수정
- 설명 개선
- 예시 추가
- 새로운 가이드 작성

---

## 🔧 개발 환경 설정

### 1. 저장소 포크

```bash
# GitHub에서 "Fork" 버튼 클릭
# https://github.com/YOUR_USERNAME/Airspace-Sim-Station/fork
```

### 2. 로컬 클론

```bash
git clone https://github.com/YOUR_USERNAME/Airspace-Sim-Station.git
cd Airspace-Sim-Station
git remote add upstream https://github.com/YOUR_USERNAME/Airspace-Sim-Station.git
```

### 3. 개발 브랜치 생성

```bash
# 최신 코드로 동기화
git fetch upstream
git rebase upstream/main

# 기능 브랜치 생성
git checkout -b feature/your-feature-name
# 또는
git checkout -b fix/bug-description
```

### 4. 환경 설정

```bash
# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# 개발 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt  # pytest, flake8 등

# 데이터베이스 초기화 (개발용)
python database/init_db.py
```

### 5. 애플리케이션 실행

```bash
# 터미널 1: 백엔드 API
python backend/app.py

# 터미널 2: 프론트엔드 서버 (필요한 경우)
cd frontend
python -m http.server 3000
```

접근: http://localhost:3000

---

## 💻 코드 스타일

### Python 코드 스타일 (PEP 8)

```python
# ✅ Good
def calculate_similarity_score(callsign1, callsign2):
    """
    두 콜사인의 유사도를 계산합니다.

    Args:
        callsign1 (str): 첫 번째 콜사인
        callsign2 (str): 두 번째 콜사인

    Returns:
        float: 유사도 점수 (0-100)
    """
    if not callsign1 or not callsign2:
        return 0.0

    score = compute_similarity(callsign1, callsign2)
    return max(0, min(100, score))

# ❌ Bad
def calc_sim(a,b):
    if a and b:
        s = compute_similarity(a,b)
        return s
    return 0
```

**규칙**:
- 들여쓰기: 4칸 스페이스
- 라인 길이: 최대 100글자
- 함수/클래스 이름: `snake_case`
- 상수: `UPPER_CASE`
- 문서화: docstring 필수 (Google 형식)

### JavaScript 코드 스타일

```javascript
// ✅ Good
async function loadLicenseInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/license/info`);
        if (!response.ok) {
            console.warn('라이선스 정보 로드 실패');
            return null;
        }

        const data = await response.json();
        return data.data;
    } catch (error) {
        console.error('라이선스 로드 오류:', error);
        return null;
    }
}

// ❌ Bad
function load_license_info(){
let response=fetch(API_BASE_URL+'/license/info')
if(response.ok){return response.json()}
}
```

**규칙**:
- 들여쓰기: 4칸 스페이스
- 함수/변수 이름: `camelCase`
- 상수: `UPPER_CASE`
- 세미콜론 사용
- `const`/`let` 사용 (var 금지)

### HTML/CSS 스타일

```html
<!-- ✅ Good -->
<div class="license-info" id="license-info">
    <span class="license-type">개발용 라이선스</span>
    <span class="license-status">유효함</span>
</div>

<!-- ❌ Bad -->
<div class='license' ID='license'>
<span class='type'>개발용</span>
</div>
```

**규칙**:
- 클래스: `kebab-case`
- ID: `camelCase` (가능하면 사용 자제)
- 속성: 큰따옴표 사용
- 들여쓰기: 4칸 스페이스

### 코드 품질 검사

```bash
# Python 코드 검사
flake8 backend/ utils/ core/
black backend/ utils/ core/  # 자동 포맷팅

# JavaScript 코드 검사 (eslint 설치 후)
eslint frontend/js/
```

---

## 📝 커밋 메시지

명확한 커밋 메시지를 작성해주세요.

### 형식

```
[TYPE] 간단한 설명 (50자 이내)

더 자세한 설명이 필요한 경우
여러 줄로 작성할 수 있습니다.
- 불릿 포인트도 가능합니다
- 이유와 변경사항을 명확히 설명해주세요

Fixes #123  # 이슈 번호 (있는 경우)
```

### TYPE 종류

- `[FEAT]` - 새로운 기능
- `[FIX]` - 버그 수정
- `[REFACTOR]` - 코드 리팩토링
- `[DOCS]` - 문서 추가/수정
- `[TEST]` - 테스트 추가/수정
- `[STYLE]` - 코드 스타일 (로직 무관)
- `[CHORE]` - 의존성, 설정 등

### 예시

```
[FEAT] 라이선스 정보를 헤더에 표시

- 라이선스 타입과 유효 여부 헤더에 추가
- 상업용/개발용 구별하여 색상 표시
- /api/license/info 엔드포인트 활용

Fixes #45
```

```
[FIX] CSV 업로드 중 라이선스 체크 오류

개발용 라이선스에서 100개 이상 항공편 업로드 시
스택 트레이스 없이 종료되는 문제 수정

- 명확한 에러 메시지 추가
- 로그 기록 추가
- 테스트 케이스 추가
```

---

## 🔄 Pull Request

### PR 생성 전

```bash
# 최신 코드로 동기화
git fetch upstream
git rebase upstream/main

# 테스트 실행
pytest tests/
flake8 backend/ utils/ core/

# 로컬에서 변경 확인
python backend/app.py
```

### PR 제출

1. GitHub에서 "Pull Requests" 탭 → "New Pull Request"
2. 기본 저장소: `YOUR_USERNAME/Airspace-Sim-Station`
3. 비교 브랜치: 자신의 `feature/your-feature-name`

### PR 설명 템플릿

```markdown
## 설명
이 PR이 해결하는 것을 간단히 설명해주세요.

## 변경 사항
- 변경 항목 1
- 변경 항목 2
- 변경 항목 3

## 유형
- [ ] 버그 수정 (Bug fix)
- [ ] 새로운 기능 (New feature)
- [ ] 기능 개선 (Enhancement)
- [ ] 문서 수정 (Documentation)
- [ ] 리팩토링 (Refactoring)

## 테스트
- [ ] 테스트 실행 완료
- [ ] 새로운 테스트 추가됨
- [ ] 기존 테스트 모두 통과

## 체크리스트
- [ ] 코드 리뷰를 요청했습니다
- [ ] 변경사항이 문서에 반영되었습니다
- [ ] 추가 의존성은 없습니다
- [ ] 로컬에서 테스트했습니다

## 스크린샷 (UI 변경 시)
변경 전/후 스크린샷 추가

## 관련 이슈
Fixes #123

## 추가 노트
다른 검토자가 알아야 할 내용
```

### PR 리뷰 대응

1. 코드 리뷰 의견 수렴
2. 요청된 변경사항 수정
3. 수정 후 "request review" 클릭
4. 각 댓글에 "Resolved" 표시

```bash
# 추가 커밋으로 피드백 반영
git add .
git commit -m "[REVIEW] Address review comments"
git push origin feature/your-feature-name
```

---

## ✅ 테스트

### 테스트 작성 가이드

```python
# tests/test_similarity.py
import pytest
from core.similarity_engine import check_similarity

class TestSimilarityEngine:
    """유사도 엔진 테스트"""

    def test_identical_callsigns(self):
        """동일한 콜사인은 100점"""
        score = check_similarity("AAL123", "AAL123")
        assert score == 100

    def test_no_similarity(self):
        """전혀 다른 콜사인"""
        score = check_similarity("AAL123", "XYZ789")
        assert 0 <= score < 50

    def test_partial_similarity(self):
        """부분 유사성"""
        score = check_similarity("AAL123", "AAL124")
        assert 50 <= score < 100

    @pytest.mark.parametrize("call1,call2", [
        ("AAL123", "AAL124"),
        ("AAL123", "ALA123"),
    ])
    def test_multiple_cases(self, call1, call2):
        """여러 경우 테스트"""
        score = check_similarity(call1, call2)
        assert 50 <= score <= 100
```

### 테스트 실행

```bash
# 모든 테스트 실행
pytest tests/

# 특정 파일 테스트
pytest tests/test_similarity.py

# 커버리지 확인
pytest --cov=core --cov=utils tests/

# 자세한 출력
pytest -v tests/
```

### 테스트 체크리스트

- [ ] 새 기능에 대한 테스트 작성됨
- [ ] 기존 테스트 모두 통과
- [ ] 커버리지 85% 이상 (권장)
- [ ] 엣지 케이스 테스트됨

---

## 📖 문서작성

### 문서 위치

- **개발 문서**: `doc/DEVELOPMENT/`
- **라이선스**: `doc/LICENSE.md`, `doc/README-LICENSE.md`
- **문제 해결**: `doc/TROUBLESHOOTING/`
- **아카이브**: `doc/ARCHIVES/`

### 문서 작성 규칙

```markdown
# 제목 (H1)

명확한 소개 문단

## 하위 제목 (H2)

### 더 자세한 제목 (H3)

- 불릿 포인트
- 코드 예시 포함
- 스크린샷 추가 권장

### 코드 예시

\`\`\`python
# 코드
\`\`\`

### 표

| 항목 | 설명 |
|------|------|
| A | 설명1 |
| B | 설명2 |
```

### 문서 체크리스트

- [ ] 제목이 명확합니다
- [ ] 목차가 있습니다 (긴 문서)
- [ ] 코드 예시가 실행 가능합니다
- [ ] 스크린샷이 최신입니다
- [ ] 링크가 유효합니다

---

## 🎓 학습 자료

### 아키텍처 이해하기

- [아키텍처 설명서](doc/DEVELOPMENT/ARCHITECTURE.md)
- [API 문서](doc/DEVELOPMENT/API.md)
- [데이터베이스 스키마](doc/DEVELOPMENT/DATABASE.md)

### 개발 주제별 가이드

- [라이선스 시스템](doc/DEVELOPMENT/LICENSE_SYSTEM.md)
- [유사도 계산](doc/DEVELOPMENT/SIMILARITY_GUIDE.md)
- [섹터 겹침 분석](doc/DEVELOPMENT/SECTOR_ANALYSIS.md)

---

## 📞 도움 받기

### 질문이 있으신가요?

1. **문서 확인**: [doc/](doc/) 폴더의 가이드 확인
2. **기존 이슈 검색**: 비슷한 질문이 있는지 확인
3. **Discussion 열기**: GitHub Discussion에서 질문
4. **이메일**: support@airspace-sim-station.local

### 커뮤니티

- GitHub Issues: 버그 리포트, 기능 요청
- GitHub Discussions: 질문, 아이디어
- Pull Requests: 코드 리뷰, 협력

---

## 🎉 기여 후

감사합니다! PR이 merge된 후:

- ✅ 메인 브랜치로 병합됨
- 📝 CHANGELOG.md에 기여자 이름 추가됨
- 🏅 프로필에 기여자 배지 표시 (선택사항)
- 🎓 다음 릴리스에서 감사 인사 공지

---

## 📜 라이선스

이 프로젝트에 기여함으로써, 당신의 기여는 MIT 라이선스 및 상업용 라이선스를 따릅니다.

---

**행복한 코딩! 🚀**

마지막 업데이트: 2025-12-27

