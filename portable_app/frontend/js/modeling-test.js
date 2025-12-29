/**
 * 모델링 테스트 탭 - 기종 고려 고도 상승 계산
 */

class ModelingTestTab {
    constructor() {
        this.form = null;
        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
        this.setDefaultDate();
    }

    cacheElements() {
        this.form = document.getElementById('modeling-test-form');
        this.callsignInput = document.getElementById('test-callsign');
        this.aircraftInput = document.getElementById('test-aircraft-type');
        this.speedInput = document.getElementById('test-speed');
        this.altitudeInput = document.getElementById('test-altitude');
        this.deptInput = document.getElementById('test-dept');
        this.destInput = document.getElementById('test-dest');
        this.eodbInput = document.getElementById('test-eobd');
        this.eobtInput = document.getElementById('test-eobt');
        this.routeInput = document.getElementById('test-route');
        this.eetInput = document.getElementById('test-eet');

        // 결과 요소
        this.statusDiv = document.getElementById('modeling-test-status');
        this.statusText = document.getElementById('modeling-test-status-text');
        this.flightInfoCard = document.getElementById('modeling-flight-info');
        this.climbAnalysisCard = document.getElementById('modeling-climb-analysis');
        this.waypointsTable = document.getElementById('modeling-waypoints');
        this.loadingDiv = document.getElementById('modeling-loading');
        this.waypointsTbody = document.getElementById('waypoints-tbody');
    }

    bindEvents() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCalculate();
            });
        }
    }

    setDefaultDate() {
        const today = new Date().toISOString().split('T')[0];
        this.eodbInput.value = today;
    }

    /**
     * 계산 실행
     */
    async handleCalculate() {
        // 유효성 검사
        if (!this.callsignInput.value.trim()) {
            alert('콜사인을 입력해주세요.');
            return;
        }
        if (!this.aircraftInput.value) {
            alert('기종을 선택해주세요.');
            return;
        }

        this.showLoading(true);
        this.hideAllResults();

        try {
            const formData = {
                callsign: this.callsignInput.value.trim(),
                aircraft_type: this.aircraftInput.value,
                speed: this.speedInput.value.trim(),
                altitude: this.altitudeInput.value.trim() || 'F370',
                dept: this.deptInput.value.trim(),
                dest: this.destInput.value.trim(),
                eobd: this.eodbInput.value,
                eobt: this.eobtInput.value,
                route: this.routeInput.value.trim(),
                eet: this.eetInput.value.trim()
            };

            const response = await api.calculateFlight(formData);

            if (response.status === 'success') {
                this.renderResults(response);
            } else {
                this.showError(response.message || '계산에 실패했습니다.');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showError('계산 중 오류가 발생했습니다: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 결과 렌더링
     */
    renderResults(data) {
        const flightInfo = data.flight_info || {};
        const waypoints = data.waypoints || [];
        const climbAnalysis = data.climb_analysis || {};

        // 항공편 정보 표시
        this.renderFlightInfo(flightInfo);

        // 고도 상승 분석 표시
        if (climbAnalysis.method_a || climbAnalysis.method_b) {
            this.renderClimbAnalysis(climbAnalysis);
        }

        // 경유점 테이블 표시
        if (waypoints.length > 0) {
            this.renderWaypoints(waypoints);
        }
    }

    /**
     * 항공편 정보 렌더링
     */
    renderFlightInfo(flightInfo) {
        document.getElementById('result-callsign').textContent = flightInfo.callsign || '-';
        document.getElementById('result-aircraft').textContent = flightInfo.aircraft_type || '-';
        document.getElementById('result-route').textContent =
            `${flightInfo.dept_airport || '-'} → ${flightInfo.dest_airport || '-'}`;
        document.getElementById('result-speed').textContent =
            `${flightInfo.calculated_speed_kmh || '-'} km/h`;
        document.getElementById('result-speed-source').textContent =
            this.formatSpeedSource(flightInfo.speed_source);
        document.getElementById('result-climb-rate').textContent =
            `${flightInfo.climb_rate_fpm || '-'} fpm`;
        document.getElementById('result-cruise-fl').textContent =
            `FL${flightInfo.cruise_flight_level || '-'}`;
        document.getElementById('result-departure').textContent =
            flightInfo.departure_time || '-';

        this.flightInfoCard.style.display = 'block';
    }

    /**
     * 고도 상승 분석 렌더링
     */
    renderClimbAnalysis(climbAnalysis) {
        const methodA = climbAnalysis.method_a || {};
        const methodB = climbAnalysis.method_b || {};

        // Method A
        document.getElementById('method-a-climb-time').textContent =
            `${methodA.total_climb_minutes || '-'} min`;
        document.getElementById('method-a-climb-distance').textContent =
            `${methodA.climb_distance_km || '-'} km`;
        document.getElementById('method-a-cruise-distance').textContent =
            `${methodA.cruise_distance_km || '-'} km`;
        document.getElementById('method-a-total-time').textContent =
            `${methodA.total_time_minutes || '-'} min`;

        // Method B
        document.getElementById('method-b-climb-time').textContent =
            `${methodB.total_climb_minutes || '-'} min`;
        document.getElementById('method-b-climb-distance').textContent =
            `${methodB.climb_distance_km || '-'} km`;

        this.climbAnalysisCard.style.display = 'block';
    }

    /**
     * 경유점 테이블 렌더링
     */
    renderWaypoints(waypoints) {
        const rows = waypoints.map((wp, idx) => {
            const isClimbing = wp.is_climbing ? 'O' : 'X';
            const climbClass = wp.is_climbing ? 'climbing' : 'cruising';
            const climbText = wp.is_climbing ? '상승중' : '순항중';

            return `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${wp.name || '-'}</td>
                    <td>${wp.estimated_time || '-'}</td>
                    <td>${wp.altitude_ft || '-'}</td>
                    <td><span class="${climbClass}">${climbText}</span></td>
                </tr>
            `;
        }).join('');

        this.waypointsTbody.innerHTML = rows;
        this.waypointsTable.style.display = 'block';
    }

    /**
     * 속도 출처 레이블
     */
    formatSpeedSource(source) {
        const sources = {
            'csv': 'CSV 입력',
            'aircraft_profile': '기종 기본값',
            'default': '시스템 기본값'
        };
        return sources[source] || source || '-';
    }

    /**
     * 에러 메시지 표시
     */
    showError(message) {
        this.statusText.textContent = `❌ ${message}`;
        this.statusDiv.style.display = 'block';
    }

    /**
     * 로딩 표시
     */
    showLoading(show) {
        this.loadingDiv.style.display = show ? 'block' : 'none';
    }

    /**
     * 모든 결과 숨기기
     */
    hideAllResults() {
        this.flightInfoCard.style.display = 'none';
        this.climbAnalysisCard.style.display = 'none';
        this.waypointsTable.style.display = 'none';
        this.statusDiv.style.display = 'none';
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.ModelingTest = new ModelingTestTab();
});
