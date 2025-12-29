@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo  유사호출 감시 시뮬레이션 시스템 시작
echo ========================================
echo.

REM Python 경로 확인
if not exist "python-embedded\python.exe" (
    echo [오류] Python을 찾을 수 없습니다.
    echo setup.bat을 먼저 실행하세요.
    pause
    exit /b 1
)

REM 환경 변수 설정
set "PYTHON_PATH=%cd%\python-embedded"
set "PYTHON_EXE=%PYTHON_PATH%\python.exe"
set "PYTHONPATH=%cd%"
set "FLASK_APP=backend\app.py"
set "FLASK_ENV=production"

echo [1/3] 데이터베이스 확인 중...
if not exist "data" mkdir data

REM 데이터베이스 초기화 (처음 실행 시에만)
if not exist "data\flights.db" (
    echo 데이터베이스가 없습니다. 초기화 중...
    "%PYTHON_EXE%" -c "from database.db_manager import DatabaseManager; DatabaseManager().initialize_database()"
    if !errorlevel! neq 0 (
        echo 데이터베이스 초기화 실패
        pause
        exit /b 1
    )
)

echo.
echo [2/3] Flask 백엔드 서버 시작 중...
echo 백엔드 서버: http://localhost:8888
echo.

REM Flask 서버 시작 (별도 창에서)
start cmd /k "cd /d %cd% && "%PYTHON_EXE%" -m flask run --host=0.0.0.0 --port=8888"

REM 서버가 시작될 때까지 대기
timeout /t 3 /nobreak

echo.
echo [3/3] 웹 브라우저 열기...
echo.

REM 브라우저 자동 오픈
start http://localhost:8888

echo.
echo ========================================
echo  시스템이 시작되었습니다!
echo ========================================
echo.
echo 브라우저가 자동으로 열립니다.
echo 또는 다음 주소를 직접 입력하세요: http://localhost:8888
echo.
echo 종료하려면 이 창을 닫으세요.
echo.
pause
