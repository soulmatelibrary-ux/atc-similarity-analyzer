@echo off
chcp 65001 > nul

echo.
echo 유사호출 감시 시뮬레이션 시스템 서버 종료 중...
echo.

REM Flask 프로세스 종료
taskkill /f /im python.exe /t >nul 2>&1

if %errorlevel% equ 0 (
    echo 서버가 종료되었습니다.
) else (
    echo 실행 중인 서버를 찾을 수 없습니다.
)

echo.
pause
