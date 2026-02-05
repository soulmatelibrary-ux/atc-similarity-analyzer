@echo off
chcp 65001 >nul
title Modeling Test GUI

echo ========================================
echo   비행계획서 모델링 테스트 GUI
echo ========================================
echo.

REM 현재 디렉토리를 스크립트 위치로 설정
cd /d "%~dp0"

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

REM GUI 실행
echo [INFO] GUI를 시작합니다...
python modeling_test_gui.py

pause
