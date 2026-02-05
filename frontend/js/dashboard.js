/**
 * 통계 대시보드 JavaScript
 * 유사호출 감시 시뮬레이션 시스템의 통계 및 분석 기능
 */

// 차트 객체 저장
let levelDistributionChart = null;
let overlapTimeChart = null;

// 대시보드 날짜 필터 상태
const dashboardState = {
    availableDates: [],      // 사용 가능한 모든 날짜
    dateIndex: -1,           // 현재 선택된 날짜 인덱스 (-1: 전체)
    selectedDate: null       // 선택된 날짜 (YYYY-MM-DD 형식)
};

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadAvailableDates();    // 먼저 사용 가능한 날짜 로드
    checkSystemHealth();
    loadLicenseInfo();       // 라이선스 정보 로드
});

/**
 * 이벤트 리스너 등록
 */
function initializeEventListeners() {
    const refreshBtn = document.getElementById('refresh-btn');
    const exportJsonBtn = document.getElementById('export-json-btn');
    const backBtn = document.getElementById('back-btn');
    const minOverlapFilter = document.getElementById('min-overlap-filter');
    const prevDateBtn = document.getElementById('dashboard-prev-date-btn');
    const nextDateBtn = document.getElementById('dashboard-next-date-btn');

    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDashboardData);
    }

    // 날짜 버튼 이벤트
    if (prevDateBtn) {
        prevDateBtn.addEventListener('click', () => {
            if (dashboardState.dateIndex > -1) {
                dashboardState.dateIndex--;
            }
            updateDashboardDateDisplay();
            loadDashboardData();
        });
    }

    if (nextDateBtn) {
        nextDateBtn.addEventListener('click', () => {
            if (dashboardState.dateIndex < dashboardState.availableDates.length - 1) {
                dashboardState.dateIndex++;
            }
            updateDashboardDateDisplay();
            loadDashboardData();
        });
    }

    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', downloadJSON);
    }

    if (backBtn) {
        backBtn.addEventListener('click', () => {
            window.location.href = 'index.html';
        });
    }

    if (minOverlapFilter) {
        minOverlapFilter.addEventListener('change', () => {
            loadRecentSimilarities();
        });
    }
}

/**
 * 시스템 상태 확인
 */
async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            updateSystemStatus('ok', `v${data.version}`);
        } else {
            updateSystemStatus('error', '연결 실패');
        }
    } catch (error) {
        updateSystemStatus('error', '오류 발생');
    }
}

/**
 * 라이선스 정보 로드 및 표시
 */
async function loadLicenseInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/license/info`);
        if (!response.ok) {
            console.warn('라이선스 정보를 불러올 수 없습니다');
            updateLicenseDisplay({
                type: 'unknown',
                is_valid: false,
                message: '라이선스 정보 불러오기 실패'
            });
            return;
        }

        const data = await response.json();
        if (data.status === 'success' && data.data) {
            updateLicenseDisplay(data.data);
        }
    } catch (error) {
        console.error('라이선스 정보 로드 오류:', error);
        updateLicenseDisplay({
            type: 'unknown',
            is_valid: false,
            message: '라이선스 정보 오류'
        });
    }
}

/**
 * 라이선스 정보 표시 업데이트
 */
function updateLicenseDisplay(licenseInfo) {
    const licenseTypeEl = document.getElementById('license-type-display');
    const licenseStatusEl = document.getElementById('license-status-display');
    const licenseInfoEl = document.getElementById('license-info');

    if (!licenseTypeEl || !licenseStatusEl) return;

    // 라이선스 타입 표시
    const typeText = licenseInfo.type === 'commercial' ? '상업용 라이선스' : '개발용 라이선스 (MIT)';
    const validity = licenseInfo.is_valid ? '✓ 유효함' : '✗ 무효함';

    licenseTypeEl.textContent = typeText;
    licenseTypeEl.style.fontWeight = 'bold';
    licenseTypeEl.style.color = licenseInfo.type === 'commercial' ? '#2e7d32' : '#1565c0';

    // 라이선스 상태 표시
    if (licenseInfo.expiry_date && licenseInfo.expiry_date !== 'N/A') {
        licenseStatusEl.textContent = `${validity} | 만료: ${licenseInfo.expiry_date}`;
    } else if (licenseInfo.message) {
        licenseStatusEl.textContent = licenseInfo.message;
    } else {
        licenseStatusEl.textContent = validity;
    }

    // 조직명이 있으면 표시
    if (licenseInfo.organization && licenseInfo.organization !== 'Unknown') {
        const orgEl = document.createElement('span');
        orgEl.style.display = 'block';
        orgEl.style.marginTop = '4px';
        orgEl.style.fontSize = '11px';
        orgEl.style.color = '#999';
        orgEl.textContent = `기관: ${licenseInfo.organization}`;
        licenseStatusEl.parentElement.appendChild(orgEl);
    }

    // 라이선스 배경색 변경
    if (licenseInfo.type === 'commercial') {
        licenseInfoEl.style.borderLeftColor = '#2e7d32';
        licenseInfoEl.style.background = '#e8f5e9';
    } else {
        licenseInfoEl.style.borderLeftColor = '#1565c0';
        licenseInfoEl.style.background = '#e3f2fd';
    }
}

/**
 * 사용 가능한 날짜 목록 로드
 */
async function loadAvailableDates() {
    try {
        const response = await fetch(`${API_BASE_URL}/flights/dates`);
        if (!response.ok) {
            console.error('사용 가능한 날짜를 불러올 수 없습니다');
            return;
        }

        const data = await response.json();
        if (data.status === 'success' && data.data && Array.isArray(data.data)) {
            dashboardState.availableDates = data.data.sort().reverse(); // 최신 날짜순으로 정렬

            // 오늘 날짜를 기본값으로 설정
            const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
            const todayIndex = dashboardState.availableDates.indexOf(today);
            dashboardState.dateIndex = todayIndex >= 0 ? todayIndex : 0; // 오늘 날짜가 있으면 선택, 없으면 최신 날짜

            updateDashboardDateDisplay();

            // 초기 데이터 로드
            loadDashboardData();
        }
    } catch (error) {
        console.error('사용 가능한 날짜 로드 오류:', error);
    }
}

/**
 * 대시보드 날짜 표시 업데이트
 */
function updateDashboardDateDisplay() {
    const dateDisplay = document.getElementById('dashboard-selected-date');
    const prevBtn = document.getElementById('dashboard-prev-date-btn');
    const nextBtn = document.getElementById('dashboard-next-date-btn');

    if (!dateDisplay) return;

    // 현재 선택된 날짜 설정
    if (dashboardState.dateIndex === -1) {
        dashboardState.selectedDate = null;
        dateDisplay.textContent = '전체 날짜';
    } else if (dashboardState.dateIndex >= 0 && dashboardState.dateIndex < dashboardState.availableDates.length) {
        dashboardState.selectedDate = dashboardState.availableDates[dashboardState.dateIndex];
        dateDisplay.textContent = dashboardState.selectedDate;
    }

    // 버튼 활성화/비활성화
    if (prevBtn) {
        prevBtn.disabled = dashboardState.dateIndex === -1;
    }
    if (nextBtn) {
        nextBtn.disabled = dashboardState.dateIndex === dashboardState.availableDates.length - 1;
    }
}

/**
 * 시스템 상태 업데이트
 */
function updateSystemStatus(status, message) {
    const statusDiv = document.getElementById('system-status');
    if (statusDiv) {
        const indicator = statusDiv.querySelector('.status-indicator');
        const text = statusDiv.querySelector('.status-text');

        if (status === 'ok') {
            indicator.style.background = '#27ae60';
            text.textContent = `✓ 정상 | ${message}`;
        } else {
            indicator.style.background = '#e74c3c';
            text.textContent = `✗ ${message}`;
        }
    }
}

/**
 * 메시지 표시
 */
function showMessage(message, type = 'info') {
    const container = document.getElementById('message-container');
    if (!container) return;

    const div = document.createElement('div');
    const className = type === 'error' ? 'error-message' :
        type === 'success' ? 'success-message' :
            'info-message';

    div.className = className;
    div.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'}"></i> ${message}`;

    container.appendChild(div);

    // 5초 후 자동 제거
    setTimeout(() => {
        div.remove();
    }, 5000);
}

/**
 * 대시보드 데이터 로드
 */
async function loadDashboardData() {
    try {
        // 선택된 날짜에 따라 다른 엔드포인트 호출
        let url = `${API_BASE_URL}/statistics/summary`;
        console.log('📊 Dashboard State:', {
            dateIndex: dashboardState.dateIndex,
            availableDates: dashboardState.availableDates,
            selectedDate: dashboardState.selectedDate
        });

        if (dashboardState.dateIndex >= 0 && dashboardState.availableDates[dashboardState.dateIndex]) {
            const selectedDate = dashboardState.availableDates[dashboardState.dateIndex];
            url = `${API_BASE_URL}/statistics/detailed?eobd=${selectedDate}`;
        }

        console.log('🔗 API URL:', url);

        // 통계 데이터 로드
        const statsResponse = await fetch(url);
        if (!statsResponse.ok) {
            showMessage('통계를 불러올 수 없습니다', 'error');
            return;
        }

        const statsData = await statsResponse.json();
        console.log('📥 API Response:', {
            total_flights: statsData.data.total_flights,
            total_similarities: statsData.data.total_similarities,
            filtered_similarities: statsData.data.filtered_similarities
        });
        updateStatisticsCards(statsData.data);

        // 차트 업데이트
        updateLevelDistributionChart(statsData.data);
        updateOverlapTimeChart(statsData.data);

        // 섹터 통계 업데이트
        updateSectorStatistics(statsData.data);

        // 최근 유사호출 로드
        await loadRecentSimilarities();

        showMessage('데이터를 성공적으로 로드했습니다', 'success');

    } catch (error) {
        console.error('데이터 로드 오류:', error);
        showMessage('데이터 로드 중 오류가 발생했습니다', 'error');
    }
}

/**
 * 통계 카드 업데이트
 */
function updateStatisticsCards(data) {
    // 분석된 항공편
    const totalFlights = document.getElementById('total-flights');
    if (totalFlights) {
        totalFlights.textContent = data.total_flights.toLocaleString();
    }

    // 검출된 유사호출 (총 유사호출 쌍)
    const totalSimilarities = document.getElementById('total-similarities');
    if (totalSimilarities) {
        totalSimilarities.textContent = data.total_similarities.toLocaleString();
    }

    // 중복 겹침 쌍 (2개 이상 섹터에서 겹친 경우) + 겹침률
    const crossSectorOverlaps = document.getElementById('cross-sector-overlaps');
    const crossSectorRatio = document.getElementById('cross-sector-ratio');
    if (crossSectorOverlaps && data.cross_sector_overlap_pairs !== undefined) {
        crossSectorOverlaps.textContent = data.cross_sector_overlap_pairs.toLocaleString();

        // 겹침률 계산 (2개 이상 섹터 겹침 / 섹터 겹침이 있는 전체 유사호출)
        if (crossSectorRatio && data.similarities_with_overlap > 0) {
            const ratio = ((data.cross_sector_overlap_pairs / data.similarities_with_overlap) * 100).toFixed(1);
            crossSectorRatio.textContent = `쌍 (${ratio}%)`;
        } else {
            crossSectorRatio.textContent = '쌍';
        }
    }
}

/**
 * 유사도 레벨 분포 차트 업데이트
 */
function updateLevelDistributionChart(data) {
    const canvas = document.getElementById('level-distribution-chart');
    const loading = document.getElementById('level-loading');

    if (!canvas || !data.level_distribution) return;

    // 로딩 상태 숨기기
    if (loading) loading.style.display = 'none';

    // 레벨과 정의를 포함한 라벨 생성
    const levelKeys = Object.keys(data.level_distribution);
    const values = Object.values(data.level_distribution);
    const labels = levelKeys.map(level => {
        // 전역 appState에서 유사도 레벨 정의 조회
        if (typeof appState !== 'undefined' && appState.similarityLevels && appState.similarityLevels[level]) {
            const description = appState.similarityLevels[level].description;
            return `${level}\n(${description})`;
        }
        return level;
    });

    // 기존 차트 제거
    if (levelDistributionChart) {
        levelDistributionChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    levelDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#667eea',
                    '#764ba2',
                    '#f093fb',
                    '#4facfe',
                    '#00f2fe',
                    '#43e97b',
                    '#fa709a',
                    '#fee140'
                ],
                borderColor: 'white',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: { size: 11 },
                        padding: 10
                    }
                }
            }
        }
    });
}

/**
 * 공존시간 분포 차트 업데이트
 */
function updateOverlapTimeChart(data) {
    const canvas = document.getElementById('overlap-time-chart');
    const loading = document.getElementById('overlap-loading');

    if (!canvas || !data.overlap_time_distribution) return;

    // 로딩 상태 숨기기
    if (loading) loading.style.display = 'none';

    const labels = Object.keys(data.overlap_time_distribution);
    const values = Object.values(data.overlap_time_distribution);

    // 기존 차트 제거
    if (overlapTimeChart) {
        overlapTimeChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    overlapTimeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '겹침 쌍의 수',
                data: values,
                backgroundColor: labels.map((_, index) =>
                    appState.selectedTimeFilter && appState.selectedTimeFilter === labels[index]
                        ? '#764ba2'
                        : '#667eea'
                ),
                borderColor: '#764ba2',
                borderWidth: 2,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: { size: 11 }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: { size: 10 }
                    }
                },
                x: {
                    ticks: {
                        font: { size: 10 }
                    }
                }
            },
            onClick: (event, activeElements) => {
                if (activeElements && activeElements.length > 0) {
                    const index = activeElements[0].index;
                    const selectedLabel = labels[index];

                    if (appState.selectedTimeFilter === selectedLabel) {
                        // 같은 시간대를 다시 클릭하면 필터 해제
                        appState.selectedTimeFilter = null;
                        handleClearTimeFilter();
                    } else {
                        // 새로운 시간대 선택
                        appState.selectedTimeFilter = selectedLabel;
                        handleTimeFilterChange(selectedLabel);
                    }
                }
            }
        }
    });
}

/**
 * 섹터 통계 업데이트
 */
function updateSectorStatistics(data) {
    const tbody = document.getElementById('sector-tbody');
    if (!tbody || !data.sector_statistics) return;

    // 총 겹침 횟수 계산
    const totalOverlaps = data.sector_statistics.reduce((sum, s) => sum + (s.count || 0), 0) || 1;

    tbody.innerHTML = '';

    if (data.sector_statistics.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #999;">데이터가 없습니다</td></tr>';
        return;
    }

    data.sector_statistics.forEach(sector => {
        const percentage = ((sector.count / totalOverlaps) * 100).toFixed(1);
        const barWidth = percentage;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${sector.sector_name}</strong></td>
            <td style="text-align: center;">${sector.count}</td>
            <td style="text-align: center;">${parseFloat(sector.avg_minutes).toFixed(1)}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 60px; height: 16px; background: #eee; border-radius: 3px; overflow: hidden;">
                        <div style="width: ${barWidth}%; height: 100%; background: linear-gradient(90deg, #667eea, #764ba2);">
                        </div>
                    </div>
                    <span style="font-size: 11px; min-width: 35px;">${percentage}%</span>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

/**
 * 최근 유사호출 로드
 */
async function loadRecentSimilarities(page = 1) {
    try {
        const minOverlap = document.getElementById('min-overlap-filter')?.value || '2';

        // API URL 구성 (날짜 필터 포함)
        let url = `${API_BASE_URL}/statistics/detailed?min_overlap_minutes=${minOverlap}&page=${page}&limit=20`;

        // 특정 날짜가 선택된 경우 eobd 파라미터 추가
        if (dashboardState.selectedDate) {
            url += `&eobd=${dashboardState.selectedDate}`;
        }

        const response = await fetch(url);

        if (!response.ok) {
            console.error('최근 유사호출을 불러올 수 없습니다');
            return;
        }

        const data = await response.json();
        updateRecentSimilaritiesTable(data.data.recent_similarities);

        // 페이지네이션 정보 업데이트
        if (data.data.pagination) {
            updateRecentSimilaritiesPagination(data.data.pagination);
        }

    } catch (error) {
        console.error('최근 유사호출 로드 오류:', error);
    }
}

/**
 * 최근 유사호출 테이블 업데이트
 */
function updateRecentSimilaritiesTable(similarities) {
    const tbody = document.getElementById('table-body');  // HTML에서 사용하는 실제 ID
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!similarities || similarities.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #999;">데이터가 없습니다</td></tr>';
        return;
    }

    similarities.forEach(sim => {
        const levelBadge = getLevelBadge(sim.similarity_level);
        const statusBadge = sim.has_sector_overlap ?
            '<span class="badge badge-danger">겹침</span>' :
            '<span class="badge badge-success">정상</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${sim.callsign1}</strong></td>
            <td><strong>${sim.callsign2}</strong></td>
            <td>${levelBadge}</td>
            <td>${sim.total_overlap_minutes}</td>
            <td>${statusBadge}</td>
        `;
        tbody.appendChild(tr);
    });
}

/**
 * 최근 유사호출 페이지네이션 업데이트
 */
function updateRecentSimilaritiesPagination(pagination) {
    // 페이지네이션 컨트롤 요소 찾기 또는 생성
    let paginationContainer = document.getElementById('recent-table-pagination');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'recent-table-pagination';
        paginationContainer.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 4px;';

        // 테이블 다음에 추가
        const recentTable = document.getElementById('recent-table');
        if (recentTable && recentTable.parentNode) {
            recentTable.parentNode.insertBefore(paginationContainer, recentTable.nextSibling);
        }
    }

    const currentPage = pagination.current_page || 1;
    const totalPages = pagination.total_pages || 1;
    const totalCount = pagination.total_count || 0;

    paginationContainer.innerHTML = `
        <button onclick="loadRecentSimilarities(${Math.max(1, currentPage - 1)})" ${currentPage === 1 ? 'disabled' : ''} class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;">
            <i class="fas fa-chevron-left"></i> 이전
        </button>
        <span style="font-size: 13px; font-weight: bold; margin: 0 10px;">
            페이지 ${currentPage} / ${totalPages}
        </span>
        <button onclick="loadRecentSimilarities(${Math.min(totalPages, currentPage + 1)})" ${currentPage === totalPages ? 'disabled' : ''} class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;">
            다음 <i class="fas fa-chevron-right"></i>
        </button>
        <span style="font-size: 12px; color: #666; margin-left: 10px;">
            (총 ${totalCount}건)
        </span>
    `;
}

/**
 * 유사도 레벨별 배지 생성
 */
function getLevelBadge(level) {
    if (!level) return '';

    // LEVEL_5: 고위험 (Red)
    if (level.startsWith('LEVEL_5')) {
        return `<span class="badge badge-danger">${level}</span>`;
    }
    // LEVEL_4: 중위험 (Yellow/Orange)
    if (level.startsWith('LEVEL_4')) {
        return `<span class="badge badge-warning">${level}</span>`;
    }
    // LEVEL_3: 저위험 (Green)
    if (level.startsWith('LEVEL_3')) {
        return `<span class="badge badge-success">${level}</span>`;
    }

    return `<span class="badge badge-secondary">${level}</span>`;
}

/**
 * JSON 데이터 다운로드
 */
async function downloadJSON() {
    try {
        const minOverlap = document.getElementById('min-overlap-filter')?.value || '2';
        const response = await fetch(
            `${API_BASE_URL}/export/json?min_overlap_minutes=${minOverlap}`
        );

        if (!response.ok) {
            showMessage('데이터를 다운로드할 수 없습니다', 'error');
            return;
        }

        const data = await response.json();

        // Blob 생성
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });

        // 다운로드
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `similarity-report-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showMessage('데이터를 성공적으로 다운로드했습니다', 'success');

    } catch (error) {
        console.error('다운로드 오류:', error);
        showMessage('다운로드 중 오류가 발생했습니다', 'error');
    }
}
