@echo off
chcp 65001 >nul
title ATC Similarity Analyzer

echo ========================================
echo   유사호출 감시 시뮬레이션 시스템
echo   ATC Similarity Analyzer v2.1.0
echo ========================================
echo.

:: 현재 디렉토리를 스크립트 위치로 설정
cd /d "%~dp0"

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.8 이상을 설치해주세요.
    pause
    exit /b 1
)

:: 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo [INFO] 가상환경을 활성화합니다...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] 가상환경을 활성화합니다...
    call .venv\Scripts\activate.bat
)

:: 의존성 설치 확인
echo [INFO] 의존성을 확인합니다...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [INFO] 필요한 패키지를 설치합니다...
    pip install -r requirements.txt
)

:: 서버 시작
echo.
echo [INFO] 서버를 시작합니다...
echo [INFO] 주소: http://localhost:8888
echo [INFO] 종료하려면 Ctrl+C를 누르세요.
echo.

:: 2초 후 브라우저 열기 (백그라운드)
start /b cmd /c "timeout /t 2 >nul && start http://localhost:8888"

:: Flask 앱 실행
python backend\app.py

pause
