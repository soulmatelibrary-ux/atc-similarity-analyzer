#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_APP="$PROJECT_ROOT/backend/app.py"

kill_port_process() {
    local port="$1"
    if lsof -ti tcp:"$port" >/dev/null 2>&1; then
        local pid
        pid=$(lsof -ti tcp:"$port" | head -n 1)
        local proc="$(ps -o comm= -p "$pid" 2>/dev/null)"
        echo -e "${YELLOW}포트 ${port}가 이미 사용 중입니다 → PID ${pid} (${proc:-unknown})${NC}"
        echo -e "${YELLOW}기존 프로세스를 종료합니다...${NC}"
        kill -9 "$pid" 2>/dev/null
        sleep 1
        echo -e "${GREEN}✓ PID ${pid} 프로세스 종료됨${NC}"
        return 0
    fi
    return 1
}

if [ ! -f "$BACKEND_APP" ]; then
    echo -e "${RED}백엔드 엔트리 파일을 찾을 수 없습니다: $BACKEND_APP${NC}"
    echo -e "${YELLOW}portable_app/backend/app.py를 복사했는지 확인하세요.${NC}"
    exit 1
fi

# 포트 8888 체크 및 필요시 종료
kill_port_process 8888

# 포트 8000 체크 및 필요시 종료
kill_port_process 8000

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}백엔드 & 프론트엔드 시작${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 백엔드 시작
echo -e "${YELLOW}백엔드 시작 중... (포트 8888)${NC}"
cd "$PROJECT_ROOT/backend"
python app.py &
BACKEND_PID=$!

# 프론트엔드 간단한 HTTP 서버 시작
echo -e "${YELLOW}프론트엔드 시작 중... (포트 8000)${NC}"
cd "$PROJECT_ROOT/frontend"
python -m http.server 8000 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 서비스 시작됨${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}백엔드: http://localhost:8888${NC}"
echo -e "${GREEN}프론트엔드: http://localhost:8000${NC}"
echo ""
echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요${NC}"
echo ""

# 백그라운드 프로세스 모니터링
wait_for_interrupt() {
    trap 'kill_services' INT TERM
    wait
}

kill_services() {
    echo ""
    echo -e "${YELLOW}서비스 종료 중...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}서비스 종료됨${NC}"
    exit 0
}

wait_for_interrupt
