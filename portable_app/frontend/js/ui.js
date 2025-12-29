/**
 * UI 이벤트 처리 - 사용자 인터랙션 관리
 */

// 글로벌 상태
const appState = {
    currentFile: null,
    simulationResults: null,
    pagination: {
        page: 1,
        totalPages: 1
    },
    filters: {
        risk_levels: ['HIGH', 'MEDIUM'],
        min_coexist: 0,
        max_coexist: 120,
        min_overlap: 2
    },
    selectedDate: null,  // 일자별 필터링 (대시보드)
    availableDates: [],  // 사용 가능한 날짜 목록
    dateIndex: -1,       // 현재 선택된 날짜 인덱스
    // 전체 항공편 필터
    allFlightsSelectedDate: null,  // 전체 항공편 탭의 선택된 날짜
    allFlightsDateIndex: 0,        // 전체 항공편 탭의 날짜 인덱스
    allFlightsAvailableDates: [],  // 전체 항공편 탭의 사용 가능한 날짜
    // 유사도 레벨 정의
    similarityLevels: {},  // 유사도 레벨 및 설명 매핑
    // 시간대 필터
    selectedTimeFilter: null  // 선택된 시간대 필터 (차트 클릭)
};

/**
 * DOM 요소 캐시
 */
const DOM = {
    fileInput: null,
    uploadBtn: null,
    uploadStatus: null,
    simulateBtn: null,
    simulationStatus: null,
    exportJsonBtn: null,
    exportCsvBtn: null,
    searchInput: null,
    dateFilter: null,
    clearDateFilterBtn: null,
    selectedDatePicker: null,
    viewResultsBtn: null,
    resultsTable: null,
    tableBody: null,
    resultCount: null,
    // 페이지네이션 버튼
    prevPageBtn: null,
    nextPageBtn: null,
    pageInfo: null,
    // 전체 항공편 필터
    allFlightsDatePicker: null,
    allFlightsViewBtn: null,
    allFlightsClearFilterBtn: null,
    // 통계 카드
    statTotalSims: null,
    statFilteredSims: null,
    statTotalFlights: null,
    // 시간대 필터
    timeFilterIndicator: null,
    timeFilterValue: null,
    clearTimeFilterBtn: null,
    // 시스템 상태
    systemStatus: null,
    footerStatus: null
};

/**
 * DOM 요소 초기화
 */
function initializeDOM() {
    DOM.fileInput = document.getElementById('file-input');
    DOM.uploadBtn = document.getElementById('upload-btn');
    DOM.uploadStatus = document.getElementById('upload-status');
    DOM.simulateBtn = document.getElementById('simulate-btn');
    DOM.simulationStatus = document.getElementById('simulation-status');
    DOM.exportJsonBtn = document.getElementById('export-json-btn');
    DOM.exportCsvBtn = document.getElementById('export-csv-btn');
    DOM.searchInput = document.getElementById('search-input');
    DOM.dateFilter = document.getElementById('date-filter');
    DOM.clearDateFilterBtn = document.getElementById('clear-date-filter-btn');
    DOM.selectedDatePicker = document.getElementById('selected-date-picker');
    DOM.viewResultsBtn = document.getElementById('view-results-btn');
    DOM.resultsTable = document.getElementById('results-table');
    DOM.tableBody = document.getElementById('table-body');
    DOM.resultCount = document.getElementById('result-count');

    // 페이지네이션 요소
    DOM.prevPageBtn = document.getElementById('prev-page-btn');
    DOM.nextPageBtn = document.getElementById('next-page-btn');
    DOM.pageInfo = document.getElementById('page-info');

    // 통계 카드 IDs
    DOM.statTotalSims = document.getElementById('stat-total-sims');
    DOM.statFilteredSims = document.getElementById('stat-filtered-sims');
    DOM.statTotalFlights = document.getElementById('stat-total-flights');

    // 전체 항공편 필터 요소
    DOM.allFlightsDatePicker = document.getElementById('all-flights-date-picker');
    DOM.allFlightsViewBtn = document.getElementById('all-flights-view-btn');
    DOM.allFlightsClearFilterBtn = document.getElementById('all-flights-clear-filter-btn');

    // 시간대 필터 요소
    DOM.timeFilterIndicator = document.getElementById('time-filter-indicator');
    DOM.timeFilterValue = document.getElementById('time-filter-value');
    DOM.clearTimeFilterBtn = document.getElementById('clear-time-filter-btn');

    DOM.systemStatus = document.getElementById('system-status');
    DOM.footerStatus = document.getElementById('footer-status');
}

/**
 * 페이지 로드 시 기존 데이터 조회
 */
async function loadExistingData(page = 1, selectedDate = null) {
    try {
        // selectedDate가 제공되지 않으면 appState의 selectedDate 사용
        if (selectedDate === null) {
            selectedDate = appState.selectedDate;
        }

        console.log('기존 데이터 조회 중...', { page, selectedDate });

        // 상세 통계 조회 (리스트 포함)
        const statsResponse = await api.getStatisticsDetailed(2, page, 20, selectedDate);

        if (statsResponse && statsResponse.status === 'success') {
            const data = statsResponse.data;
            const recentSimilarities = data.recent_similarities || [];

            // 1. 통계 카드 업데이트
            updateStatisticsUI(data);

            // 차트 업데이트
            if (typeof updateCharts === 'function') {
                updateCharts(data);
            }

            // 페이지네이션 정보 업데이트
            if (data.pagination) {
                appState.pagination.totalPages = data.pagination.total_pages;
                appState.pagination.page = data.pagination.current_page;
                updatePaginationUI();
            }

            // 2. 테이블 데이터 업데이트
            // 시뮬레이션 결과와 호환되는 구조로 변환
            const coexistences = recentSimilarities.map(sim => ({
                id: sim.id,
                callsign1: sim.callsign1,
                callsign2: sim.callsign2,
                similarity_level: sim.similarity_level,
                risk_level: 'UNKNOWN',
                // 백엔드에서 이제 sector_overlaps를 제공함
                sector_overlaps: sim.sector_overlaps || [],
                // 원본 데이터가 가진 추가 필드 보존
                ...sim
            }));

            // 데이터 개수 보정: total_similarities를 전체 결과 개수로 재계산
            // (백엔드에서 필터링이 제대로 안 될 때 프론트엔드에서 보정)
            if (data.pagination && data.pagination.total_count !== undefined) {
                // 페이지네이션이 있으면 전체 개수 사용
                data.total_similarities = data.pagination.total_count;
            } else if (coexistences.length > 0) {
                // 페이지네이션이 없으면 현재 개수 사용
                data.total_similarities = coexistences.length;
            }

            // 테이블 결과 표시
            displayTableResults(coexistences);

            // 시뮬레이션 실행 버튼 활성화 (이미 데이터가 있으므로 시뮬레이션 가능)
            DOM.simulateBtn.disabled = false;

            // 데이터가 있으면 내보내기 활성화
            if (recentSimilarities.length > 0) {
                DOM.exportJsonBtn.disabled = false;
                DOM.exportCsvBtn.disabled = false;
            }

            // appState에 데이터 저장 (시간대 필터링을 위해 필수)
            appState.simulationResults = {
                coexistences: coexistences,
                statistics: data
            };

            console.log('기존 데이터 로드 완료:', coexistences.length, '개');
        } else {
            // API 응답 실패 또는 데이터 없음
            console.log('데이터 조회 응답 실패 또는 데이터 없음:', statsResponse);
            DOM.tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">데이터가 없습니다. 시뮬레이션을 실행하거나 파일을 업로드하세요.</td></tr>';
        }
    } catch (error) {
        console.error('기존 데이터 조회 중 오류:', error);
        DOM.tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">데이터를 불러올 수 없습니다.</td></tr>';
    }
}

function updatePaginationUI() {
    if (DOM.prevPageBtn && DOM.nextPageBtn && DOM.pageInfo) {
        DOM.pageInfo.textContent = `${appState.pagination.page} / ${appState.pagination.totalPages || 1}`;
        DOM.prevPageBtn.disabled = appState.pagination.page <= 1;
        DOM.nextPageBtn.disabled = appState.pagination.page >= (appState.pagination.totalPages || 1);
    }
}

async function handlePageChange(direction) {
    let newPage = appState.pagination.page + direction;
    if (newPage < 1) newPage = 1;
    if (newPage > appState.pagination.totalPages) newPage = appState.pagination.totalPages;

    if (newPage !== appState.pagination.page) {
        await loadExistingData(newPage);
    }
}

/**
 * 이벤트 리스너 등록
 */
function attachEventListeners() {
    // 파일 입력 변경
    if (DOM.fileInput) {
        DOM.fileInput.addEventListener('change', handleFileSelection);
    }

    // 드래그 앤 드롭
    const fileLabel = document.querySelector('.file-label');
    if (fileLabel) {
        fileLabel.addEventListener('dragover', handleDragOver);
        fileLabel.addEventListener('dragleave', handleDragLeave);
        fileLabel.addEventListener('drop', handleDrop);
    }

    // 업로드 버튼
    if (DOM.uploadBtn) {
        DOM.uploadBtn.addEventListener('click', handleUpload);
    }

    // 시뮬레이션 버튼
    if (DOM.simulateBtn) {
        DOM.simulateBtn.addEventListener('click', handleSimulate);
    }

    // 결과 조회 버튼 (새로 추가)
    const viewResultsBtn = document.getElementById('view-results-btn');
    if (viewResultsBtn) {
        viewResultsBtn.addEventListener('click', handleViewResults);
    }

    // 내보내기 버튼
    if (DOM.exportJsonBtn) {
        DOM.exportJsonBtn.addEventListener('click', handleExportJSON);
    }
    if (DOM.exportCsvBtn) {
        DOM.exportCsvBtn.addEventListener('click', handleExportCSV);
    }

    // 검색 입력
    if (DOM.searchInput) {
        DOM.searchInput.addEventListener('input', handleSearch);
    }

    // 날짜 필터
    if (DOM.dateFilter) {
        DOM.dateFilter.addEventListener('change', handleDateFilterChange);
    }

    // 날짜 필터 해제 버튼
    if (DOM.clearDateFilterBtn) {
        DOM.clearDateFilterBtn.addEventListener('click', handleClearDateFilter);
    }

    // 날짜 선택 (달력)
    if (DOM.selectedDatePicker) {
        DOM.selectedDatePicker.addEventListener('change', handleDatePickerChange);
    }

    // 페이지네이션 버튼
    if (DOM.prevPageBtn) {
        DOM.prevPageBtn.addEventListener('click', () => handlePageChange(-1));
    }
    if (DOM.nextPageBtn) {
        DOM.nextPageBtn.addEventListener('click', () => handlePageChange(1));
    }

    // 단순 결과 조회 버튼
    if (DOM.viewResultsBtn) {
        DOM.viewResultsBtn.addEventListener('click', handleViewResultsByDate);
    }

    // 전체 항공편 필터 (달력)
    if (DOM.allFlightsDatePicker) {
        DOM.allFlightsDatePicker.addEventListener('change', handleAllFlightsDatePickerChange);
    }
    if (DOM.allFlightsViewBtn) {
        DOM.allFlightsViewBtn.addEventListener('click', handleAllFlightsViewByDate);
    }
    if (DOM.allFlightsClearFilterBtn) {
        DOM.allFlightsClearFilterBtn.addEventListener('click', handleAllFlightsClearFilter);
    }

    // 시간대 필터 클리어 버튼
    if (DOM.clearTimeFilterBtn) {
        DOM.clearTimeFilterBtn.addEventListener('click', () => {
            appState.selectedTimeFilter = null;
            handleClearTimeFilter();
        });
    }

    // 일자별 DB 초기화
    handleDeleteTypeChange();  // 라디오 버튼 변경 리스너 설정
    const deleteDbBtn = document.getElementById('delete-db-btn');
    if (deleteDbBtn) {
        deleteDbBtn.addEventListener('click', handleDeleteDatabase);
    }

    // 탭 네비게이션
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // 탭 스타일 활성화
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // 뷰 전환
            const targetId = tab.dataset.target;
            document.querySelectorAll('.view-section').forEach(view => {
                view.classList.remove('active');
                view.style.display = 'none';
            });
            const targetView = document.getElementById(targetId);
            targetView.classList.add('active');

            // 뷰별 display 설정 (flex나 block 등 CSS 클래스에 따름)
            if (targetId === 'dashboard-view') {
                targetView.style.display = 'block'; // Or flex, depending on layout
                // CSS class 'view-section.active' sets some styles, but inline style might override. 
                // Let the CSS handle it by removing inline none.
                targetView.style.removeProperty('display');
            } else if (targetId === 'all-flights-view') {
                targetView.style.removeProperty('display');
                // 전체 항공편 데이터 로드 (첫 1회 또는 매번)
                loadAllFlights();
            }
        });
    });

    // 전체 엑셀 다운로드 버튼
    const exportExcelBtn = document.getElementById('export-all-excel-btn');
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', () => {
            window.location.href = `${API_BASE_URL}/export/flights/excel`;
        });
    }

    // 파일 선택
    if (DOM.fileInput) {
        DOM.fileInput.addEventListener('change', handleFileSelection);
    }

    // 드래그 앤 드롭
    const dropZone = document.getElementById('drop-zone');
    if (dropZone) {
        // ... existing drag handlers

        // 모달 닫기 버튼
        const detailModal = document.getElementById('detail-modal');
        const closeModalSpan = document.querySelector('.close-modal');

        if (closeModalSpan) {
            closeModalSpan.addEventListener('click', () => {
                if (detailModal) detailModal.style.display = 'none';
            });
        }

        // 모달 외부 클릭 시 닫기
        window.addEventListener('click', (event) => {
            if (event.target === detailModal) {
                detailModal.style.display = 'none';
            }
        });

    }

    // 페이지네이션 버튼
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');

    if (prevBtn) {
        prevBtn.addEventListener('click', () => handlePageChange(-1));
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', () => handlePageChange(1));
    }
}

/**
 * 파일 선택 처리
 */
function handleFileSelection(event) {
    const file = event.target.files[0];
    if (file) {
        appState.currentFile = file;
        DOM.uploadBtn.disabled = false;
        showMessage(DOM.uploadStatus, `선택됨: ${file.name}`, 'info');
    }
}

/**
 * 드래그 오버 처리
 */
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.style.borderColor = '#3498db';
    event.currentTarget.style.backgroundColor = '#f0f4f8';
}

/**
 * 드래그 리브 처리
 */
function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.style.borderColor = '#ecf0f1';
    event.currentTarget.style.backgroundColor = '#fafbfc';
}

/**
 * 드롭 처리
 */
function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.style.borderColor = '#ecf0f1';
    event.currentTarget.style.backgroundColor = '#fafbfc';

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        DOM.fileInput.files = files;
        handleFileSelection({ target: { files } });
    }
}

/**
 * 파일 업로드 처리
 */
async function handleUpload() {
    if (!appState.currentFile) {
        showMessage(DOM.uploadStatus, '파일을 선택하세요', 'error');
        return;
    }

    // 선택된 모드 확인
    const mode = document.querySelector('input[name="upload-mode"]:checked').value;

    try {
        DOM.uploadBtn.disabled = true;

        // 진행 상태바 컨테이너 표시
        const progressContainer = document.getElementById('upload-progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }

        showMessage(DOM.uploadStatus, `파일 업로드 중... (${mode === 'replace' ? '덮어쓰기' : '누적'})`, 'loading');

        const startTime = Date.now();
        const result = await api.uploadFile(appState.currentFile, mode);

        // 업로드 응답 후 진행 상황 모니터링
        if (result.status === 'success' && result.data && result.data.process_id) {
            // 백그라운드 처리 시작 - 진행 상황 모니터링 시작
            showMessage(DOM.uploadStatus, '파일 처리 중... (백그라운드)', 'loading');
            await monitorUploadProgress(result.data.process_id, startTime);
            DOM.simulateBtn.disabled = false;
        } else if (result.status === 'success') {
            const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
            showMessage(
                DOM.uploadStatus,
                `${result.data.record_count}개 항공편 로드 완료 (${elapsedTime}초)`,
                'success'
            );
            DOM.simulateBtn.disabled = false;
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        } else {
            showMessage(DOM.uploadStatus, result.message || '업로드 실패', 'error');
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        }
    } catch (error) {
        showMessage(DOM.uploadStatus, '업로드 중 오류 발생', 'error');
        console.error(error);
        const progressContainer = document.getElementById('upload-progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    } finally {
        DOM.uploadBtn.disabled = false;
    }
}

/**
 * 최소 공존시간 변경 처리
 */
async function handleMinOverlapChange() {
    // 페이지 리셋 후 데이터 로드
    await loadExistingData(1);
}

/**
 * 결과 조회 (시뮬레이션 없이)
 */
async function handleViewResults() {
    await loadExistingData(1);
    showMessage(DOM.simulationStatus, '최신 결과를 조회했습니다.', 'success');
}

/**
 * 날짜별 결과 조회
 */
async function handleViewResultsByDate() {
    if (appState.dateIndex === -1 || appState.availableDates.length === 0) {
        showMessage(DOM.simulationStatus, '조회할 날짜를 선택하세요.', 'warning');
        return;
    }

    const selectedDate = appState.availableDates[appState.dateIndex];
    appState.selectedDate = selectedDate;
    appState.pagination.page = 1;

    await loadExistingData(1, selectedDate);
    showMessage(DOM.simulationStatus, `${selectedDate} 결과를 조회했습니다.`, 'success');
}

/**
 * 이전 날짜로 이동
 */
function handlePrevDate() {
    if (appState.availableDates.length === 0) {
        showMessage(DOM.simulationStatus, '사용 가능한 날짜가 없습니다.', 'warning');
        return;
    }

    if (appState.dateIndex > 0) {
        appState.dateIndex--;
    } else {
        appState.dateIndex = appState.availableDates.length - 1;
    }

    updateDateDisplay();
    loadExistingData(1);  // 새 날짜로 데이터 재로드
}

/**
 * 날짜 선택 변경 (달력)
 */
function handleDatePickerChange(event) {
    const selectedDate = event.target.value;
    if (selectedDate) {
        appState.selectedDate = selectedDate;
        loadExistingData(1, selectedDate);  // 선택된 날짜로 데이터 로드
    }
}

/**
 * 날짜 표시 업데이트
 */
function updateDateDisplay() {
    // 달력에 선택된 날짜 표시
    if (DOM.selectedDatePicker && appState.selectedDate) {
        DOM.selectedDatePicker.value = appState.selectedDate;
    }
}

/**
 * 사용 가능한 날짜 목록 로드
 */
async function loadAvailableDates() {
    try {
        // API에서 사용 가능한 날짜 동적으로 가져오기
        const response = await api.getAvailableDates();
        if (response && response.status === 'success' && response.data) {
            appState.availableDates = response.data.sort();  // 날짜순 정렬

            // 기본값으로 첫번째 날짜 선택
            if (appState.availableDates.length > 0) {
                appState.dateIndex = 0;
                appState.selectedDate = appState.availableDates[0];

                // Date picker 설정
                if (DOM.selectedDatePicker) {
                    DOM.selectedDatePicker.value = appState.selectedDate;
                    DOM.selectedDatePicker.min = appState.availableDates[0];
                    DOM.selectedDatePicker.max = appState.availableDates[appState.availableDates.length - 1];
                }
            }

            updateDateDisplay();
        }
    } catch (error) {
        console.error('사용 가능한 날짜 로드 실패:', error);
    }
}

/**
 * 유사도 레벨 정의 로드
 */
async function loadSimilarityLevels() {
    try {
        const response = await api.getSimilarityLevels();
        if (response && response.status === 'success' && response.data) {
            appState.similarityLevels = response.data;
            console.log('유사도 레벨 정의 로드 완료:', appState.similarityLevels);
        }
    } catch (error) {
        console.error('유사도 레벨 정의 로드 실패:', error);
        appState.similarityLevels = {};
    }
}

/**
 * 업로드 진행 상황 모니터링
 */
async function monitorUploadProgress(processId, startTime) {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const maxAttempts = 300; // 최대 30초 (100ms × 300)

        const pollProgress = async () => {
            attempts++;

            if (attempts > maxAttempts) {
                reject(new Error('진행 상황 모니터링 타임아웃'));
                return;
            }

            try {
                const progress = await getUploadProgress(processId);

                if (!progress || !progress.percent) {
                    // 아직 진행 정보가 없는 경우
                    setTimeout(pollProgress, 100);
                    return;
                }

                // 진행 상태바 업데이트
                const progressBar = document.getElementById('progress-bar');
                const progressPercent = document.getElementById('progress-percent');
                const progressStage = document.getElementById('progress-stage');

                if (progressBar) {
                    progressBar.style.width = progress.percent + '%';
                }
                if (progressPercent) {
                    progressPercent.textContent = progress.percent + '%';
                }
                if (progressStage) {
                    progressStage.textContent = progress.stage || '처리 중...';
                }

                // 완료 또는 에러 확인
                if (progress.percent >= 100 || progress.status === 'completed') {
                    const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
                    showMessage(
                        DOM.uploadStatus,
                        `${progress.total}개 항공편 로드 완료 (${elapsedTime}초)`,
                        'success'
                    );
                    resolve(progress);
                } else if (progress.status === 'error') {
                    showMessage(DOM.uploadStatus, progress.stage || '업로드 오류 발생', 'error');
                    reject(new Error(progress.stage));
                } else {
                    // 계속 폴링
                    setTimeout(pollProgress, 200);
                }
            } catch (error) {
                // API 호출 실패 (업로드가 완료되었을 수 있음)
                if (attempts > 50) {
                    // 충분히 기다렸으면 완료로 간주
                    const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
                    showMessage(
                        DOM.uploadStatus,
                        `업로드 완료 (${elapsedTime}초)`,
                        'success'
                    );
                    resolve({});
                } else {
                    setTimeout(pollProgress, 200);
                }
            }
        };

        // 첫 번째 폴링 시작
        setTimeout(pollProgress, 500);
    });
}

/**
 * 시뮬레이션 실행 처리
 */
/**
 * 유사호출 시뮬레이션 실행
 */
async function runSimulation(filters = {}, minOverlapMinutes = 2) {
    return api.runSimulation(filters, minOverlapMinutes);
}

/**
 * 통계 UI 업데이트 (updateStatisticsUI의 별칭)
 */
function updateStatistics(data) {
    return updateStatisticsUI(data);
}

async function handleSimulate() {
    try {
        DOM.simulateBtn.disabled = true;
        showMessage(DOM.simulationStatus, '유사호출 분석 중...', 'loading');

        // 프로그레스 바 표시
        const progressContainer = document.getElementById('simulation-progress-container');
        const progressBar = document.getElementById('simulation-progress-bar');
        const progressText = document.getElementById('simulation-progress-text');
        const progressPercent = document.getElementById('simulation-progress-percent');

        if (progressContainer) {
            progressContainer.style.display = 'block';
            progressBar.style.width = '10%';
            progressText.textContent = '10%';
            progressPercent.textContent = '10%';
        }

        // 시뮬레이션 요청 시작
        const startTime = Date.now();
        const minOverlapInput = document.getElementById('min-overlap-input');
        const minOverlapMinutes = minOverlapInput ? parseInt(minOverlapInput.value) || 2 : 2;

        // 프로그레스 바 천천히 진행 (시뮬레이션 진행 중)
        let currentProgress = 10;
        const progressInterval = setInterval(() => {
            if (currentProgress < 90) {
                currentProgress += Math.random() * 30;
                if (currentProgress > 90) currentProgress = 90;
                progressBar.style.width = currentProgress + '%';
                progressText.textContent = Math.floor(currentProgress) + '%';
                progressPercent.textContent = Math.floor(currentProgress) + '%';
            }
        }, 300);

        const result = await runSimulation({}, minOverlapMinutes);
        clearInterval(progressInterval);

        const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);

        // 프로그레스 바 100% 완료
        progressBar.style.width = '100%';
        progressText.textContent = '100%';
        progressPercent.textContent = '100%';

        if (result.status === 'success') {
            appState.simulationResults = result.data;
            const totalEvents = result.data.total_events || 0;

            // 예상 시간 정보 표시 (버튼 클릭 후)
            const estimatedTimeDisplay = document.getElementById('estimated-time-display');
            if (estimatedTimeDisplay && result.data.estimated_time_minutes) {
                const estimatedMin = result.data.estimated_time_minutes;
                const totalPairs = result.data.total_pairs || 0;
                document.getElementById('estimated-time-text').textContent =
                    estimatedMin < 1 ?
                    `${Math.ceil(estimatedMin * 60)}초` :
                    `${estimatedMin.toFixed(1)}분`;
                document.getElementById('estimated-pairs-text').textContent =
                    `약 ${totalPairs.toLocaleString()}개 쌍`;
                estimatedTimeDisplay.style.display = 'block';
            }

            showMessage(
                DOM.simulationStatus,
                `${totalEvents}개 유사호출 감지 완료 (${elapsedTime}초)`,
                'success'
            );

            // UI 업데이트
            updateStatistics(result.data.statistics);
            filterAndDisplayResults(result.data);

            // 내보내기 버튼 활성화
            DOM.exportJsonBtn.disabled = false;
            DOM.exportCsvBtn.disabled = false;
        } else {
            showMessage(DOM.simulationStatus, result.message || '시뮬레이션 실패', 'error');
        }
    } catch (error) {
        showMessage(DOM.simulationStatus, '시뮬레이션 중 오류 발생', 'error');
        console.error(error);
    } finally {
        DOM.simulateBtn.disabled = false;
        // 프로그레스 바 숨기기 (2초 후)
        setTimeout(() => {
            const progressContainer = document.getElementById('simulation-progress-container');
            if (progressContainer) {
                progressContainer.style.display = 'none';
                document.getElementById('simulation-progress-bar').style.width = '0%';
                document.getElementById('simulation-progress-text').textContent = '0%';
                document.getElementById('simulation-progress-percent').textContent = '';
            }
        }, 2000);
    }
}

/**
 * 삭제 방식 선택 변경 핸들러
 */
function handleDeleteTypeChange() {
    const deleteTypeRadios = document.querySelectorAll('input[name="delete-type"]');
    const deleteDateSection = document.getElementById('delete-date-section');

    if (!deleteDateSection) {
        console.warn('[경고] delete-date-section 요소를 찾을 수 없습니다');
        return;
    }

    deleteTypeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            console.log('[삭제 방식 변경]', e.target.value);
            if (e.target.value === 'date') {
                deleteDateSection.style.display = 'block';
                console.log('[날짜 섹션] 표시');
            } else {
                deleteDateSection.style.display = 'none';
                console.log('[날짜 섹션] 숨김');
            }
        });
    });
}

/**
 * DB 삭제 핸들러
 */
async function handleDeleteDatabase() {
    try {
        const deleteAllRadio = document.getElementById('delete-all');
        const deleteByDateRadio = document.getElementById('delete-by-date');
        const deleteDatePicker = document.getElementById('delete-date-picker');
        const deleteBtn = document.getElementById('delete-db-btn');

        // 선택된 라디오 버튼 값으로 deleteType 결정
        let deleteType = document.querySelector('input[name="delete-type"]:checked')?.value || 'all';
        let selectedDate = deleteType === 'date' ? deleteDatePicker.value : null;

        // 날짜 형식 정규화 (YYYY-MM-DD로 변환)
        if (selectedDate) {
            // "2025. 11. 30." 형식을 "2025-11-30"으로 변환
            selectedDate = selectedDate.replace(/\s+/g, '').replace(/\./g, '-');
            // "2025-11-30" 형식 확인
            const dateRegex = /^\d{4}-\d{1,2}-\d{1,2}$/;
            if (!dateRegex.test(selectedDate)) {
                alert('❌ 날짜 형식 오류\n\n입력된 날짜: ' + deleteDatePicker.value + '\n변환된 날짜: ' + selectedDate);
                return;
            }
            // 월과 일을 2자리로 패딩
            const [year, month, day] = selectedDate.split('-');
            selectedDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
            console.log('[날짜 변환]', deleteDatePicker.value, '→', selectedDate);
        }

        // 검증
        if (deleteType === 'date' && !selectedDate) {
            alert('⚠️ 삭제할 일자를 선택해주세요.');
            return;
        }

        // 확인 다이얼로그
        let confirmMessage = '';
        if (deleteType === 'all') {
            confirmMessage = '전체 데이터베이스를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.';
        } else {
            confirmMessage = `${selectedDate} 데이터를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`;
        }

        if (!confirm(confirmMessage)) {
            return;
        }

        deleteBtn.disabled = true;
        const statusDiv = document.createElement('div');
        statusDiv.id = 'delete-status';
        deleteBtn.parentNode.insertBefore(statusDiv, deleteBtn);

        showMessage(statusDiv, '삭제 중...', 'loading');

        // API 호출 (디버깅용 로깅)
        console.log('[삭제 요청]', { deleteType, selectedDate });
        const response = await api.deleteDatabase(deleteType, selectedDate);
        console.log('[삭제 응답]', response);

        if (response.status === 'success') {
            showMessage(statusDiv, response.message || '데이터 삭제 완료', 'success');
            alert('✅ 삭제 완료: ' + (response.message || '데이터 삭제가 완료되었습니다'));

            // 2초 후 페이지 새로고침
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            const errorMsg = response.message || response.error || '삭제 실패 - 알 수 없는 오류';
            showMessage(statusDiv, errorMsg, 'error');
            alert('❌ 삭제 실패:\n\n' + errorMsg);
            console.error('[삭제 실패]', response);
        }
    } catch (error) {
        console.error('DB 삭제 오류:', error);
        const errorMsg = error.message || error.toString() || '삭제 중 오류 발생';
        const statusDiv = document.getElementById('delete-status') || document.createElement('div');
        showMessage(statusDiv, '삭제 중 오류 발생: ' + errorMsg, 'error');
        alert('❌ 삭제 오류:\n\n' + errorMsg + '\n\n(자세한 내용은 브라우저 콘솔을 확인하세요)');
        console.error('[상세 오류]', error);
    } finally {
        const deleteBtn = document.getElementById('delete-db-btn');
        if (deleteBtn) {
            deleteBtn.disabled = false;
        }
    }
}

/**
 * 검색 처리
 */
function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();

    if (!appState.simulationResults) {
        return;
    }

    const filteredResults = appState.simulationResults.coexistences.filter(coex => {
        return coex.callsign1.toLowerCase().includes(searchTerm) ||
            coex.callsign2.toLowerCase().includes(searchTerm);
    });

    displayTableResults(filteredResults);
}

/**
 * 최소 공존시간 필터 변경 처리
 */
function handleMinOverlapChange(event) {
    const minOverlapMinutes = parseInt(event.target.value) || 0;
    appState.filters.min_overlap = minOverlapMinutes;

    if (!appState.simulationResults) {
        return;
    }

    // 최소 공존시간으로 필터링
    const filteredResults = appState.simulationResults.coexistences.filter(coex => {
        if (!coex.sector_overlaps || coex.sector_overlaps.length === 0) {
            return true; // 섹터 정보가 없으면 표시
        }
        // 최소 공존시간을 만족하는 겹침이 하나라도 있으면 표시
        return coex.sector_overlaps.some(overlap => overlap.overlap_minutes >= minOverlapMinutes);
    });

    displayTableResults(filteredResults);
}

/**
 * 날짜 필터 변경 처리
 */
async function handleDateFilterChange(event) {
    const selectedDate = event.target.value;
    appState.selectedDate = selectedDate;
    appState.pagination.page = 1; // 페이지 초기화

    console.log('날짜 필터 변경:', selectedDate);
    await loadExistingData(1, selectedDate);
}

/**
 * 날짜 필터 해제 처리
 */
async function handleClearDateFilter() {
    appState.selectedDate = null;
    appState.pagination.page = 1; // 페이지 초기화
    if (DOM.dateFilter) {
        DOM.dateFilter.value = '';
    }

    console.log('날짜 필터 해제');
    await loadExistingData(1, null);
}

/**
 * 시간대 필터 적용
 */
function handleTimeFilterChange(timeLabel) {
    if (!appState.simulationResults || !appState.simulationResults.coexistences) {
        console.log('시뮬레이션 결과가 없습니다');
        return;
    }

    // 시간대 파싱 (예: "00:00-00:15" → {start: "00:00", end: "00:15"})
    const timeParts = timeLabel.split('-');
    if (timeParts.length !== 2) {
        console.error('Invalid time label format:', timeLabel);
        return;
    }

    const startTime = timeParts[0].trim();
    const endTime = timeParts[1].trim();

    // 시간을 분으로 변환하여 비교
    const [startHour, startMin] = startTime.split(':').map(Number);
    const [endHour, endMin] = endTime.split(':').map(Number);
    const filterStartMinutes = startHour * 60 + startMin;
    const filterEndMinutes = endHour * 60 + endMin;

    // 시간대 내의 겹침을 필터링
    const filteredResults = appState.simulationResults.coexistences.filter(coex => {
        const sectorOverlaps = coex.sector_overlaps || [];

        // 이 coexistence의 겹침이 선택한 시간대와 교집합이 있는지 확인
        return sectorOverlaps.some(overlap => {
            const [overlapStartHour, overlapStartMin] = overlap.overlap_start.split(':').map(Number);
            const [overlapEndHour, overlapEndMin] = overlap.overlap_end.split(':').map(Number);
            const overlapStartMinutes = overlapStartHour * 60 + overlapStartMin;
            const overlapEndMinutes = overlapEndHour * 60 + overlapEndMin;

            // 시간대 겹침 확인
            return !(overlapEndMinutes <= filterStartMinutes || overlapStartMinutes >= filterEndMinutes);
        });
    });

    console.log(`시간대 필터 적용: ${timeLabel}, 결과: ${filteredResults.length}개`);
    displayTableResults(filteredResults);

    // UI에 선택된 시간대 표시
    if (DOM.timeFilterIndicator && DOM.timeFilterValue) {
        DOM.timeFilterValue.textContent = timeLabel;
        DOM.timeFilterIndicator.style.display = 'block';
    }
}

/**
 * 시간대 필터 해제
 */
/**
 * 시간대 필터링 (차트 클릭 시)
 */
async function filterByTimeRange(hour) {
    appState.selectedTimeFilter = hour;

    try {
        // API에 시간대 필터를 포함해서 데이터 재조회
        const selectedDate = appState.selectedDate;
        const statsResponse = await api.getStatisticsDetailed(2, 1, 20, selectedDate, hour);

        if (statsResponse && statsResponse.status === 'success') {
            const recentSimilarities = statsResponse.data.recent_similarities || [];

            // 시뮬레이션 구조로 변환
            const coexistences = recentSimilarities.map(sim => ({
                id: sim.id,
                callsign1: sim.callsign1,
                callsign2: sim.callsign2,
                similarity_level: sim.similarity_level,
                risk_level: 'UNKNOWN',
                sector_overlaps: sim.sector_overlaps || [],
                ...sim
            }));

            console.log(`시간대 필터링: ${hour}시 - ${coexistences.length}개 결과`);
            displayTableResults(coexistences);

            // 페이지네이션 정보 업데이트
            if (statsResponse.data.pagination) {
                appState.pagination.totalPages = statsResponse.data.pagination.total_pages;
                appState.pagination.page = statsResponse.data.pagination.current_page;
                updatePaginationUI();
            }

            // UI에서 필터 표시
            if (DOM.timeFilterIndicator && DOM.timeFilterValue) {
                DOM.timeFilterIndicator.style.display = 'block';
                DOM.timeFilterValue.textContent = `${hour}:00`;
            }
        }
    } catch (error) {
        console.error('시간대 필터링 오류:', error);
    }
}

/**
 * 시간대 필터 해제
 */
function handleClearTimeFilter() {
    appState.selectedTimeFilter = null;

    if (appState.simulationResults && appState.simulationResults.coexistences) {
        console.log('시간대 필터 해제');
        displayTableResults(appState.simulationResults.coexistences);
    }

    // UI에서 필터 표시 제거
    if (DOM.timeFilterIndicator) {
        DOM.timeFilterIndicator.style.display = 'none';
    }
}

/**
 * JSON 내보내기 처리
 */
async function handleExportJSON() {
    try {
        DOM.exportJsonBtn.disabled = true;

        const result = await exportJSON();

        if (result.status === 'success') {
            // JSON 다운로드
            const dataStr = JSON.stringify(result, null, 2);
            downloadFile(dataStr, 'similarity-results.json', 'application/json');
        }
    } catch (error) {
        alert('JSON 내보내기 실패');
        console.error(error);
    } finally {
        DOM.exportJsonBtn.disabled = false;
    }
}

/**
 * CSV 내보내기 처리
 */
async function handleExportCSV() {
    try {
        if (!appState.simulationResults) {
            alert('먼저 시뮬레이션을 실행하세요');
            return;
        }

        const coexistences = appState.simulationResults.coexistences;

        // CSV 헤더
        const headers = ['콜사인 1', '콜사인 2', '유사도', '위험도', '점수'];
        const csvContent = [
            headers.join(','),
            ...coexistences.map(c =>
                `${c.callsign1},${c.callsign2},${c.similarity_level},${c.risk_level},0`
            )
        ].join('\n');

        downloadFile(csvContent, 'similarity-results.csv', 'text/csv;charset=utf-8;');
    } catch (error) {
        alert('CSV 내보내기 실패');
        console.error(error);
    }
}

/**
 * 통계 UI 업데이트
 */
function updateStatisticsUI(data) {
    if (!data) return;

    // 포맷팅 함수
    const formatNumber = (num) => num ? num.toLocaleString() : '0';

    // 1. 기본 통계 (유사호출 감지, 분석된 항공편)
    if (DOM.statTotalSims) DOM.statTotalSims.textContent = formatNumber(data.total_similarities);
    if (DOM.statTotalFlights) DOM.statTotalFlights.textContent = formatNumber(data.total_flights);

    // 2. 필터링된 개수 (섹터 내 공존)
    if (DOM.statFilteredSims) DOM.statFilteredSims.textContent = formatNumber(data.filtered_similarities);

    // 3. 고급 통계 (피크 시간, 최다 빈도 섹터, 평균 공존 시간)
    if (document.getElementById('stat-peak-time')) {
        document.getElementById('stat-peak-time').textContent = data.peak_hour ? `${data.peak_hour}시` : '-';
    }

    // 최다 빈도 섹터 (상위 2개 표시, 두 줄에)
    if (document.getElementById('stat-top-sector')) {
        if (data.top_sectors && data.top_sectors.length > 0) {
            const topSectorsHtml = '<div style="display: flex; flex-direction: column; gap: 6px;">' +
                data.top_sectors
                    .slice(0, 2)
                    .map((s, idx) => `<div style="font-size: 13px;"><span style="font-weight:bold; color:#f39c12;">${s.sector_name}</span> (${s.count}건)</div>`)
                    .join('') +
                '</div>';
            document.getElementById('stat-top-sector').innerHTML = topSectorsHtml;
        } else {
            document.getElementById('stat-top-sector').textContent = data.top_sector || '-';
        }
    }

    if (document.getElementById('stat-avg-overlap')) {
        document.getElementById('stat-avg-overlap').textContent = data.avg_overlap_minutes ? `${data.avg_overlap_minutes}분` : '0분';
    }

    // 4. 차트 업데이트 (시간대별 공존 현황)
    if (typeof updateCharts === 'function') {
        updateCharts(data);
    }
}

/**
 * 결과 표시
 */
function filterAndDisplayResults(simulationData) {
    if (!simulationData || !simulationData.coexistences) return;
    displayTableResults(simulationData.coexistences);
}

/**
 * 테이블 결과 표시
 */
function displayTableResults(results) {
    DOM.tableBody.innerHTML = '';

    if (results.length === 0) {
        DOM.tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">검색 결과가 없습니다</td></tr>';
        DOM.resultCount.textContent = `결과: 0개`;
        return;
    }

    results.slice(0, 100).forEach(coex => {
        // 섹터 겹침 정보 처리
        const sectorOverlaps = coex.sector_overlaps || [];

        // 유사도 레벨 추출 및 검증
        const rawLevel = coex.similarity_level;
        const level = rawLevel && rawLevel.trim() ? rawLevel.trim() : '-';
        const formattedLevel = formatSimilarityLevel(level);

        // 디버깅 로그 (개발 모드)
        if (coex.similarity_level === null || coex.similarity_level === undefined || coex.similarity_level === '') {
            console.warn(`[테이블 렌더링] 비어있는 similarity_level 감지:`, {
                callsign1: coex.callsign1,
                callsign2: coex.callsign2,
                raw_level: rawLevel,
                formatted_level: formattedLevel
            });
        }

        if (sectorOverlaps.length === 0) {
            // 섹터 겹침이 없는 경우
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${coex.callsign1}</td>
                <td>${coex.callsign2}</td>
                <td>${formattedLevel}</td>
                <td colspan="5" class="empty-sector">섹터 겹침 정보 없음</td>
            `;
            DOM.tableBody.appendChild(row);
        } else {
            // 모든 섹터 정보를 한 줄로 통합
            const row = document.createElement('tr');
            row.classList.add('clickable-row'); // 클릭 가능 표시
            row.title = "클릭하여 상세 정보 비교 보기";
            row.onclick = () => openDetailModal(coex.flight_id_1, coex.flight_id_2, coex.callsign1, coex.callsign2);

            // 공항 정보 표시
            const route1 = coex.dept1 && coex.dest1 ? `<div style="font-size: 0.8em; color: #7f8c8d;">${coex.dept1} → ${coex.dest1}</div>` : '';
            const route2 = coex.dept2 && coex.dest2 ? `<div style="font-size: 0.8em; color: #7f8c8d;">${coex.dept2} → ${coex.dest2}</div>` : '';

            // 섹터 정보를 콤팩트하게 통합
            const sectorInfo = sectorOverlaps.map(o =>
                `<div style="font-size:0.85em; margin:2px 0;">${o.sector}: ${o.overlap_start}~${o.overlap_end} (${o.overlap_minutes}분)</div>`
            ).join('');

            row.innerHTML = `
                <td style="font-weight: bold;">
                    ${coex.callsign1}
                    ${route1}
                    <div style="margin-top: 5px;">
                        <button class="btn-climb-comparison" data-flight-id="${coex.flight_id_1}" title="고도 상승 계산 비교 보기">
                            <i class="fas fa-chart-line"></i> 비교
                        </button>
                    </div>
                </td>
                <td style="font-weight: bold;">
                    ${coex.callsign2}
                    ${route2}
                    <div style="margin-top: 5px;">
                        <button class="btn-climb-comparison" data-flight-id="${coex.flight_id_2}" title="고도 상승 계산 비교 보기">
                            <i class="fas fa-chart-line"></i> 비교
                        </button>
                    </div>
                </td>
                <td style="font-size: 0.9em;">
                    ${formattedLevel}
                </td>
                <td style="font-size: 0.85em; text-align: left;">
                    ${sectorInfo}
                </td>
            `;
            DOM.tableBody.appendChild(row);
        }
    });

    DOM.resultCount.textContent = `결과: ${results.length}개`;
}

/**
 * 메시지 표시
 */
function showMessage(element, message, type) {
    if (!element) return;

    element.className = `status-message ${type}`;

    // 로딩 중인 경우 스피너 추가
    if (type === 'loading' || type === 'info') {
        const spinner = document.createElement('span');
        spinner.className = 'spinner';
        element.innerHTML = '';
        element.appendChild(spinner);

        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        element.appendChild(messageSpan);
    } else {
        element.textContent = message;
    }
}

/**
 * 유사도 레벨에 정의를 추가하여 포맷
 * 빈 문자열/null/undefined 처리 추가
 */
function formatSimilarityLevel(levelCode) {
    // 빈 값 처리
    if (!levelCode || levelCode.trim() === '') {
        return '-';  // 비어있으면 대시 표시
    }

    // 유사도 레벨 정의 조회
    if (!appState.similarityLevels || !appState.similarityLevels[levelCode]) {
        console.warn(`유사도 레벨 정의 없음: ${levelCode}`);
        return levelCode; // 정의가 없으면 코드만 반환
    }

    const levelInfo = appState.similarityLevels[levelCode];
    const description = levelInfo.description || levelInfo.name || '';

    return description ? `${levelCode} (${description})` : levelCode;
}

/**
 * 유사도 레벨 정보를 HTML 배지로 포맷
 */
function formatSimilarityLevelBadge(levelCode) {
    if (!appState.similarityLevels || !appState.similarityLevels[levelCode]) {
        return `<span class="badge">${levelCode}</span>`;
    }

    const levelInfo = appState.similarityLevels[levelCode];
    const description = levelInfo.description || '';
    const riskColor = levelInfo.risk === 'HIGH' ? '#ff6b6b' :
                     levelInfo.risk === 'MEDIUM' ? '#ffd43b' : '#51cf66';

    return `<span class="badge" style="background-color: ${riskColor}; color: #000; cursor: help;" title="${description}">${levelCode}</span>`;
}

/**
 * 파일 다운로드
 */
function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

/**
 * 시스템 상태 업데이트
 */
function updateSystemStatus(isOnline) {
    if (DOM.systemStatus) {
        const indicator = DOM.systemStatus.querySelector('.status-indicator');
        const text = DOM.systemStatus.querySelector('.status-text');

        if (isOnline) {
            indicator.style.backgroundColor = '#27ae60';
            text.textContent = '시스템 정상';
        } else {
            indicator.style.backgroundColor = '#e74c3c';
            text.textContent = '시스템 오류';
        }
    }

    if (DOM.footerStatus) {
        DOM.footerStatus.textContent = isOnline ? '시스템 상태: 정상' : '시스템 상태: 오류';
    }
}


/**
 * 시간 비교 함수: 두 시간 범위가 겹치는지 확인
 */
function timesOverlap(start1, end1, start2, end2) {
    // 시간을 "HH:MM" 형식에서 분 단위로 변환
    const toMinutes = (timeStr) => {
        if (!timeStr) return 0;
        const [h, m] = timeStr.substring(0, 5).split(':').map(Number);
        return h * 60 + m;
    };

    const start1Min = toMinutes(start1);
    const end1Min = toMinutes(end1);
    const start2Min = toMinutes(start2);
    const end2Min = toMinutes(end2);

    // 두 범위가 겹치지 않으려면: end1 <= start2 또는 end2 <= start1
    // 따라서 겹치려면: end1 > start2 AND end2 > start1
    return end1Min > start2Min && end2Min > start1Min;
}

/**
 * 겹치는 섹터 검출
 */
function detectOverlappingSectors(flight1, flight2) {
    const overlappingSectors = [];

    if (!flight1 || !flight2 || !flight1.sectors || !flight2.sectors) {
        return overlappingSectors;
    }

    // 두 항공편의 섹터 비교
    for (const sector1 of flight1.sectors) {
        for (const sector2 of flight2.sectors) {
            // 같은 섹터 이름이고 시간이 겹칠 경우
            if (sector1.sector_name === sector2.sector_name &&
                timesOverlap(sector1.entry_time, sector1.exit_time, sector2.entry_time, sector2.exit_time)) {
                overlappingSectors.push(sector1.sector_name);
                console.log(`Found overlapping sector: ${sector1.sector_name}`);
                break; // 같은 섹터는 한 번만 추가
            }
        }
    }

    return overlappingSectors;
}

/**
 * 상세 비교 모달 열기
 */
async function openDetailModal(flightId1, flightId2, callsign1, callsign2) {
    const modal = document.getElementById('detail-modal');
    const modalBody = modal.querySelector('.modal-body');

    // 초기화 및 로딩 표시
    modal.style.display = 'block';

    // 모달 내용 초기화 (로딩 스피너)
    document.getElementById('modal-info-1').innerHTML = '<div class="spinner"></div> 데이터 로딩 중...';
    document.getElementById('modal-info-2').innerHTML = '<div class="spinner"></div> 데이터 로딩 중...';
    document.getElementById('modal-waypoint-table-1').innerHTML = '';
    document.getElementById('modal-waypoint-table-2').innerHTML = '';
    document.getElementById('modal-table-1').innerHTML = '';
    document.getElementById('modal-table-2').innerHTML = '';

    // 제목 설정
    document.getElementById('modal-title-1').textContent = callsign1;
    document.getElementById('modal-title-2').textContent = callsign2;

    try {
        console.log('Requesting flight details:', { flightId1, flightId2 });

        // API 호출
        const response = await api.getFlightPairDetails(flightId1, flightId2);
        console.log('Flight details response:', response);

        if (response.status === 'success') {
            const data = response.data;
            console.log('Flight data:', data);

            // 겹치는 섹터 검출
            const overlappingSectors = detectOverlappingSectors(data.flight1, data.flight2);
            console.log('Overlapping sectors:', overlappingSectors);

            updateModalColumn(1, data.flight1, callsign1, overlappingSectors);
            updateModalColumn(2, data.flight2, callsign2, overlappingSectors);
        } else {
            alert('데이터를 불러오는데 실패했습니다.');
            modal.style.display = 'none';
        }
    } catch (error) {
        console.error('상세 정보 로드 실패:', error);
        alert('서버 통신 오류가 발생했습니다.');
        modal.style.display = 'none';
    }
}

/**
 * 모달 컬럼 업데이트 (항공편 정보 및 섹터 테이블)
 */
function updateModalColumn(index, flightData, callsign, overlappingSectors = []) {
    console.log(`updateModalColumn called with index=${index}, flightData:`, flightData);

    if (!flightData) {
        console.log(`No flight data for index ${index}`);
        return;
    }

    const info = flightData.info;
    const sectors = flightData.sectors;
    console.log(`Sectors for index ${index}:`, sectors);


    // 1. 기본 정보 렌더링
    const infoHtml = `
        <div class="flight-info-box">
            <strong>${callsign}</strong> (${info.aircraft_type || 'Unknown'})\n
            <span style="color:#666;">${info.dept_airport_cd || '?'} → ${info.dest_airport_cd || '?'}</span><br>
            Speed: ${info.spd || '-'} / Level: ${info.alt || '-'}<br>
            Route: <span style="font-size:0.85em; color:#555;">${info.enr || '-'}</span>
        </div>
    `;

    // HTML ID: modal-info-1 or modal-info-2
    const infoEl = document.getElementById(`modal-info-${index}`);
    if (infoEl) infoEl.innerHTML = infoHtml;

    // 2. 지점별 통과 시간 테이블 렌더링
    const waypointTableEl = document.getElementById(`modal-waypoint-table-${index}`);
    if (waypointTableEl) {
        let waypointRowsHtml = '';
        const waypoints = flightData.waypoints || [];

        // 배열 형식 처리 (API에서 반환되는 새 형식)
        if (waypoints && waypoints.length > 0) {
            waypoints.forEach(w => {
                const time = w.estimated_time || w.actual_time || '-';
                waypointRowsHtml += `
                    <tr>
                        <td>${w.waypoint_name}</td>
                        <td>${time}</td>
                    </tr>
                `;
            });
        }
        // 폴백: 기존 문자열 형식도 처리
        else {
            const waypointTimesStr = info.waypoint_times || '';
            if (waypointTimesStr) {
                // Parse waypoint_times format: "POINTNAME HHMM POINTNAME HHMM ..."
                const parts = waypointTimesStr.trim().split(/\s+/);
                for (let i = 0; i < parts.length; i += 2) {
                    if (i + 1 < parts.length) {
                        const pointName = parts[i];
                        const timeStr = parts[i + 1];
                        // Convert HHMM to HH:MM format
                        const formattedTime = timeStr.length === 4 ?
                            `${timeStr.substring(0, 2)}:${timeStr.substring(2, 4)}` :
                            timeStr;
                        waypointRowsHtml += `
                            <tr>
                                <td>${pointName}</td>
                                <td>${formattedTime}</td>
                            </tr>
                        `;
                    }
                }
            }
        }

        if (!waypointRowsHtml) {
            waypointRowsHtml = `<tr><td colspan="2">지점 통과 정보 없음</td></tr>`;
        }
        waypointTableEl.innerHTML = waypointRowsHtml;
    }

    // 3. 섹터 테이블 렌더링
    // HTML ID: modal-table-1 or modal-table-2 (tbody)
    const tbodyEl = document.getElementById(`modal-table-${index}`);
    if (tbodyEl) {
        let rowsHtml = '';
        if (sectors && sectors.length > 0) {
            sectors.forEach(s => {
                // 겹치는 섹터인지 확인
                const isOverlapping = overlappingSectors.includes(s.sector_name);
                const rowClass = isOverlapping ? ' class="overlapping-sector"' : '';

                rowsHtml += `
                    <tr${rowClass}>
                        <td>${s.sector_name}</td>
                        <td>${(s.entry_time || '').substring(0, 5)}</td>
                        <td>${(s.exit_time || '').substring(0, 5)}</td>
                    </tr>
                `;
            });
        } else {
            rowsHtml = `<tr><td colspan="3">섹터 정보 없음</td></tr>`;
        }
        tbodyEl.innerHTML = rowsHtml;
    }
}


/**
 * 전체 항공편 목록 로드 및 표시 (페이지네이션 포함)
 */
async function loadAllFlights(page = 1, eobd = null) {
    const tableBody = document.getElementById('all-flights-body');
    tableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;"><div class="spinner"></div> 데이터 로딩 중...</td></tr>';

    try {
        // eobd가 제공되지 않으면 appState에서 사용
        if (eobd === null) {
            eobd = appState.allFlightsSelectedDate;
        }
        const response = await api.getAllFlights(page, 100, eobd);  // 페이지당 100개로 증가
        console.log('All flights response:', response);

        if (response.status === 'success' && response.data) {
            let flights = response.data;
            const pagination = response.pagination;

            // 날짜순으로 정렬 (시간도 함께 정렬)
            flights.sort((a, b) => {
                const dateTimeA = `${a.eobd || ''}T${a.eobt || '00:00'}`;
                const dateTimeB = `${b.eobd || ''}T${b.eobt || '00:00'}`;
                return new Date(dateTimeA) - new Date(dateTimeB);
            });

            // 전체 항공편 수 표시
            const header = document.querySelector('.view-section.active h2') || document.querySelector('h2');
            if (header) {
                header.innerHTML = `<i class="fas fa-plane"></i> 전체 항공편 상세 정보 <span style="color:#999; font-size:0.8em; margin-left:10px;"> (총 ${pagination.total}건)</span>`;
            }

            if (flights.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">데이터가 없습니다</td></tr>';
                return;
            }

            tableBody.innerHTML = '';

            flights.forEach((f, index) => {
                const row = document.createElement('tr');
                // 행 번호 계산: (페이지-1) * 페이지당항목수 + 인덱스 + 1
                const rowNumber = (pagination.page - 1) * pagination.limit + index + 1;

                // 유사호출 정보 조회
                let similarityHtml = '<span style="color:#999;">없음</span>';

                // 방법 1: API에서 직접 반환된 similarities 배열 사용
                if (f.similarities && f.similarities.length > 0) {
                    const levelGroups = {};
                    f.similarities.forEach(sim => {
                        const level = sim.similarity_level;
                        const hasOverlap = sim.has_sector_overlap;  // 실제 공존 여부

                        if (!levelGroups[level]) {
                            levelGroups[level] = {
                                withOverlap: [],    // 공존하는 항공기
                                withoutOverlap: []  // 공존하지 않는 항공기
                            };
                        }

                        if (hasOverlap) {
                            if (!levelGroups[level].withOverlap.includes(sim.other_callsign)) {
                                levelGroups[level].withOverlap.push(sim.other_callsign);
                            }
                        } else {
                            if (!levelGroups[level].withoutOverlap.includes(sim.other_callsign)) {
                                levelGroups[level].withoutOverlap.push(sim.other_callsign);
                            }
                        }
                    });

                    similarityHtml = Object.entries(levelGroups)
                        .map(([level, callsignGroups]) => {
                            const formattedLevel = formatSimilarityLevel(level);
                            let html = `<div style="margin:3px 0; font-size:0.85em;">
                                <strong>${formattedLevel}</strong><br>`;

                            // 공존하는 항공기 (초록색 강조)
                            if (callsignGroups.withOverlap.length > 0) {
                                html += `<span style="color:#27ae60; font-weight:bold; font-size:0.8em;">
                                    ✓ ${callsignGroups.withOverlap.join(', ')}</span><br>`;
                            }

                            // 공존하지 않는 항공기 (회색 표시)
                            if (callsignGroups.withoutOverlap.length > 0) {
                                html += `<span style="color:#999; font-size:0.8em;">
                                    ○ ${callsignGroups.withoutOverlap.join(', ')}</span>`;
                            }

                            html += `</div>`;
                            return html;
                        })
                        .join('');
                }
                // 폴백: 시뮬레이션 결과에서 찾기 (기존 방법)
                else if (appState.simulationResults && appState.simulationResults.coexistences) {
                    const coexistences = appState.simulationResults.coexistences.filter(coex =>
                        coex.flight_id_1 === f.id || coex.flight_id_2 === f.id
                    );

                    if (coexistences.length > 0) {
                        const levelGroups = {};
                        coexistences.forEach(coex => {
                            const level = coex.similarity_level;
                            if (!levelGroups[level]) {
                                levelGroups[level] = [];
                            }
                            const otherCallsign = coex.flight_id_1 === f.id ? coex.callsign2 : coex.callsign1;
                            if (!levelGroups[level].includes(otherCallsign)) {
                                levelGroups[level].push(otherCallsign);
                            }
                        });

                        similarityHtml = Object.entries(levelGroups)
                            .map(([level, callsigns]) => {
                                const formattedLevel = formatSimilarityLevel(level);
                                return `<div style="margin:3px 0; font-size:0.85em;">
                                    <strong>${formattedLevel}</strong><br>
                                    <span style="color:#666; font-size:0.8em;">${callsigns.join(', ')}</span>
                                </div>`;
                            })
                            .join('');
                    }
                }

                // 지점별 통과시간 포맷팅
                let waypointHtml = '<span style="color:#999; font-size:0.9em;">지점 정보 없음</span>';

                // 배열 형식으로 처리 (백엔드에서 waypoints 배열 반환)
                if (f.waypoints && f.waypoints.length > 0) {
                    const waypointItems = f.waypoints.map(w => {
                        const time = w.estimated_time || w.actual_time || '-';
                        const displayTime = time.length === 5 ? time : (time.length === 4 ? `${time.substring(0, 2)}:${time.substring(2, 4)}` : time);
                        return `${w.waypoint_name} ${displayTime}`;
                    });

                    if (waypointItems.length > 0) {
                        waypointHtml = waypointItems.map(item =>
                            `<span style="display:inline-block; background:#e8f5e9; padding:2px 6px; margin:2px 2px; border-radius:3px; font-size:0.8em; border:1px solid #c8e6c9; color:#2e7d32;">${item}</span>`
                        ).join('');
                    }
                }
                // 폴백: 기존 waypoint_times 문자열 형식도 처리
                else if (f.waypoint_times && f.waypoint_times.trim()) {
                    const parts = f.waypoint_times.trim().split(/\s+/);
                    const waypointItems = [];
                    for (let i = 0; i < parts.length; i += 2) {
                        if (i + 1 < parts.length) {
                            const pointName = parts[i];
                            const timeStr = parts[i + 1];
                            const formattedTime = timeStr.length === 4 ?
                                `${timeStr.substring(0, 2)}:${timeStr.substring(2, 4)}` :
                                timeStr;
                            waypointItems.push(`${pointName} ${formattedTime}`);
                        }
                    }
                    if (waypointItems.length > 0) {
                        waypointHtml = waypointItems.map(item =>
                            `<span style="display:inline-block; background:#e8f5e9; padding:2px 6px; margin:2px 2px; border-radius:3px; font-size:0.8em; border:1px solid #c8e6c9; color:#2e7d32;">${item}</span>`
                        ).join('');
                    }
                }

                // 섹터 정보 포맷팅 (없으면 "정보 없음" 표시)
                let sectorHtml = '<span style="color:#999;">정보 없음</span>';
                if (f.sectors && f.sectors.length > 0) {
                    // 보기 좋게 칩 형태로 나열
                    sectorHtml = f.sectors.map(s =>
                        `<span style="
                            display:inline-block;
                            background:#f1f2f6;
                            padding:3px 8px;
                            margin:2px;
                            border-radius:4px;
                            font-size:0.85em;
                            border:1px solid #dfe4ea;">
                            <strong>${s.sector_name}</strong><br>
                            진입: ${(s.entry_time || '').substring(0, 5)}&nbsp;|&nbsp;진출: ${(s.exit_time || '').substring(0, 5)}
                        </span>`
                    ).join('');
                }

                row.innerHTML = `
                    <td style="text-align:center; font-weight:bold; color:#667eea; background:#f8f9fa;">${rowNumber}</td>
                    <td style="font-weight:bold; color:#2c3e50;">${f.callsign}</td>
                    <td>
                        <div>${f.eobd || '-'}</div>
                        <div style="font-size:0.9em; color:#7f8c8d;">${f.eobt ? f.eobt.substring(0, 5) : '-'}</div>
                    </td>
                    <td>
                        <span class="badge badge-low">${f.dept_airport_cd || '?'}</span>
                        <i class="fas fa-arrow-right" style="font-size:0.8em; color:#95a5a6; margin:0 4px;"></i>
                        <span class="badge badge-low">${f.dest_airport_cd || '?'}</span>
                    </td>
                    <td style="font-size:0.9em;">
                        <div>TYPE: ${f.aircraft_type || '-'}</div>
                        <div style="color:#666;">SPD: ${f.spd || '-'} / ALT: ${f.alt || '-'}</div>
                    </td>
                    <td style="text-align:left; word-wrap:break-word;">
                        ${waypointHtml}
                    </td>
                    <td style="text-align:left; word-wrap:break-word;">
                        ${sectorHtml}
                    </td>
                    <td style="text-align:left; font-size:0.9em;">
                        ${similarityHtml}
                    </td>
                `;
                tableBody.appendChild(row);
            });

            // 페이지네이션 컨트롤 업데이트
            updateAllFlightsPageination(pagination);

        }
    } catch (error) {
        console.error('전체 항공편 로드 실패:', error);
        tableBody.innerHTML = '<tr><td colspan="8" class="empty-state" style="color:red;">데이터 로드 실패</td></tr>';
    }
}

/**
 * 전체 항공편 페이지네이션 업데이트
 */
function updateAllFlightsPageination(pagination) {
    // 페이지네이션 컨트롤이 없으면 추가
    let paginationDiv = document.getElementById('all-flights-pagination');
    if (!paginationDiv) {
        paginationDiv = document.createElement('div');
        paginationDiv.id = 'all-flights-pagination';
        paginationDiv.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #ddd;';

        // all-flights-view 내 panel의 마지막 요소로 추가
        const allFlightsView = document.getElementById('all-flights-view');
        const panel = allFlightsView ? allFlightsView.querySelector('.panel') : null;
        if (panel) {
            panel.appendChild(paginationDiv);
        }
    }

    const startItem = (pagination.page - 1) * pagination.limit + 1;
    const endItem = Math.min(pagination.page * pagination.limit, pagination.total);

    paginationDiv.innerHTML = `
        <button class="btn btn-secondary" id="all-flights-prev" onclick="loadAllFlights(${Math.max(1, pagination.page - 1)})" ${pagination.page === 1 ? 'disabled' : ''} style="padding: 8px 12px;">
            <i class="fas fa-chevron-left"></i> 이전
        </button>

        <div style="display: flex; flex-direction: row; align-items: center; gap: 15px; white-space: nowrap;">
            <span style="font-size: 13px; font-weight: bold; color: #2c3e50; min-width: 100px; text-align: center;">
                페이지 ${pagination.page} / ${pagination.total_pages}
            </span>
            <span style="font-size: 12px; color: #7f8c8d;">
                항목 ${startItem} ~ ${endItem} / 총 ${pagination.total}건
            </span>
        </div>

        <button class="btn btn-secondary" id="all-flights-next" onclick="loadAllFlights(${Math.min(pagination.total_pages, pagination.page + 1)})" ${pagination.page === pagination.total_pages ? 'disabled' : ''} style="padding: 8px 12px;">
            다음 <i class="fas fa-chevron-right"></i>
        </button>
    `;
}

/**
 * 전체 항공편 - 날짜 네비게이션 함수들
 */
/**
 * 전체 항공편 날짜 선택 변경 (달력)
 */
function handleAllFlightsDatePickerChange(event) {
    const selectedDate = event.target.value;
    if (selectedDate) {
        appState.allFlightsSelectedDate = selectedDate;
        loadAllFlights(1, selectedDate);
    }
}

/**
 * 전체 항공편 날짜 표시 업데이트
 */
function updateAllFlightsDateDisplay() {
    if (DOM.allFlightsDatePicker && appState.allFlightsAvailableDates.length > 0) {
        // Date picker의 min/max 설정
        const sortedDates = appState.allFlightsAvailableDates.sort();
        DOM.allFlightsDatePicker.min = sortedDates[0];
        DOM.allFlightsDatePicker.max = sortedDates[sortedDates.length - 1];

        // 선택된 날짜 또는 전체 보기
        if (appState.allFlightsSelectedDate) {
            DOM.allFlightsDatePicker.value = appState.allFlightsSelectedDate;
        } else {
            // 전체보기: 날짜 피커를 비우기 (null 또는 빈 문자열)
            DOM.allFlightsDatePicker.value = '';
        }
    }
}

function handleAllFlightsViewByDate() {
    if (appState.allFlightsDateIndex < 0 || appState.allFlightsAvailableDates.length === 0) {
        showMessage(DOM.simulationStatus, '조회할 날짜를 선택하세요.', 'warning');
        return;
    }
    const selectedDate = appState.allFlightsAvailableDates[appState.allFlightsDateIndex];
    appState.allFlightsSelectedDate = selectedDate;
    loadAllFlights(1, selectedDate);
}

function handleAllFlightsClearFilter() {
    appState.allFlightsSelectedDate = null;
    appState.allFlightsDateIndex = -1;
    updateAllFlightsDateDisplay();
    loadAllFlights(1, null);
}

async function loadAllFlightsDateList() {
    try {
        // API에서 사용 가능한 날짜 조회
        const response = await api.getAvailableDates();
        if (response.status === 'success' && response.data && response.data.length > 0) {
            appState.allFlightsAvailableDates = response.data;
        } else {
            appState.allFlightsAvailableDates = [];
        }

        // 기본값으로 첫 번째 날짜(최신 날짜) 선택
        if (appState.allFlightsAvailableDates.length > 0) {
            appState.allFlightsDateIndex = 0;
            appState.allFlightsSelectedDate = appState.allFlightsAvailableDates[0];
        }
        updateAllFlightsDateDisplay();
    } catch (error) {
        console.error('전체 항공편 사용 가능 날짜 로드 실패:', error);
        appState.allFlightsAvailableDates = [];
        updateAllFlightsDateDisplay();
    }
}

/**
 * ⚡ CLI 빠른 시뮬레이션 핸들러
 */

// CLI 파일 선택 처리
function handleCLIFileSelection(event) {
    const file = event.target.files[0];
    if (!file) return;

    const fileInput = document.getElementById('cli-file-input');
    const selectedFileDiv = document.getElementById('cli-selected-file');
    const filenameSpan = document.getElementById('cli-filename');
    const runBtn = document.getElementById('cli-run-btn');

    console.log('[CLI] 파일 선택됨:', file.name, file.size, file.type);

    filenameSpan.textContent = file.name;
    selectedFileDiv.style.display = 'flex';
    // 파일 객체를 직접 저장
    fileInput._selectedFile = file;
    runBtn.disabled = false;
}

// CLI 드래그 오버
function handleCLIDragOver(event) {
    event.preventDefault();
    event.currentTarget.style.background = '#e3f2fd';
}

// CLI 드래그 리브
function handleCLIDragLeave(event) {
    event.currentTarget.style.background = 'white';
}

// CLI 드롭
function handleCLIDrop(event) {
    event.preventDefault();
    event.currentTarget.style.background = 'white';

    const file = event.dataTransfer.files[0];
    if (!file) return;

    const fileInput = document.getElementById('cli-file-input');
    const selectedFileDiv = document.getElementById('cli-selected-file');
    const filenameSpan = document.getElementById('cli-filename');
    const runBtn = document.getElementById('cli-run-btn');

    filenameSpan.textContent = file.name;
    selectedFileDiv.style.display = 'flex';
    fileInput._selectedFile = file;
    runBtn.disabled = false;
}

// CLI 시뮬레이션 실행
async function handleCLIRun() {
    const fileInput = document.getElementById('cli-file-input');
    const file = fileInput._selectedFile || fileInput.files[0];
    const statusDiv = document.getElementById('cli-status');
    const progressContainer = document.getElementById('cli-progress-container');
    const progressBar = document.getElementById('cli-progress-bar');
    const progressText = document.getElementById('cli-progress-text');
    const runBtn = document.getElementById('cli-run-btn');

    if (!file) {
        showMessage(statusDiv, '파일을 선택하세요', 'error');
        return;
    }

    runBtn.disabled = true;
    statusDiv.textContent = '';
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = '처리 중... (0%)';

    try {
        // FormData로 파일 준비
        const formData = new FormData();
        formData.append('file', file);
        formData.append('reset_db', 'true'); // DB 초기화

        // API 호출
        const response = await fetch('http://localhost:8888/api/simulation/run-cli', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            showMessage(statusDiv, `❌ 오류: ${error.message}`, 'error');
            return;
        }

        const result = await response.json();

        // 진행 상황 표시
        if (result.status === 'success') {
            progressBar.style.width = '100%';
            progressText.textContent = `✅ 완료! (${result.message})`;

            const message =
                `✅ 시뮬레이션 완료!\n` +
                `📍 검출된 유사호출: ${result.data?.similarity_count || 0}개\n` +
                `⏱️  소요시간: ${result.data?.elapsed_time?.toFixed(1) || '?'}초`;

            showMessage(statusDiv, message, 'success');

            // 대시보드 새로고침
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showMessage(statusDiv, `❌ 오류: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('CLI 시뮬레이션 오류:', error);
        showMessage(statusDiv, `❌ 오류: ${error.message}`, 'error');
    } finally {
        runBtn.disabled = false;
        progressContainer.style.display = 'none';
    }
}

// CLI DB 초기화
async function handleCLIResetDB() {
    if (!confirm('📌 데이터베이스를 초기화하시겠습니까?\n(모든 항공편, 유사호출, 통계 데이터가 삭제됩니다)')) {
        return;
    }

    const statusDiv = document.getElementById('cli-status');
    showMessage(statusDiv, '초기화 중...', 'loading');

    try {
        const response = await fetch('http://localhost:8888/api/simulation/reset-db', {
            method: 'POST'
        });

        if (!response.ok) {
            showMessage(statusDiv, '❌ DB 초기화 실패', 'error');
            return;
        }

        showMessage(statusDiv, '✅ DB 초기화 완료', 'success');

        // 1초 후 페이지 새로고침
        setTimeout(() => {
            location.reload();
        }, 1000);
    } catch (error) {
        console.error('DB 초기화 오류:', error);
        showMessage(statusDiv, `❌ 오류: ${error.message}`, 'error');
    }
}

// CLI 이벤트 리스너 등록
function attachCLIEventListeners() {
    // 파일 선택
    const cliFileInput = document.getElementById('cli-file-input');
    if (cliFileInput) {
        cliFileInput.addEventListener('change', handleCLIFileSelection);
    }

    // 드래그 앤 드롭
    const cliDropZone = document.getElementById('cli-drop-zone');
    if (cliDropZone) {
        cliDropZone.addEventListener('dragover', handleCLIDragOver);
        cliDropZone.addEventListener('dragleave', handleCLIDragLeave);
        cliDropZone.addEventListener('drop', handleCLIDrop);
    }

    // 적용 버튼
    const cliRunBtn = document.getElementById('cli-run-btn');
    if (cliRunBtn) {
        cliRunBtn.addEventListener('click', handleCLIRun);
    }

    // DB 초기화 버튼
    const cliResetBtn = document.getElementById('cli-reset-db-btn');
    if (cliResetBtn) {
        cliResetBtn.addEventListener('click', handleCLIResetDB);
    }
}

/**
 * 초기화
 */
async function loadSidebarStatistics() {
    /**
     * 왼쪽 사이드바에 항공사별, 유사도 레벨, 콜사인10 통계 로드
     */
    try {
        const response = await api.getStatisticsSummary();

        if (response && response.status === 'success' && response.data) {
            const data = response.data;

            // 1. 항공사별 유사호출 표시
            const airlineStatsDiv = document.getElementById('sidebar-airline-stats');
            if (airlineStatsDiv && data.airline_ranking && data.airline_ranking.length > 0) {
                let airlineHtml = '<div style="display: flex; flex-direction: column; gap: 8px;">';
                data.airline_ranking.forEach((item, idx) => {
                    const airline = item.airline || '-';
                    const count = item.count || 0;
                    const barWidth = (count / data.airline_ranking[0].count) * 100;
                    airlineHtml += `
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="min-width: 40px; font-weight: 600; color: #2c3e50;">${airline}</span>
                            <div style="flex: 1; background: #ecf0f1; border-radius: 3px; height: 18px; position: relative;">
                                <div style="background: linear-gradient(90deg, #3498db 0%, #2980b9 100%); height: 100%; border-radius: 3px; width: ${barWidth}%;"></div>
                            </div>
                            <span style="min-width: 30px; text-align: right; font-weight: 600; color: #2980b9;">${count}</span>
                        </div>
                    `;
                });
                airlineHtml += '</div>';
                airlineStatsDiv.innerHTML = airlineHtml;
            } else {
                airlineStatsDiv.innerHTML = '<p style="color: #999; text-align: center;">데이터 없음</p>';
            }

            // 2. 유사도 레벨 분포 표시
            const similarityLevelDiv = document.getElementById('sidebar-similarity-level-stats');
            if (similarityLevelDiv && data.level_ranking && data.level_ranking.length > 0) {
                let levelHtml = '<div style="display: flex; flex-direction: column; gap: 6px;">';
                const maxCount = data.level_ranking[0].count || 1;
                data.level_ranking.forEach((item) => {
                    const level = item.level || '-';
                    const count = item.count || 0;
                    const barWidth = (count / maxCount) * 100;
                    const levelColors = {
                        'LEVEL_4-3': '#e74c3c',
                        'LEVEL_4-2': '#e67e22',
                        'LEVEL_4-1': '#f39c12',
                        'LEVEL_3-2': '#f1c40f',
                        'LEVEL_3-1': '#27ae60'
                    };
                    const barColor = levelColors[level] || '#95a5a6';
                    levelHtml += `
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="min-width: 80px; font-weight: 600; color: #2c3e50; font-size: 12px;">${level}</span>
                            <div style="flex: 1; background: #ecf0f1; border-radius: 3px; height: 16px; position: relative;">
                                <div style="background: ${barColor}; height: 100%; border-radius: 3px; width: ${barWidth}%;"></div>
                            </div>
                            <span style="min-width: 30px; text-align: right; font-weight: 600; color: #2c3e50; font-size: 12px;">${count}</span>
                        </div>
                    `;
                });
                levelHtml += '</div>';
                similarityLevelDiv.innerHTML = levelHtml;
            } else {
                similarityLevelDiv.innerHTML = '<p style="color: #999; text-align: center;">데이터 없음</p>';
            }

            // 3. 콜사인 TOP 10 표시
            const topSimilaritiesDiv = document.getElementById('sidebar-top-similarities');
            if (topSimilaritiesDiv && data.callsign_top10 && data.callsign_top10.length > 0) {
                let topHtml = '<div style="display: flex; flex-direction: column; gap: 6px;">';
                data.callsign_top10.forEach((item, idx) => {
                    const callsign1 = item.callsign_1 || '-';
                    const callsign2 = item.callsign_2 || '-';
                    const score = (item.similarity_score || 0).toFixed(3);
                    const level = item.similarity_level || '-';
                    topHtml += `
                        <div style="padding: 6px; background: #fff; border: 1px solid #ecf0f1; border-radius: 4px; font-size: 11px; line-height: 1.4;">
                            <div style="font-weight: 600; color: #2c3e50;">${idx + 1}. ${callsign1} ↔ ${callsign2}</div>
                            <div style="color: #7f8c8d; margin-top: 2px;">
                                <span>점수: <span style="color: #e74c3c; font-weight: 600;">${score}</span></span>
                                <span style="margin-left: 8px;">레벨: <span style="color: #2980b9; font-weight: 600;">${level}</span></span>
                            </div>
                        </div>
                    `;
                });
                topHtml += '</div>';
                topSimilaritiesDiv.innerHTML = topHtml;
            } else {
                topSimilaritiesDiv.innerHTML = '<p style="color: #999; text-align: center;">데이터 없음</p>';
            }

            console.log('사이드바 통계 로드 완료');
        } else {
            console.error('통계 데이터 조회 실패');
        }
    } catch (error) {
        console.error('사이드바 통계 로드 오류:', error);
        document.getElementById('sidebar-airline-stats').innerHTML = '<p style="color: #999; text-align: center;">오류</p>';
        document.getElementById('sidebar-similarity-level-stats').innerHTML = '<p style="color: #999; text-align: center;">오류</p>';
        document.getElementById('sidebar-top-similarities').innerHTML = '<p style="color: #999; text-align: center;">오류</p>';
    }
}

async function initializeUI() {
    initializeDOM();
    attachEventListeners();
    attachCLIEventListeners(); // CLI 이벤트 리스너 추가

    // 초기 버튼 상태
    DOM.uploadBtn.disabled = true;
    DOM.simulateBtn.disabled = true;
    DOM.exportJsonBtn.disabled = true;
    DOM.exportCsvBtn.disabled = true;

    // 시스템 상태 확인
    api.healthCheck()
        .then(() => updateSystemStatus(true))
        .catch(() => updateSystemStatus(false));

    // 사용 가능한 날짜 로드
    await loadAvailableDates();

    // 유사도 레벨 정의 로드 (필수 - 테이블 렌더링 전에 완료되어야 함)
    console.log('[초기화] 유사도 레벨 정의 로드 중...');
    await loadSimilarityLevels();
    console.log('[초기화] 유사도 레벨 정의 로드 완료:', Object.keys(appState.similarityLevels || {}).length, '개');

    // 전체 항공편 탭의 날짜 목록 로드
    await loadAllFlightsDateList();

    // 왼쪽 사이드바 통계 로드
    console.log('[초기화] 사이드바 통계 로드 중...');
    await loadSidebarStatistics();

    // 페이지 로드 시 기존 데이터 조회 (오늘 날짜 데이터로 초기화)
    // 유사도 레벨 정의 로드 완료 후 실행되도록 주의
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD 형식
    appState.selectedDate = today;
    await loadExistingData(1, today);

    // 전체 항공편 탭의 기본 데이터 로드 (기본값: 오늘 날짜)
    if (appState.allFlightsSelectedDate) {
        await loadAllFlights(1, appState.allFlightsSelectedDate);
    }
}

// DOM 로드 완료 후 초기화
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeUI);
} else {
    initializeUI();
}
