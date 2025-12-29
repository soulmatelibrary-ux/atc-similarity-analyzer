/**
 * 메인 애플리케이션 - 초기화 및 오케스트레이션
 */

/**
 * 애플리케이션 초기화
 */
async function initializeApplication() {
    console.log('유사호출 감시 시뮬레이션 시스템 초기화 중...');

    try {
        // 1. API 헬스 체크
        const health = await api.healthCheck();
        console.log('API 헬스 체크:', health);

        // 2. UI 초기화 (ui.js에서 수행)
        // initializeUI()는 ui.js에서 자동으로 호출됨

        // 3. 페이지 로드 완료
        logApplicationStartup();

    } catch (error) {
        console.error('애플리케이션 초기화 실패:', error);
        alert('시스템 초기화 실패. 서버가 실행 중인지 확인하세요.');
    }
}

/**
 * 애플리케이션 시작 로그
 */
function logApplicationStartup() {
    console.log('%c유사호출 감지 및 시스템', 'font-size: 16px; font-weight: bold; color: #3498db;');
    console.log('%cv1.0.0 - Phase 5 Frontend', 'font-size: 12px; color: #7f8c8d;');
    console.log('%cAPI 기본 URL: ' + API_BASE_URL, 'font-size: 12px; color: #7f8c8d;');
    console.log('%c애플리케이션이 준비되었습니다.', 'font-size: 12px; color: #27ae60; font-weight: bold;');
}

/**
 * 페이지 언로드 시 정리
 */
function cleanup() {
    destroyCharts();
}

/**
 * 글로벌 에러 핸들러
 */
window.addEventListener('error', function (event) {
    console.error('예상치 못한 오류:', event.error);
});

/**
 * 언로드 이벤트 처리
 */
window.addEventListener('unload', cleanup);
window.addEventListener('beforeunload', cleanup);

// 애플리케이션 시작
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApplication);
} else {
    initializeApplication();
}

// 주기적인 시스템 상태 확인 (30초마다)
setInterval(async () => {
    try {
        // 1. 서버 연결 확인
        await api.healthCheck();
        updateSystemStatus(true, '시스템 정상');
    } catch (error) {
        updateSystemStatus(false);
    }
}, 30000);
