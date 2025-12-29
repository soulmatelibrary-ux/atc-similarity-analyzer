/**
 * 고도 상승 계산 비교 시각화 모듈
 *
 * 항공편의 Method A (단순 선형)와 Method B (EET 역계산) 결과를 비교합니다.
 */

class ClimbComparisonVisualizer {
    constructor() {
        this.currentFlightId = null;
        this.currentData = null;
        this.charts = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // 비교 데이터 로드 버튼
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-climb-comparison')) {
                const flightId = e.target.dataset.flightId;
                this.loadClimbComparison(flightId);
            }
        });
    }

    /**
     * 고도 상승 계산 비교 데이터 로드
     */
    async loadClimbComparison(flightId) {
        try {
            const response = await api.getClimbComparison(flightId);

            if (response.status === 'error') {
                alert('고도 상승 계산 데이터를 로드할 수 없습니다: ' + response.message);
                return;
            }

            this.currentFlightId = flightId;
            this.currentData = response;

            // 모달 또는 패널 표시
            this.displayClimbComparisonModal(response);

        } catch (error) {
            console.error('Failed to load climb comparison:', error);
            alert('고도 상승 계산 데이터 로드 중 오류가 발생했습니다.');
        }
    }

    /**
     * 고도 상승 비교 모달 표시
     */
    displayClimbComparisonModal(data) {
        const html = `
            <div id="climbComparisonModal" class="modal">
                <div class="modal-content climb-comparison-modal">
                    <span class="close-btn" onclick="climbVisualizer.closeModal()">&times;</span>

                    <h2>고도 상승 계산 비교</h2>

                    <!-- 항공편 정보 섹션 -->
                    <div class="flight-info-section">
                        ${this.getFlightInfoHTML(data.flight_info)}
                    </div>

                    <!-- 탭 네비게이션 -->
                    <div class="climb-tabs">
                        <button class="tab-button active" data-tab="altitude-graph">고도 그래프</button>
                        <button class="tab-button" data-tab="comparison-table">비교 테이블</button>
                        <button class="tab-button" data-tab="statistics">통계</button>
                    </div>

                    <!-- 탭 콘텐츠 -->
                    <div class="tab-content">
                        <!-- 고도 그래프 -->
                        <div id="altitude-graph" class="tab-pane active">
                            <canvas id="altitudeChart"></canvas>
                        </div>

                        <!-- 비교 테이블 -->
                        <div id="comparison-table" class="tab-pane">
                            ${this.getComparisonTableHTML(data.waypoints)}
                        </div>

                        <!-- 통계 -->
                        <div id="statistics" class="tab-pane">
                            ${this.getStatisticsHTML(data.statistics)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 기존 모달 제거
        const existingModal = document.getElementById('climbComparisonModal');
        if (existingModal) existingModal.remove();

        // 새 모달 추가
        document.body.insertAdjacentHTML('beforeend', html);

        // 탭 이벤트 리스너 추가
        this.setupTabListeners();

        // 차트 그리기
        if (data.waypoints && data.waypoints.length > 0) {
            this.drawAltitudeChart(data.waypoints);
        }
    }

    /**
     * 항공편 정보 HTML 생성
     */
    getFlightInfoHTML(flightInfo) {
        if (!flightInfo) return '';

        return `
            <div class="flight-info-grid">
                <div class="info-item">
                    <span class="label">콜사인:</span>
                    <span class="value">${flightInfo.callsign || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="label">기종:</span>
                    <span class="value">${flightInfo.aircraft_type || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="label">경로:</span>
                    <span class="value">${flightInfo.dept_airport_cd || 'N/A'} → ${flightInfo.dest_airport_cd || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="label">계산 속도:</span>
                    <span class="value">${flightInfo.calculated_speed_kmh || 'N/A'} km/h</span>
                </div>
                <div class="info-item">
                    <span class="label">속도 출처:</span>
                    <span class="value">${this.getSpeedSourceLabel(flightInfo.speed_source)}</span>
                </div>
                <div class="info-item">
                    <span class="label">상승률:</span>
                    <span class="value">${flightInfo.climb_rate_fpm || 'N/A'} fpm</span>
                </div>
                <div class="info-item">
                    <span class="label">순항 고도:</span>
                    <span class="value">FL ${flightInfo.cruise_flight_level || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="label">출발 시간:</span>
                    <span class="value">${flightInfo.eobt || 'N/A'}</span>
                </div>
            </div>
        `;
    }

    /**
     * 비교 테이블 HTML 생성
     */
    getComparisonTableHTML(waypoints) {
        if (!waypoints || waypoints.length === 0) {
            return '<p class="no-data">비교 데이터가 없습니다.</p>';
        }

        const rows = waypoints.map((wp, idx) => `
            <tr>
                <td>${idx + 1}</td>
                <td>${wp.waypoint_name}</td>
                <td>${wp.simple_linear_time || 'N/A'}</td>
                <td>${wp.simple_linear_altitude_ft ? Math.round(wp.simple_linear_altitude_ft / 100) : 'N/A'}</td>
                <td>${wp.eet_backtrack_time || 'N/A'}</td>
                <td>${wp.eet_backtrack_altitude_ft ? Math.round(wp.eet_backtrack_altitude_ft / 100) : 'N/A'}</td>
                <td class="time-diff ${wp.time_difference_seconds > 60 ? 'high-diff' : ''}">${wp.time_difference_seconds || 0}초</td>
                <td class="alt-diff ${wp.altitude_difference_ft > 500 ? 'high-diff' : ''}">${wp.altitude_difference_ft || 0}ft</td>
            </tr>
        `).join('');

        return `
            <div class="comparison-table-wrapper">
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>지점</th>
                            <th colspan="2" class="method-a">Method A (단순 선형)</th>
                            <th colspan="2" class="method-b">Method B (EET 역계산)</th>
                            <th colspan="2">차이</th>
                        </tr>
                        <tr>
                            <th></th>
                            <th></th>
                            <th>시간</th>
                            <th>고도</th>
                            <th>시간</th>
                            <th>고도</th>
                            <th>시간</th>
                            <th>고도</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    }

    /**
     * 통계 HTML 생성
     */
    getStatisticsHTML(statistics) {
        if (!statistics) {
            return '<p class="no-data">통계 데이터가 없습니다.</p>';
        }

        return `
            <div class="statistics-grid">
                <div class="stat-card">
                    <div class="stat-title">지점 수</div>
                    <div class="stat-value">${statistics.total_waypoints || 0}</div>
                    <div class="stat-unit">waypoints</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">평균 시간 차이</div>
                    <div class="stat-value">${this.formatNumber(statistics.avg_time_diff_seconds || 0, 1)}</div>
                    <div class="stat-unit">초</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">최대 시간 차이</div>
                    <div class="stat-value">${statistics.max_time_diff_seconds || 0}</div>
                    <div class="stat-unit">초</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">평균 고도 차이</div>
                    <div class="stat-value">${this.formatNumber(statistics.avg_alt_diff_ft || 0, 0)}</div>
                    <div class="stat-unit">ft</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">최대 고도 차이</div>
                    <div class="stat-value">${statistics.max_alt_diff_ft || 0}</div>
                    <div class="stat-unit">ft</div>
                </div>
            </div>

            <div class="statistics-interpretation">
                <h4>해석</h4>
                <ul>
                    <li><strong>시간 차이:</strong> 두 계산 방식의 시간 차이입니다. 작을수록 일치도가 높습니다.</li>
                    <li><strong>고도 차이:</strong> 계산된 고도의 차이입니다. 상승 과정에서의 차이를 나타냅니다.</li>
                    <li><strong>평균 값:</strong> 모든 경유점에서의 평균 차이입니다.</li>
                    <li><strong>최대 값:</strong> 가장 큰 차이를 보이는 지점입니다.</li>
                </ul>
            </div>
        `;
    }

    /**
     * 고도 차트 그리기
     */
    drawAltitudeChart(waypoints) {
        const ctx = document.getElementById('altitudeChart');
        if (!ctx) return;

        // 기존 차트 제거
        if (this.charts.altitude) {
            this.charts.altitude.destroy();
        }

        // 데이터 준비
        const labels = waypoints.map(wp => wp.waypoint_name || '');
        const methodAData = waypoints.map(wp => (wp.simple_linear_altitude_ft || 0) / 100);
        const methodBData = waypoints.map(wp => (wp.eet_backtrack_altitude_ft || 0) / 100);

        // 차트 생성
        this.charts.altitude = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Method A (단순 선형)',
                        data: methodAData,
                        borderColor: '#FF6B6B',
                        backgroundColor: 'rgba(255, 107, 107, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 5,
                        pointBackgroundColor: '#FF6B6B'
                    },
                    {
                        label: 'Method B (EET 역계산)',
                        data: methodBData,
                        borderColor: '#4ECDC4',
                        backgroundColor: 'rgba(78, 205, 196, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 5,
                        pointBackgroundColor: '#4ECDC4'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: '경유점별 고도 비교'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: '고도 (Flight Level)'
                        },
                        beginAtZero: true
                    },
                    x: {
                        title: {
                            display: true,
                            text: '경유점'
                        }
                    }
                }
            }
        });
    }

    /**
     * 탭 리스너 설정
     */
    setupTabListeners() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabPanes = document.querySelectorAll('.tab-pane');

        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                // 활성 탭 제거
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabPanes.forEach(pane => pane.classList.remove('active'));

                // 새 탭 활성화
                e.target.classList.add('active');
                const tabId = e.target.dataset.tab;
                document.getElementById(tabId).classList.add('active');
            });
        });
    }

    /**
     * 모달 닫기
     */
    closeModal() {
        const modal = document.getElementById('climbComparisonModal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * 속도 출처 레이블
     */
    getSpeedSourceLabel(source) {
        const labels = {
            'csv': 'CSV 입력',
            'aircraft_profile': '기종 기본값',
            'default': '시스템 기본값'
        };
        return labels[source] || source || 'N/A';
    }

    /**
     * 숫자 포맷팅
     */
    formatNumber(value, decimals = 0) {
        return parseFloat(value).toFixed(decimals);
    }
}

// 글로벌 인스턴스 생성
let climbVisualizer;

document.addEventListener('DOMContentLoaded', () => {
    climbVisualizer = new ClimbComparisonVisualizer();
});
