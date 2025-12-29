@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo  유사호출 감시 시뮬레이션 시스템 - 초기 설정
echo ========================================
echo.

REM Python 경로 확인
if not exist "python-embedded\python.exe" (
    echo.
    echo [오류] Python을 찾을 수 없습니다.
    echo.
    echo 다음 단계를 따르세요:
    echo 1. https://www.python.org/downloads/ 에서 Windows Embeddable Package 다운로드
    echo    (예: python-3.12.0-embed-amd64.zip 또는 python-3.13.0-embed-amd64.zip)
    echo.
    echo 2. 다운로드한 zip 파일을 이 폴더에서 압축 해제
    echo.
    echo 3. 압축 해제된 폴더 이름을 "python-embedded"로 변경
    echo.
    echo 4. 이 파일(setup.bat)을 다시 실행
    echo.
    pause
    exit /b 1
)

echo [1/4] Python 경로 설정 중...
set "PYTHON_PATH=%cd%\python-embedded"
set "PYTHON_EXE=%PYTHON_PATH%\python.exe"
set "PIP_EXE=%PYTHON_PATH%\Scripts\pip.exe"

echo Python 위치: %PYTHON_EXE%

REM pip 활성화
echo.
echo [2/4] pip 활성화 중...
if exist "%PYTHON_PATH%\python312._pth" (
    (
        echo python312.zip
        echo .
        echo import site
    ) > "%PYTHON_PATH%\python312._pth"
    echo python312._pth 수정 완료
)
if exist "%PYTHON_PATH%\python313._pth" (
    (
        echo python313.zip
        echo .
        echo import site
    ) > "%PYTHON_PATH%\python313._pth"
    echo python313._pth 수정 완료
)

REM pip 업그레이드
echo.
echo [3/4] pip 업그레이드 중...
"%PYTHON_EXE%" -m pip install --upgrade pip setuptools wheel -q
if %errorlevel% neq 0 (
    echo pip 업그레이드 실패
    pause
    exit /b 1
)

REM 의존성 설치
echo.
echo [4/4] 필요한 패키지 설치 중 (시간이 걸릴 수 있습니다)...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 패키지 설치 실패
    pause
    exit /b 1
)

echo.
echo ========================================
echo  설정 완료!
echo ========================================
echo.
echo 이제 run.bat 을 실행하여 서버를 시작하세요.
echo.
pause
