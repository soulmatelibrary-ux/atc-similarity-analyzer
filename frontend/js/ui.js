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
    selectedDateRange: null,  // 범위 조회 상태 {start: date, end: date}
    // 전체 항공편 필터
    allFlightsSelectedDate: null,  // 전체 항공편 탭의 선택된 날짜
    allFlightsDateIndex: 0,        // 전체 항공편 탭의 날짜 인덱스
    allFlightsAvailableDates: [],  // 전체 항공편 탭의 사용 가능한 날짜
    // 유사도 레벨 정의
    similarityLevels: {},  // 유사도 레벨 및 설명 매핑
    // 시간대 필터
    selectedTimeFilter: null,  // 선택된 시간대 필터 (차트 클릭)
    // 테이블 정렬
    tableSortColumn: null,  // 현재 정렬 중인 컬럼
    tableSortDirection: 'asc',  // 정렬 방향 ('asc' 또는 'desc')
    // 라이선스 관리
    generatedLicense: null  // 생성된 라이선스 데이터
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

// 기간 분석 전용 상태
const PERIOD_ANALYSIS_MAX_DAYS = 31;
const PERIOD_LEVEL_ORDER = ['LEVEL_5', 'LEVEL_4', 'LEVEL_3'];
let periodDailyChartInstance = null;

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
    DOM.startDatePicker = document.getElementById('start-date-picker');
    DOM.endDatePicker = document.getElementById('end-date-picker');
    DOM.dateRangeDisplay = document.getElementById('date-range-display');
    DOM.dateRangeWarning = document.getElementById('date-range-warning');
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
    DOM.allFlightsDatePrevBtn = document.getElementById('all-flights-date-prev-btn');
    DOM.allFlightsDateNextBtn = document.getElementById('all-flights-date-next-btn');
    DOM.allFlightsViewBtn = document.getElementById('all-flights-view-btn');
    DOM.allFlightsClearFilterBtn = document.getElementById('all-flights-clear-filter-btn');

    // 시간대 필터 요소
    DOM.timeFilterIndicator = document.getElementById('time-filter-indicator');
    DOM.timeFilterValue = document.getElementById('time-filter-value');
    DOM.clearTimeFilterBtn = document.getElementById('clear-time-filter-btn');

    // 일자별 필터 요소
    DOM.dateFilterIndicator = document.getElementById('date-filter-indicator');
    DOM.dateFilterValue = document.getElementById('date-filter-value');
    DOM.clearDateFilterBtn = document.getElementById('clear-date-filter-btn');

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

        // 상세 통계 조회 (리스트 포함) - 페이징 제거: 10000개까지 한번에 로드
        const statsResponse = await api.getStatisticsDetailed(2, page, 10000, selectedDate);

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
        // 범위 조회 상태가 있으면 범위 조회 유지, 아니면 단일 날짜 조회
        if (appState.selectedDateRange) {
            // 범위 조회 페이지 변경
            await handleViewResultsPage(newPage);
        } else {
            // 단일 날짜 조회 페이지 변경
            await loadExistingData(newPage);
        }
    }
}

/**
 * 범위 조회 페이지 변경 처리
 */
async function handleViewResultsPage(page = 1) {
    try {
        if (!appState.selectedDateRange) return;

        const startDate = appState.selectedDateRange.start;
        const endDate = appState.selectedDateRange.end;

        // 범위 조회 API 호출 (페이징 제거: 10000개까지 한번에 로드)
        const url = `${API_BASE_URL}/statistics/detailed?start_date=${startDate}&end_date=${endDate}&page=${page}&limit=10000`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`API 오류: ${response.status}`);

        const result = await response.json();
        if (result.status !== 'success') throw new Error(result.message);

        // 데이터 표시
        const statistics = result.data;
        const coexistences = statistics.recent_similarities || [];

        displayTableResults(coexistences);

        // 결과 개수 업데이트
        const resultCount = document.getElementById('result-count');
        if (resultCount) {
            resultCount.textContent = `결과: ${statistics.pagination?.total_count || coexistences.length}개`;
        }

        // 페이지네이션 정보 업데이트
        if (statistics.pagination) {
            appState.pagination.page = statistics.pagination.current_page || page;
            appState.pagination.totalPages = statistics.pagination.total_pages || 1;
        }
        updatePaginationUI();

    } catch (error) {
        console.error('범위 조회 페이지 변경 오류:', error);
        showMessage(DOM.simulationStatus, `페이지 로드 실패: ${error.message}`, 'error');
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

    // 테이블 CSV 내보내기 버튼 (대시보드용)
    const exportTableCsvBtn = document.getElementById('export-csv-btn');
    if (exportTableCsvBtn) {
        exportTableCsvBtn.addEventListener('click', handleExportTableCSV);
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

    // 날짜 선택 (달력) - 새로운 범위 선택 사용으로 주석 처리
    // if (DOM.selectedDatePicker) {
    //     DOM.selectedDatePicker.addEventListener('change', handleDatePickerChange);
    // }

    // 빠른 날짜 선택 버튼
    const quickDateTodayBtn = document.getElementById('quick-date-today');
    if (quickDateTodayBtn) {
        quickDateTodayBtn.addEventListener('click', handleQuickDateToday);
    }

    const quickDateYesterdayBtn = document.getElementById('quick-date-yesterday');
    if (quickDateYesterdayBtn) {
        quickDateYesterdayBtn.addEventListener('click', handleQuickDateYesterday);
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
    if (DOM.allFlightsDatePrevBtn) {
        DOM.allFlightsDatePrevBtn.addEventListener('click', handleAllFlightsPrevDate);
    }
    if (DOM.allFlightsDateNextBtn) {
        DOM.allFlightsDateNextBtn.addEventListener('click', handleAllFlightsNextDate);
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

    // 일자별 필터 클리어 버튼
    if (DOM.clearDateFilterBtn) {
        DOM.clearDateFilterBtn.addEventListener('click', () => {
            appState.selectedDate = null;
            handleClearDateFilter();
        });
    }

    // 테이블 정렬 (헤더 클릭)
    const sortableHeaders = document.querySelectorAll('th[data-sort]');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const sortColumn = header.getAttribute('data-sort');
            handleTableSort(sortColumn);
        });
    });

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

            // 모든 팝업 닫기
            closeDetailModal();
            closeSingleFlightModal();

            // 뷰 전환
            const targetId = tab.dataset.target;
            document.querySelectorAll('.view-section').forEach(view => {
                view.classList.remove('active');
                view.style.display = 'none';
            });
            const targetView = document.getElementById(targetId);
            targetView.classList.add('active');

            // 뷰별 display 설정
            if (targetId === 'summary-view') {
                targetView.style.display = 'block'; // Summary view는 block
                loadSummaryView();
            } else if (targetId === 'dashboard-view') {
                targetView.style.display = 'flex';
            } else if (targetId === 'period-analysis-view') {
                targetView.style.display = 'flex';
            } else if (targetId === 'csv-management-view') {
                targetView.style.display = 'flex';
            } else if (targetId === 'all-flights-view') {
                targetView.style.display = 'flex';
                // 전체 항공편 데이터 로드 (첫 1회 또는 매번)
                loadAllFlights();
            } else if (targetId === 'aircraft-view') {
                targetView.style.display = 'flex';
                loadAircraftView();
            } else if (targetId === 'test-view') {
                targetView.style.display = 'flex';
                loadTestView();
            } else if (targetId === 'admin-view') {
                targetView.style.display = 'flex';
                // 관리자 라이선스 관리 초기화
                setupAdminLicenseManagement();
            }
        });
    });

    // 요약 탭 새로고침 대조
    const refreshSummaryBtn = document.getElementById('refresh-summary-btn');
    if (refreshSummaryBtn) {
        refreshSummaryBtn.addEventListener('click', loadSummaryView);
    }

    // 요약 탭 시간 오프셋 버튼
    const offsetBtns = document.querySelectorAll('.offset-btn');
    offsetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // 활성 상태 변경
            offsetBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // 데이터 로드
            loadSummaryView();
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
                closeDetailModal();
            });
        }

        // 모달 외부 클릭 시 닫기
        window.addEventListener('click', (event) => {
            if (event.target === detailModal) {
                closeDetailModal();
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

    // ===== 새로운 헤더 날짜 조회 UI 이벤트 리스너 =====
    // 날짜 선택 입력
    const datePicker = document.getElementById('date-picker');
    if (datePicker) {
        datePicker.addEventListener('change', (e) => {
            appState.selectedDate = e.target.value;
            handleDashboardDateChange();
        });
    }

    // 이전 날짜 버튼
    const prevDateBtn = document.getElementById('date-prev-btn');
    if (prevDateBtn) {
        prevDateBtn.addEventListener('click', () => {
            if (appState.availableDates && appState.availableDates.length > 0) {
                const currentDate = appState.selectedDate || appState.availableDates[0];
                const currentIndex = appState.availableDates.indexOf(currentDate);
                if (currentIndex > 0) {
                    appState.selectedDate = appState.availableDates[currentIndex - 1];
                    if (datePicker) datePicker.value = appState.selectedDate;
                    handleDashboardDateChange();
                }
            }
        });
    }

    // 다음 날짜 버튼
    const nextDateBtn = document.getElementById('date-next-btn');
    if (nextDateBtn) {
        nextDateBtn.addEventListener('click', () => {
            if (appState.availableDates && appState.availableDates.length > 0) {
                const currentDate = appState.selectedDate || appState.availableDates[0];
                const currentIndex = appState.availableDates.indexOf(currentDate);
                if (currentIndex < appState.availableDates.length - 1) {
                    appState.selectedDate = appState.availableDates[currentIndex + 1];
                    if (datePicker) datePicker.value = appState.selectedDate;
                    handleDashboardDateChange();
                }
            }
        });
    }

    // 기간 분석 탭 - 조회 버튼
    const periodQueryBtn = document.getElementById('period-query-btn');
    if (periodQueryBtn) {
        periodQueryBtn.addEventListener('click', handlePeriodAnalysisQuery);
    }
    const periodQuick7Btn = document.getElementById('period-quick-7d');
    if (periodQuick7Btn) {
        periodQuick7Btn.addEventListener('click', () => handlePeriodQuickRange(7));
    }
    const periodQuick14Btn = document.getElementById('period-quick-14d');
    if (periodQuick14Btn) {
        periodQuick14Btn.addEventListener('click', () => handlePeriodQuickRange(14));
    }
    const periodQuick30Btn = document.getElementById('period-quick-30d');
    if (periodQuick30Btn) {
        periodQuick30Btn.addEventListener('click', () => handlePeriodQuickRange(30));
    }
    const periodResetBtn = document.getElementById('period-reset-btn');
    if (periodResetBtn) {
        periodResetBtn.addEventListener('click', handlePeriodReset);
    }

    // ===== CSV 관리 탭 파일 업로드 로직 =====
    const csvFileInput = document.getElementById('csv-file-input');
    const csvUploadBtn = document.getElementById('csv-upload-btn');
    const csvRemoveFileBtn = document.getElementById('csv-remove-file');
    const csvDropZone = document.getElementById('csv-drop-zone');
    const csvSelectedFile = document.getElementById('csv-selected-file');
    const csvFilename = document.getElementById('csv-filename');
    const csvStatus = document.getElementById('csv-status');
    const csvDeleteDateBtn = document.getElementById('csv-delete-date-btn');
    const csvDeleteAllBtn = document.getElementById('csv-delete-all-btn');

    if (csvFileInput) {
        // 파일 선택 이벤트
        csvFileInput.addEventListener('change', handleCsvFileSelect);

        // 드래그 앤 드롭
        if (csvDropZone) {
            csvDropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                csvDropZone.style.borderColor = '#2980b9';
                csvDropZone.style.background = '#e3f2fd';
            });
            csvDropZone.addEventListener('dragleave', () => {
                csvDropZone.style.borderColor = '#3498db';
                csvDropZone.style.background = '#f0f7ff';
            });
            csvDropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                csvDropZone.style.borderColor = '#3498db';
                csvDropZone.style.background = '#f0f7ff';
                if (e.dataTransfer.files.length) {
                    csvFileInput.files = e.dataTransfer.files;
                    handleCsvFileSelect();
                }
            });
        }
    }

    if (csvUploadBtn) {
        csvUploadBtn.addEventListener('click', handleCsvFileUpload);
    }

    if (csvRemoveFileBtn) {
        csvRemoveFileBtn.addEventListener('click', () => {
            csvFileInput.value = '';
            csvSelectedFile.style.display = 'none';
            csvUploadBtn.disabled = true;
            csvStatus.innerHTML = '';
        });
    }

    // 샘플 CSV 다운로드
    const downloadSampleCsvBtn = document.getElementById('download-sample-csv');
    if (downloadSampleCsvBtn) {
        downloadSampleCsvBtn.addEventListener('click', downloadSampleCSV);
        // 호버 효과
        downloadSampleCsvBtn.addEventListener('mouseover', () => {
            downloadSampleCsvBtn.style.background = '#2980b9';
        });
        downloadSampleCsvBtn.addEventListener('mouseout', () => {
            downloadSampleCsvBtn.style.background = '#3498db';
        });
    }

    if (csvDeleteDateBtn) {
        csvDeleteDateBtn.addEventListener('click', () => {
            showCsvDeleteModal('date');
        });
    }

    if (csvDeleteAllBtn) {
        csvDeleteAllBtn.addEventListener('click', () => {
            showCsvDeleteModal('all');
        });
    }

    // ===== 삭제 기능 =====
    const cliDeleteDateBtn = document.getElementById('cli-delete-date-btn');
    const cliDeleteAllBtn = document.getElementById('cli-delete-all-btn');
    const deleteModal = document.getElementById('delete-modal');
    const deleteConfirmBtn = document.getElementById('delete-confirm-btn');
    const deleteCancelBtn = document.getElementById('delete-cancel-btn');
    const deleteTargetDate = document.getElementById('delete-target-date');
    const deleteDatePicker = document.getElementById('delete-date-picker-container');
    const deleteModalTitle = document.getElementById('delete-modal-title');
    const deleteModalMessage = document.getElementById('delete-modal-message');

    let deleteType = null;  // 'date' 또는 'all'

    if (cliDeleteDateBtn) {
        cliDeleteDateBtn.addEventListener('click', () => {
            deleteType = 'date';
            deleteModalTitle.textContent = '입력 일자별 삭제';
            deleteModalMessage.textContent = '삭제할 날짜를 선택해주세요. 해당 날짜의 데이터가 모두 삭제됩니다.';
            deleteDatePicker.style.display = 'block';
            deleteModal.style.display = 'flex';
            deleteTargetDate.value = '';
        });
    }

    if (cliDeleteAllBtn) {
        cliDeleteAllBtn.addEventListener('click', () => {
            deleteType = 'all';
            deleteModalTitle.textContent = '전체 데이터 삭제';
            deleteModalMessage.textContent = '⚠️ 모든 데이터가 삭제됩니다. 이 작업은 되돌릴 수 없습니다!';
            deleteDatePicker.style.display = 'none';
            deleteModal.style.display = 'flex';
        });
    }

    if (deleteConfirmBtn) {
        deleteConfirmBtn.addEventListener('click', async () => {
            if (deleteType === 'date' && !deleteTargetDate.value) {
                showCliStatus('날짜를 선택해주세요', 'error');
                return;
            }

            const cliWarningMessage = deleteType === 'date'
                ? `${deleteTargetDate.value} 날짜의 데이터를 삭제합니다. 계속하시겠습니까?`
                : '모든 데이터를 삭제합니다. 이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?';
            if (!window.confirm(cliWarningMessage)) {
                return;
            }

            deleteModal.style.display = 'none';
            await handleDatabaseDelete(deleteType, deleteTargetDate.value);
        });
    }

    if (deleteCancelBtn) {
        deleteCancelBtn.addEventListener('click', () => {
            deleteModal.style.display = 'none';
            deleteType = null;
        });
    }

    // 모달 배경 클릭으로 닫기
    if (deleteModal) {
        deleteModal.addEventListener('click', (e) => {
            if (e.target === deleteModal) {
                deleteModal.style.display = 'none';
                deleteType = null;
            }
        });
    }
}

/**
 * 기간 분석 탭 조회 버튼 클릭
 */
async function handlePeriodAnalysisQuery() {
    const startInput = document.getElementById('period-start-date');
    const endInput = document.getElementById('period-end-date');
    const queryBtn = document.getElementById('period-query-btn');

    const startDate = startInput?.value;
    const endDate = endInput?.value;

    if (!startDate || !endDate) {
        setPeriodStatus('시작일과 종료일을 모두 선택하세요.', 'error');
        return;
    }

    const start = new Date(startDate);
    const end = new Date(endDate);

    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        setPeriodStatus('유효한 날짜를 선택하세요.', 'error');
        return;
    }

    if (start > end) {
        setPeriodStatus('종료일은 시작일보다 빠를 수 없습니다.', 'error');
        return;
    }

    const diffDays = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;
    if (diffDays > PERIOD_ANALYSIS_MAX_DAYS) {
        setPeriodStatus(`최대 ${PERIOD_ANALYSIS_MAX_DAYS}일까지 조회할 수 있습니다.`, 'error');
        return;
    }

    try {
        setPeriodStatus('기간 데이터를 조회하는 중입니다...', 'loading');
        if (queryBtn) {
            queryBtn.disabled = true;
        }

        const minOverlap = appState?.filters?.min_overlap || 2;
        const response = await api.getPeriodAnalysis(startDate, endDate, minOverlap);

        if (!response || response.status !== 'success') {
            throw new Error(response?.message || '기간 분석 데이터를 불러오지 못했습니다.');
        }

        renderPeriodAnalysis(response.data || {});
        setPeriodStatus(`총 ${diffDays}일 범위의 데이터를 업데이트했습니다.`, 'success');
    } catch (error) {
        console.error('기간 분석 조회 실패:', error);
        setPeriodStatus(error.message || '기간 분석 데이터를 불러오지 못했습니다.', 'error');
    } finally {
        if (queryBtn) {
            queryBtn.disabled = false;
        }
    }
}

function setPeriodStatus(message, type = 'info') {
    const statusEl = document.getElementById('period-status');
    if (!statusEl) return;

    statusEl.textContent = message || '';
    statusEl.className = `period-status ${type}`;
    if (!message) {
        statusEl.classList.add('hidden');
    } else {
        statusEl.classList.remove('hidden');
    }
}

function renderPeriodAnalysis(data = {}) {
    updatePeriodKpis(data.kpis || {});
    renderPeriodLevelBreakdown(data.levels || {});
    renderPeriodDailyChart(data.daily_levels || {});
    renderPeriodHeatmap(data.hourly_heatmap || {});
    renderPeriodTopList(
        'period-route-toplist',
        data.routes || [],
        (item) => `${item.dept || '-'} → ${item.dest || '-'}`
    );
    renderPeriodTopList(
        'period-airline-toplist',
        data.airlines || [],
        (item) => `${item.airline_a || '-'} · ${item.airline_b || '-'}`
    );
    renderPeriodDailyTable(data.daily_rows || []);
}

function updatePeriodKpis(kpis = {}) {
    const totalFlightsEl = document.getElementById('period-total-flights');
    const detectionRateEl = document.getElementById('period-detection-rate');
    const rateGradeEl = document.getElementById('period-rate-grade');
    const peakHourEl = document.getElementById('period-peak-hour');
    const peakDescEl = document.getElementById('period-peak-desc');

    if (totalFlightsEl) {
        totalFlightsEl.textContent = formatNumber(kpis.total_flights);
    }
    if (detectionRateEl) {
        detectionRateEl.textContent = formatPercent(kpis.detection_rate);
    }
    if (rateGradeEl) {
        const countText = kpis.detection_count ? ` · ${formatNumber(kpis.detection_count)}건` : '';
        rateGradeEl.textContent = kpis.rate_grade ? `${kpis.rate_grade}${countText}` : '-';
    }
    if (peakHourEl) {
        if (kpis.top_peak_hours && kpis.top_peak_hours.length > 0) {
            // Top 1, 2 표시
            const peaks = kpis.top_peak_hours.map(p => `${p.hour}:00`).join(', ');
            peakHourEl.textContent = peaks;
            peakHourEl.style.fontSize = kpis.top_peak_hours.length > 1 ? '24px' : '32px'; // 글자 크기 조정
        } else {
            peakHourEl.textContent = kpis.peak_hour ? `${kpis.peak_hour}:00` : '-';
        }
    }
    if (peakDescEl) {
        peakDescEl.textContent = (kpis.top_peak_hours && kpis.top_peak_hours.length > 0)
            ? '가장 많은 겹침이 발생한 상위 시간대'
            : (kpis.peak_hour ? '가장 많은 겹침이 발생한 시간' : '데이터 없음');
    }
}

function renderPeriodLevelBreakdown(levels = {}) {
    const container = document.getElementById('period-level-breakdown');
    if (!container) return;

    const hasData = Object.keys(levels).length > 0;
    if (!hasData) {
        container.innerHTML = '<li>데이터 없음 <span>-</span></li>';
        return;
    }

    container.innerHTML = PERIOD_LEVEL_ORDER.map(level => {
        const label = getLevelLabel(level);
        const count = formatNumber(levels[level] || 0);
        return `<li>${label} <span>${count}</span></li>`;
    }).join('');
}

function renderPeriodDailyChart(dailyLevels = {}) {
    const container = document.getElementById('period-daily-chart');
    if (!container) return;

    const labels = Object.keys(dailyLevels).sort();

    if (!labels.length) {
        if (periodDailyChartInstance) {
            periodDailyChartInstance.destroy();
            periodDailyChartInstance = null;
        }
        container.innerHTML = '<div class="chart-empty">데이터가 없습니다.</div>';
        return;
    }

    let canvas = container.querySelector('canvas');
    if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'period-daily-chart-canvas';
        container.innerHTML = '';
        container.appendChild(canvas);
    }

    const datasets = PERIOD_LEVEL_ORDER.map(level => ({
        label: getLevelLabel(level),
        data: labels.map(date => dailyLevels[date]?.[level] || 0),
        backgroundColor: getLevelColor(level),
        borderWidth: 0,
        stack: 'levels'
    }));

    if (periodDailyChartInstance) {
        periodDailyChartInstance.destroy();
    }

    if (typeof Chart === 'undefined') {
        container.innerHTML = '<div class="chart-empty">차트 라이브러리가 로드되지 않았습니다.</div>';
        return;
    }

    const ctx = canvas.getContext('2d');
    periodDailyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function renderPeriodHeatmap(heatmapData = {}) {
    const container = document.getElementById('period-heatmap');
    if (!container) return;

    const dates = Object.keys(heatmapData).sort();
    if (!dates.length) {
        container.innerHTML = '<div class="chart-empty">데이터가 없습니다.</div>';
        return;
    }

    const hours = Array.from({ length: 24 }, (_, idx) => idx.toString().padStart(2, '0'));
    let maxValue = 0;
    dates.forEach(date => {
        const hourly = heatmapData[date] || {};
        Object.values(hourly).forEach(count => {
            maxValue = Math.max(maxValue, count);
        });
    });

    const table = document.createElement('table');
    table.className = 'heatmap-table';
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headerRow.innerHTML = `<th>날짜 / 시간</th>${hours.map(h => `<th>${h}</th>`).join('')}`;
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    dates.forEach(date => {
        const row = document.createElement('tr');
        const titleCell = document.createElement('td');
        titleCell.textContent = date;
        row.appendChild(titleCell);

        hours.forEach(hour => {
            const cell = document.createElement('td');
            const value = heatmapData[date]?.[hour] || 0;
            cell.className = 'heatmap-cell';
            const ratio = maxValue ? value / maxValue : 0;
            cell.style.backgroundColor = getHeatmapColor(value, maxValue);
            cell.style.color = ratio > 0.6 ? '#ffffff' : '#2c3e50';
            cell.title = `${date} ${hour}:00 · ${value}건`;
            cell.textContent = value > 0 ? value : '';
            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });

    table.appendChild(tbody);
    container.innerHTML = '';
    container.appendChild(table);
}

function renderPeriodTopList(targetId, items, labelBuilder, suffix = '건') {
    const target = document.getElementById(targetId);
    if (!target) return;

    if (!items || !items.length) {
        target.innerHTML = '<li class="placeholder-cell">데이터가 없습니다.</li>';
        return;
    }

    target.innerHTML = items.map((item, index) => {
        const label = labelBuilder ? labelBuilder(item, index) : '';
        const value = formatNumber(item.count);
        return `<li><div class="toplist-label">${label}</div><div class="toplist-value">${value}${suffix}</div></li>`;
    }).join('');
}

function renderPeriodDailyTable(rows = []) {
    const tbody = document.getElementById('period-comparison-table');
    if (!tbody) return;

    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="placeholder-cell">기간을 선택하고 조회를 눌러 데이터를 확인하세요.</td></tr>';
        return;
    }

    const sortedRows = [...rows].sort((a, b) => a.date.localeCompare(b.date));

    tbody.innerHTML = sortedRows.map(row => {
        const rate = formatPercent(row.detection_rate, '0.0%');
        const peakHour = row.peak_hour ? `${row.peak_hour}:00` : '-';
        const dominant = getLevelLabel(row.dominant_level);
        return `
            <tr>
                <td>${row.date}</td>
                <td>${formatNumber(row.flights)}</td>
                <td>${formatNumber(row.detections)}</td>
                <td>${rate}</td>
                <td>${peakHour}</td>
                <td>${dominant}</td>
            </tr>
        `;
    }).join('');
}

function formatNumber(value, fallback = '-') {
    if (value === null || value === undefined) {
        return fallback;
    }
    const numberValue = Number(value);
    if (Number.isNaN(numberValue)) {
        return fallback;
    }
    return numberValue.toLocaleString('en-US');
}

function formatPercent(value, fallback = '0.0%') {
    if (value === null || value === undefined) {
        return fallback;
    }
    const numberValue = Number(value);
    if (Number.isNaN(numberValue)) {
        return fallback;
    }
    return `${numberValue.toFixed(2)}%`;
}

function getLevelLabel(level) {
    if (!level) return '-';
    if (level.startsWith('LEVEL_')) {
        return `L${level.split('_')[1]}`;
    }
    return level;
}

function getLevelColor(level) {
    switch (level) {
        case 'LEVEL_5':
            return '#c0392b';
        case 'LEVEL_4':
            return '#e67e22';
        case 'LEVEL_3':
            return '#f1c40f';
        default:
            return '#95a5a6';
    }
}

function getHeatmapColor(value, max) {
    if (!max || value <= 0) {
        return '#f6f8fa';
    }
    const ratio = value / max;
    const start = [255, 235, 238];
    const end = [211, 47, 47];
    const color = start.map((startChannel, idx) => {
        const endChannel = end[idx];
        return Math.round(startChannel + (endChannel - startChannel) * ratio);
    });
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

function handlePeriodQuickRange(days) {
    const endInput = document.getElementById('period-end-date');
    const startInput = document.getElementById('period-start-date');
    if (!startInput || !endInput) return;

    const today = new Date();
    const endDate = new Date(today);
    const startDate = new Date(today);
    startDate.setDate(endDate.getDate() - (days - 1));

    startInput.value = formatDateInput(startDate);
    endInput.value = formatDateInput(endDate);
    setPeriodStatus(`${days}일 범위를 선택했습니다. 조회를 눌러 데이터를 확인하세요.`, 'info');
}

function handlePeriodReset() {
    const startInput = document.getElementById('period-start-date');
    const endInput = document.getElementById('period-end-date');
    if (startInput) startInput.value = '';
    if (endInput) endInput.value = '';
    clearPeriodInsights();
    setPeriodStatus('기간을 다시 선택해주세요.', 'info');
}

function clearPeriodInsights() {
    updatePeriodKpis({});
    renderPeriodLevelBreakdown({});
    renderPeriodDailyChart({});
    renderPeriodHeatmap({});
    renderPeriodTopList('period-route-toplist', []);
    renderPeriodTopList('period-airline-toplist', []);
    renderPeriodDailyTable([]);
}

function formatDateInput(date) {
    const year = date.getFullYear();
    const month = `${date.getMonth() + 1}`.padStart(2, '0');
    const day = `${date.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
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
    try {
        // 시작일과 종료일 가져오기
        const startDate = DOM.startDatePicker?.value;
        const endDate = DOM.endDatePicker?.value;

        if (!startDate || !endDate) {
            showMessage(DOM.simulationStatus, '날짜를 선택하세요.', 'warning');
            return;
        }

        console.log(`범위 조회: ${startDate} ~ ${endDate}`);

        // 범위 조회를 위해 쿼리 파라미터 생성
        const params = {
            start_date: startDate,
            end_date: endDate
        };

        // API에서 범위 데이터 조회
        const url = `${API_BASE_URL}/statistics/detailed?start_date=${params.start_date}&end_date=${params.end_date}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`API 오류: ${response.status}`);

        const result = await response.json();
        if (result.status !== 'success') throw new Error(result.message);

        // 상태 업데이트
        appState.selectedDateRange = {
            start: startDate,
            end: endDate
        };

        // 데이터 표시
        const statistics = result.data;
        const coexistences = statistics.recent_similarities || [];

        // 범위 조회 시 total_similarities를 전체 결과 개수로 재계산
        // (백엔드에서 필터링이 제대로 안 될 때 프론트엔드에서 보정)
        if (statistics.pagination && statistics.pagination.total_count !== undefined) {
            // 페이지네이션이 있으면 전체 개수 사용
            statistics.total_similarities = statistics.pagination.total_count;
        } else if (coexistences.length > 0) {
            // 페이지네이션이 없으면 현재 개수 사용
            statistics.total_similarities = coexistences.length;
        }

        displayTableResults(coexistences);

        // 결과 개수 업데이트
        const resultCount = document.getElementById('result-count');
        if (resultCount) {
            resultCount.textContent = `결과: ${coexistences.length}개`;
        }

        // 차트 업데이트
        if (typeof updateCharts === 'function') {
            updateCharts(statistics);
        }

        // 통계 카드 업데이트
        updateStatisticsUI(statistics);

        // 일자별 통계 아코디언 표시 (범위 조회 시)
        if (statistics.statistics_by_date && Object.keys(statistics.statistics_by_date).length > 0) {
            displayDailyStatisticsAccordion(statistics.statistics_by_date);
        } else {
            // 범위 조회가 아니면 아코디언 숨김
            const accordionDiv = document.getElementById('daily-statistics-accordion');
            if (accordionDiv) {
                accordionDiv.style.display = 'none';
            }
        }

        // 결과 섹션 표시 (범위 조회 시 유사호출 목록 표시)
        const resultsSection = document.querySelector('.results-section');
        if (resultsSection) {
            resultsSection.style.display = 'block';
            // 결과 섹션으로 스크롤 (사용자가 결과를 쉽게 볼 수 있도록)
            setTimeout(() => {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 300);
        }

        // 페이지네이션 정보 업데이트 (백엔드에서 받은 정보 사용)
        if (statistics.pagination) {
            appState.pagination.page = statistics.pagination.current_page || 1;
            appState.pagination.totalPages = statistics.pagination.total_pages || 1;
        } else {
            // 페이지네이션 정보가 없으면 기본값 설정
            appState.pagination.page = 1;
            appState.pagination.totalPages = 1;
        }
        updatePaginationUI();

        // 애니메이션 상태 저장 (페이지네이션 네비게이션 시 사용)
        appState.simulationResults = {
            coexistences: coexistences,
            statistics: statistics
        };

        showMessage(DOM.simulationStatus, `${startDate} ~ ${endDate} 결과를 조회했습니다.`, 'success');

    } catch (error) {
        console.error('범위 조회 오류:', error);
        showMessage(DOM.simulationStatus, `조회 실패: ${error.message}`, 'error');
    }
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
        console.log(`달력에서 선택: ${selectedDate}`);
        // 자동으로 단순 결과 조회 실행 (버튼 클릭 불필요)
        handleViewResults();
    }
}

/**
 * 빠른 날짜 선택: 오늘
 */
function handleQuickDateToday() {
    const today = new Date();
    const dateString = today.toISOString().split('T')[0]; // YYYY-MM-DD 형식

    // 시작일과 종료일을 오늘로 설정
    if (DOM.startDatePicker) {
        DOM.startDatePicker.value = dateString;
    }
    if (DOM.endDatePicker) {
        DOM.endDatePicker.value = dateString;
    }

    // 기간 표시 업데이트
    updateDateRangeDisplay();

    // 상태 업데이트
    appState.selectedDate = dateString;

    // 자동으로 조회 실행
    handleViewResults();

    console.log('[빠른 선택] 오늘:', dateString);
}

/**
 * 빠른 날짜 선택: 어제
 */
function handleQuickDateYesterday() {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const dateString = yesterday.toISOString().split('T')[0]; // YYYY-MM-DD 형식

    // 시작일과 종료일을 어제로 설정
    if (DOM.startDatePicker) {
        DOM.startDatePicker.value = dateString;
    }
    if (DOM.endDatePicker) {
        DOM.endDatePicker.value = dateString;
    }

    // 기간 표시 업데이트
    updateDateRangeDisplay();

    // 상태 업데이트
    appState.selectedDate = dateString;

    // 자동으로 조회 실행
    handleViewResults();

    console.log('[빠른 선택] 어제:', dateString);
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
                    // 진행률과 처리 건수 함께 표시
                    const buildText = progress.total && progress.processed !== undefined
                        ? `${progress.percent}% (${progress.processed.toLocaleString()}/${progress.total.toLocaleString()}건)`
                        : `${progress.percent}%`;
                    progressPercent.textContent = buildText;
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

    deleteTypeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'date') {
                deleteDateSection.style.display = 'block';
            } else {
                deleteDateSection.style.display = 'none';
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
        const deleteDatePicker = document.getElementById('dashboard-delete-date-picker');
        const deleteBtn = document.getElementById('delete-db-btn');

        let deleteType = deleteAllRadio.checked ? 'all' : 'date';
        let selectedDate = deleteByDateRadio.checked ? deleteDatePicker.value : null;

        // 검증
        if (deleteType === 'date' && !selectedDate) {
            alert('삭제할 일자를 선택해주세요.');
            return;
        }

        // ===== 1단계 확인: 작업 내용 설명 =====
        let confirmMessage1 = '';
        if (deleteType === 'all') {
            confirmMessage1 = '⚠️ 전체 데이터베이스 삭제\n\n' +
                '다음 데이터가 영구적으로 삭제됩니다:\n' +
                '• 모든 항공편 정보\n' +
                '• 모든 유사호출 데이터\n' +
                '• 모든 통계 정보\n\n' +
                '이 작업은 되돌릴 수 없습니다.\n\n' +
                '계속하시겠습니까?';
        } else {
            confirmMessage1 = `⚠️ ${selectedDate} 데이터 삭제\n\n` +
                '해당 날짜의 다음 데이터가 삭제됩니다:\n' +
                '• 항공편 정보\n' +
                '• 유사호출 데이터\n\n' +
                '이 작업은 되돌릴 수 없습니다.\n\n' +
                '계속하시겠습니까?';
        }

        if (!confirm(confirmMessage1)) {
            return;
        }

        // ===== 2단계 확인: 텍스트 입력 요구 =====
        const confirmText = prompt(
            '⚠️ 최종 확인\n\n' +
            '정말로 삭제하시려면 아래에 "DELETE"를 입력하세요.\n' +
            '(대소문자 구분 없음)',
            ''
        );

        if (confirmText === null) {
            // 사용자가 취소를 누른 경우
            return;
        }

        if (confirmText.toUpperCase() !== 'DELETE') {
            alert('❌ 삭제가 취소되었습니다.\n올바른 확인 텍스트를 입력하지 않았습니다.');
            return;
        }

        deleteBtn.disabled = true;
        deleteBtn.style.opacity = '0.5';
        deleteBtn.style.cursor = 'not-allowed';

        const statusDiv = document.createElement('div');
        statusDiv.id = 'delete-status';
        deleteBtn.parentNode.insertBefore(statusDiv, deleteBtn);

        showMessage(statusDiv, '🗑️ 삭제 중...', 'loading');

        // API 호출
        const response = await api.deleteDatabase(deleteType, selectedDate);

        if (response.status === 'success') {
            showMessage(statusDiv, '✅ ' + (response.message || '데이터 삭제 완료'), 'success');

            // 2초 후 페이지 새로고침
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showMessage(statusDiv, '❌ ' + (response.message || '삭제 실패'), 'error');
        }
    } catch (error) {
        console.error('DB 삭제 오류:', error);
        const statusDiv = document.getElementById('delete-status') || document.createElement('div');
        showMessage(statusDiv, '❌ 삭제 중 오류 발생', 'error');
    } finally {
        const deleteBtn = document.getElementById('delete-db-btn');
        if (deleteBtn) {
            deleteBtn.disabled = false;
            deleteBtn.style.opacity = '1';
            deleteBtn.style.cursor = 'pointer';
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
 * 테이블 정렬 처리
 */
function handleTableSort(column) {
    if (!appState.simulationResults || !appState.simulationResults.coexistences) {
        return;
    }

    // 같은 컬럼을 클릭하면 방향 반전, 다른 컬럼이면 오름차순으로 시작
    if (appState.tableSortColumn === column) {
        appState.tableSortDirection = appState.tableSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        appState.tableSortColumn = column;
        appState.tableSortDirection = 'asc';
    }

    // 정렬 아이콘 업데이트
    updateSortIcons();

    // 현재 표시 중인 데이터 정렬
    const results = [...appState.simulationResults.coexistences];

    results.sort((a, b) => {
        let valueA, valueB;

        switch (column) {
            case 'callsign1':
                valueA = a.callsign1 || '';
                valueB = b.callsign1 || '';
                break;
            case 'callsign2':
                valueA = a.callsign2 || '';
                valueB = b.callsign2 || '';
                break;
            case 'similarity':
                valueA = a.similarity_level || '';
                valueB = b.similarity_level || '';
                break;
            case 'overlap':
                valueA = a.total_overlap_minutes || 0;
                valueB = b.total_overlap_minutes || 0;
                break;
            default:
                return 0;
        }

        // 문자열 또는 숫자 비교
        if (typeof valueA === 'string') {
            valueA = valueA.toLowerCase();
            valueB = valueB.toLowerCase();
        }

        if (appState.tableSortDirection === 'asc') {
            return valueA > valueB ? 1 : valueA < valueB ? -1 : 0;
        } else {
            return valueA < valueB ? 1 : valueA > valueB ? -1 : 0;
        }
    });

    // 정렬된 결과 표시
    displayTableResults(results);
}

/**
 * 정렬 아이콘 업데이트
 */
function updateSortIcons() {
    const headers = document.querySelectorAll('th[data-sort]');
    headers.forEach(header => {
        const icon = header.querySelector('i');
        const column = header.getAttribute('data-sort');

        if (column === appState.tableSortColumn) {
            // 현재 정렬 중인 컬럼
            if (appState.tableSortDirection === 'asc') {
                icon.className = 'fas fa-sort-up';
                icon.style.opacity = '1';
            } else {
                icon.className = 'fas fa-sort-down';
                icon.style.opacity = '1';
            }
        } else {
            // 정렬되지 않은 컬럼
            icon.className = 'fas fa-sort';
            icon.style.opacity = '0.5';
        }
    });
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
 * 대시보드 날짜 변경 처리 (헤더 날짜 선택기)
 */
async function handleDashboardDateChange() {
    const selectedDate = appState.selectedDate;
    appState.pagination.page = 1; // 페이지 초기화

    console.log('대시보드 날짜 변경:', selectedDate);
    await loadExistingData(1, selectedDate);
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
        // API에 시간대 필터를 포함해서 데이터 재조회 (페이징 제거: 10000개까지 한번에 로드)
        const selectedDate = appState.selectedDate;
        const statsResponse = await api.getStatisticsDetailed(2, 1, 10000, selectedDate, hour);

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
 * 일자별 필터 해제
 */
function handleClearDateFilter() {
    appState.selectedDate = null;

    // 기존 데이터 재조회 (필터 없음)
    loadExistingData(1, null);

    // UI에서 필터 표시 제거
    if (DOM.dateFilterIndicator) {
        DOM.dateFilterIndicator.style.display = 'none';
    }

    console.log('일자별 필터 해제');
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
 * 현재 테이블의 데이터를 CSV로 내보내기 (대시보드용)
 */
function handleExportTableCSV() {
    try {
        if (!appState.simulationResults || !appState.simulationResults.coexistences) {
            alert('내보낼 데이터가 없습니다. 먼저 데이터를 조회하세요.');
            return;
        }

        const coexistences = appState.simulationResults.coexistences;

        // CSV 헤더
        const headers = ['콜사인1', 'EOBD1', 'EOBT1', '출발지1', '도착지1',
            '콜사인2', 'EOBD2', 'EOBT2', '출발지2', '도착지2',
            '유사도레벨', '섹터정보', '총공존시간'];

        // 섹터 정보를 문자열로 변환
        const formatSectorInfo = (sectorOverlaps) => {
            if (!sectorOverlaps || sectorOverlaps.length === 0) return '';
            return sectorOverlaps
                .map(s => `${s.sector}(${s.overlap_start}~${s.overlap_end})`)
                .join(';');
        };

        // CSV 데이터 생성
        const csvRows = coexistences.map(c => [
            c.callsign1 || '',
            c.eobd1 || '',
            c.eobt1 || '',
            c.dept1 || '',
            c.dest1 || '',
            c.callsign2 || '',
            c.eobd2 || '',
            c.eobt2 || '',
            c.dept2 || '',
            c.dest2 || '',
            c.similarity_level || '',
            formatSectorInfo(c.sector_overlaps),
            c.total_overlap_minutes || ''
        ].map(val => {
            // CSV에서 콤마나 따옴표 처리
            val = String(val).replace(/"/g, '""');
            if (val.includes(',') || val.includes('"') || val.includes('\n')) {
                return `"${val}"`;
            }
            return val;
        }).join(','));

        const csvContent = [headers.join(','), ...csvRows].join('\n');
        downloadFile(csvContent, `similarity-results-${new Date().toISOString().split('T')[0]}.csv`, 'text/csv;charset=utf-8;');

        alert(`${coexistences.length}개의 데이터가 CSV로 내보내졌습니다.`);
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

    // 헤더 현재 데이터 정보 업데이트
    if (appState.selectedDate) {
        updateHeaderDataInfo(appState.selectedDate, data.total_flights);
    }

    // 1. 기본 통계 (유사호출 감지, 분석된 항공편)
    if (DOM.statTotalSims) DOM.statTotalSims.textContent = formatNumber(data.total_similarities);
    if (DOM.statTotalFlights) DOM.statTotalFlights.textContent = formatNumber(data.total_flights);

    const totalSimsPercentage = document.getElementById('stat-total-sims-percentage');
    if (totalSimsPercentage) {
        const ratio = data.total_flights > 0
            ? ((data.total_similarities / data.total_flights) * 100).toFixed(1)
            : '0.0';
        totalSimsPercentage.textContent = `${ratio}%`;
    }

    // 동일 날짜 / 크로스 날짜 유사호출 표시
    if (data.same_date_similarities !== undefined) {
        const sameDateElem = document.getElementById('stat-same-date-sims');
        if (sameDateElem) sameDateElem.textContent = formatNumber(data.same_date_similarities);
    }
    if (data.cross_date_similarities !== undefined) {
        const crossDateElem = document.getElementById('stat-cross-date-sims');
        if (crossDateElem) crossDateElem.textContent = formatNumber(data.cross_date_similarities);
    }

    // 2. 필터링된 개수 (섹터 내 공존)
    if (DOM.statFilteredSims) DOM.statFilteredSims.textContent = formatNumber(data.filtered_similarities);

    // 4. 고급 통계 (피크 시간, 최다 빈도 섹터, 평균 공존 시간)
    if (document.getElementById('stat-peak-time')) {
        document.getElementById('stat-peak-time').textContent = data.peak_hour ? `${data.peak_hour}시` : '-';
    }

    // 최다 빈도 섹터 (상위 2개 표시, 한 줄에)
    if (document.getElementById('stat-top-sector')) {
        if (data.top_sectors && data.top_sectors.length > 0) {
            const topSectorsText = data.top_sectors
                .slice(0, 2)
                .map((s) => `<span style="font-weight:bold; color:#f39c12;">${s.sector_name}</span> (${s.count}건)`)
                .join(', ');
            document.getElementById('stat-top-sector').innerHTML = topSectorsText;
        } else {
            document.getElementById('stat-top-sector').textContent = data.top_sector || '-';
        }
    }

    if (document.getElementById('stat-avg-overlap')) {
        document.getElementById('stat-avg-overlap').textContent = data.avg_overlap_minutes ? `${data.avg_overlap_minutes}분` : '0분';
    }

    // 5. 차트 업데이트 (시간대별 공존 현황)
    if (typeof updateCharts === 'function') {
        updateCharts(data);
    }

    // 6. 왼쪽 사이드바 메뉴 업데이트
    if (typeof updateDashboardMenus === 'function') {
        updateDashboardMenus(data);
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

            // EOBD/EOBT 정보 포맷 (있을 경우만)
            const timeInfo1 = [];
            if (coex.eobd1) timeInfo1.push(`EOBD: ${coex.eobd1}`);
            if (coex.eobt1) timeInfo1.push(`EOBT: ${coex.eobt1}`);
            const timeHtml1 = timeInfo1.length > 0 ? `<div style="font-size: 0.75em; color: #7f8c8d; margin-top: 2px;">${timeInfo1.join(' / ')}</div>` : '';

            const timeInfo2 = [];
            if (coex.eobd2) timeInfo2.push(`EOBD: ${coex.eobd2}`);
            if (coex.eobt2) timeInfo2.push(`EOBT: ${coex.eobt2}`);
            const timeHtml2 = timeInfo2.length > 0 ? `<div style="font-size: 0.75em; color: #7f8c8d; margin-top: 2px;">${timeInfo2.join(' / ')}</div>` : '';

            row.innerHTML = `
                <td style="font-weight: bold;">
                    ${coex.callsign1}
                    ${timeHtml1}
                    ${route1}
                </td>
                <td style="font-weight: bold;">
                    ${coex.callsign2}
                    ${timeHtml2}
                    ${route2}
                </td>
                <td style="font-size: 0.9em;">
                    ${formattedLevel}
                </td>
                <td style="font-size: 0.85em; text-align: left;">
                    ${sectorInfo}
                </td>
                <td style="text-align: center; font-weight: bold; color: #667eea;">
                    ${coex.total_overlap_minutes || 0}분
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

function closeDetailModal() {
    const modal = document.getElementById('detail-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * 상세 비교 모달 열기
 */
async function openDetailModal(flightId1, flightId2, callsign1, callsign2) {
    const modal = document.getElementById('detail-modal');
    if (!modal) return;
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


    // EOBT 및 ETA 계산
    const eobt = info.eobt ? info.eobt.substring(0, 5) : '-';
    let eta = '-';

    // ETA: 마지막 웨이포인트 시간 또는 섹터 퇴출 시간
    if (flightData.waypoints && flightData.waypoints.length > 0) {
        const lastWp = flightData.waypoints[flightData.waypoints.length - 1];
        const lastTime = lastWp.estimated_time || lastWp.actual_time;
        if (lastTime) {
            // [v2.1] ETA에 마지막 웨이포인트 이름 포함 (예: DOTOL 13:05)
            eta = `${lastWp.waypoint_name} ${lastTime.substring(0, 5)}`;
        }
    }

    // 1. 기본 정보 렌더링
    const infoHtml = `
        <div class="flight-info-box">
            <strong>${callsign}</strong> (${info.aircraft_type || 'Unknown'})\n
            <span style="color:#666;">
                ${info.dept_airport_cd || '?'} <span style="color:#2c3e50; font-weight:bold; font-size:0.9em;">(${eobt})</span> 
                → 
                ${info.dest_airport_cd || '?'} <span style="color:#2c3e50; font-weight:bold; font-size:0.9em;">(${eta})</span>
            </span><br>
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
                    <td class="chip-cell">
                        <div class="chip-scroll">
                            ${waypointHtml}
                        </div>
                    </td>
                    <td class="chip-cell">
                        <div class="chip-scroll chip-scroll--sectors">
                            ${sectorHtml}
                        </div>
                    </td>
                    <td style="text-align:left; font-size:0.9em;">
                        ${similarityHtml}
                    </td>
                `;

                // 행 클릭 이벤트 추가 - 항공편 상세정보 팝업 열기
                row.style.cursor = 'pointer';
                row.title = '클릭하여 상세 정보 보기';
                row.classList.add('clickable-row');
                row.onclick = (e) => {
                    // 내부 링크나 버튼 클릭은 무시
                    if (e.target.closest('a, button')) return;
                    openSingleFlightModal(f.id, f.callsign);
                };

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
        // 인덱스 정보 업데이트
        if (appState.allFlightsAvailableDates && appState.allFlightsAvailableDates.length > 0) {
            appState.allFlightsDateIndex = appState.allFlightsAvailableDates.indexOf(selectedDate);
        }
        loadAllFlights(1, selectedDate);
    }
}

/**
 * ◀️ 이전 날짜로 이동 (전체 항공편)
 */
async function handleAllFlightsPrevDate() {
    if (appState.allFlightsAvailableDates && appState.allFlightsAvailableDates.length > 0) {
        // 현재 선택된 날짜의 인덱스 찾기
        let currentIndex = appState.allFlightsDateIndex;
        if (currentIndex === -1 && appState.allFlightsSelectedDate) {
            currentIndex = appState.allFlightsAvailableDates.indexOf(appState.allFlightsSelectedDate);
        }

        // 이전 날짜 (Older)
        if (currentIndex > 0) {
            appState.allFlightsDateIndex = currentIndex - 1;
            appState.allFlightsSelectedDate = appState.allFlightsAvailableDates[appState.allFlightsDateIndex];
            updateAllFlightsDateDisplay();
            loadAllFlights(1, appState.allFlightsSelectedDate);
        }
    }
}

/**
 * ▶️ 다음 날짜로 이동 (전체 항공편)
 */
async function handleAllFlightsNextDate() {
    if (appState.allFlightsAvailableDates && appState.allFlightsAvailableDates.length > 0) {
        // 현재 선택된 날짜의 인덱스 찾기
        let currentIndex = appState.allFlightsDateIndex;
        if (currentIndex === -1 && appState.allFlightsSelectedDate) {
            currentIndex = appState.allFlightsAvailableDates.indexOf(appState.allFlightsSelectedDate);
        }

        // 다음 날짜 (Newer)
        if (currentIndex < appState.allFlightsAvailableDates.length - 1) {
            appState.allFlightsDateIndex = currentIndex + 1;
            appState.allFlightsSelectedDate = appState.allFlightsAvailableDates[appState.allFlightsDateIndex];
            updateAllFlightsDateDisplay();
            loadAllFlights(1, appState.allFlightsSelectedDate);
        }
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
            // 날짜순 오름차순 정렬 (Dashboard와 동일하게)
            appState.allFlightsAvailableDates = response.data.sort();
        } else {
            appState.allFlightsAvailableDates = [];
        }

        // 기본값으로 마지막 날짜(가장 최신 날짜) 선택
        if (appState.allFlightsAvailableDates.length > 0) {
            appState.allFlightsDateIndex = appState.allFlightsAvailableDates.length - 1;
            appState.allFlightsSelectedDate = appState.allFlightsAvailableDates[appState.allFlightsDateIndex];
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
    const dropZone = document.getElementById('cli-drop-zone');

    console.log('[CLI] 파일 선택됨:', file.name, file.size, file.type);

    filenameSpan.textContent = file.name;
    selectedFileDiv.style.display = 'flex';
    // 파일 객체를 직접 저장
    fileInput._selectedFile = file;
    runBtn.disabled = false;
    runBtn.style.opacity = '1';
    runBtn.style.cursor = 'pointer';

    // 파일 선택 영역 스타일 변경
    dropZone.style.borderColor = '#27ae60';
    dropZone.style.background = '#f0f7ff';
}

// CLI 파일 제거 처리
function handleCLIFileRemove() {
    const fileInput = document.getElementById('cli-file-input');
    const selectedFileDiv = document.getElementById('cli-selected-file');
    const filenameSpan = document.getElementById('cli-filename');
    const runBtn = document.getElementById('cli-run-btn');
    const dropZone = document.getElementById('cli-drop-zone');

    // 파일 입력 초기화
    fileInput.value = '';
    fileInput._selectedFile = null;

    // UI 초기화
    filenameSpan.textContent = '';
    selectedFileDiv.style.display = 'none';
    runBtn.disabled = true;
    runBtn.style.opacity = '0.6';
    runBtn.style.cursor = 'not-allowed';

    // 파일 선택 영역 스타일 초기화
    dropZone.style.borderColor = '';
    dropZone.style.background = '';

    console.log('[CLI] 파일 제거됨');
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
    const dropZone = document.getElementById('cli-drop-zone');

    filenameSpan.textContent = file.name;
    selectedFileDiv.style.display = 'flex';
    fileInput._selectedFile = file;
    runBtn.disabled = false;
    runBtn.style.opacity = '1';
    runBtn.style.cursor = 'pointer';

    // 파일 선택 영역 스타일 변경
    dropZone.style.borderColor = '#27ae60';
    dropZone.style.background = '#f0f7ff';
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
        const response = await fetch(`${window.location.origin}/api/simulation/run-cli`, {
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
        const response = await fetch(`${window.location.origin}/api/simulation/reset-db`, {
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

    // 파일 제거 버튼
    const cliRemoveFileBtn = document.getElementById('cli-remove-file');
    if (cliRemoveFileBtn) {
        cliRemoveFileBtn.addEventListener('click', handleCLIFileRemove);
    }
}

/**
 * 헤더 현재 데이터 정보 업데이트
 * @param {string} date - 선택된 날짜 (YYYY-MM-DD)
 * @param {number} flightCount - 항공편 수
 */
function updateHeaderDataInfo(date = null, flightCount = 0) {
    const dateSpan = document.getElementById('current-date-info');
    const flightsSpan = document.getElementById('current-flights-info');

    if (!dateSpan || !flightsSpan) return;

    if (date) {
        dateSpan.textContent = date;
        flightsSpan.textContent = flightCount.toLocaleString();
    } else {
        dateSpan.textContent = '데이터 없음';
        flightsSpan.textContent = '-';
    }
}

/**
 * 초기화
 */
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

    // 날짜 범위 초기화 (기본값: 오늘)
    initializeDateRange();

    // 사용 가능한 날짜 로드
    await loadAvailableDates();

    // 유사도 레벨 정의 로드 (필수 - 테이블 렌더링 전에 완료되어야 함)
    console.log('[초기화] 유사도 레벨 정의 로드 중...');
    await loadSimilarityLevels();
    console.log('[초기화] 유사도 레벨 정의 로드 완료:', Object.keys(appState.similarityLevels || {}).length, '개');

    // 전체 항공편 탭의 날짜 목록 로드
    await loadAllFlightsDateList();

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

/**
 * 차트 토글 버튼 이벤트 핸들러
 */
function setupChartToggleButtons() {
    const btnHourly = document.getElementById('btn-hourly-chart');
    const btnDaily = document.getElementById('btn-daily-chart');
    const timeChart = document.getElementById('timeChart');
    const dailyChart = document.getElementById('dailyChart');

    if (!btnHourly || !btnDaily || !timeChart || !dailyChart) {
        console.warn('차트 토글 요소를 찾을 수 없습니다');
        return;
    }

    // 시간대별 차트 버튼 클릭
    btnHourly.addEventListener('click', () => {
        // UI 업데이트
        btnHourly.style.background = '#667eea';
        btnHourly.style.color = 'white';
        btnHourly.style.borderColor = '#667eea';

        btnDaily.style.background = 'white';
        btnDaily.style.color = '#333';
        btnDaily.style.borderColor = '#bdc3c7';

        // 차트 표시/숨김
        timeChart.style.display = 'block';
        dailyChart.style.display = 'none';

        // 활성 상태 표시
        btnHourly.classList.add('active');
        btnDaily.classList.remove('active');

        console.log('시간대별 차트로 전환');
    });

    // 일자별 차트 버튼 클릭
    btnDaily.addEventListener('click', () => {
        // UI 업데이트
        btnDaily.style.background = '#667eea';
        btnDaily.style.color = 'white';
        btnDaily.style.borderColor = '#667eea';

        btnHourly.style.background = 'white';
        btnHourly.style.color = '#333';
        btnHourly.style.borderColor = '#bdc3c7';

        // 차트 표시/숨김
        dailyChart.style.display = 'block';
        timeChart.style.display = 'none';

        // 활성 상태 표시
        btnDaily.classList.add('active');
        btnHourly.classList.remove('active');

        console.log('일자별 차트로 전환');
    });
}

/**
 * 일자별 필터링 함수 (차트 클릭 시)
 */
async function filterByDate(dateStr) {
    try {
        console.log(`일자 필터링: ${dateStr}`);
        appState.selectedDate = dateStr;

        // API에 날짜 필터를 포함해서 데이터 재조회
        const response = await fetch(`/api/statistics/detailed?eobd=${dateStr}`);
        if (!response.ok) throw new Error(`API 오류: ${response.status}`);

        const result = await response.json();
        if (result.status !== 'success') throw new Error(result.message);

        const statistics = result.data;
        const coexistences = statistics.recent_similarities || [];

        console.log(`일자 필터링: ${dateStr} - ${coexistences.length}개 결과`);

        // UI 업데이트 - 올바른 함수명 사용
        displayTableResults(coexistences);

        // 결과 개수 업데이트
        const resultCount = document.getElementById('result-count');
        if (resultCount) {
            resultCount.textContent = `결과: ${coexistences.length}개`;
        }

        // 날짜 필터 인디케이터 표시
        const filterIndicator = document.getElementById('date-filter-indicator');
        const filterValue = document.getElementById('date-filter-value');
        if (filterIndicator && filterValue) {
            filterValue.textContent = dateStr;
            filterIndicator.style.display = 'block';
        }

        // 차트 업데이트
        if (typeof updateCharts === 'function') {
            updateCharts(statistics);
        }

    } catch (error) {
        console.error('일자 필터링 오류:', error);
        alert('일자 필터링 오류: ' + error.message);
    }
}

/**
 * 날짜 범위 초기화 (기본값: 오늘)
 */
function initializeDateRange() {
    const today = new Date();
    const dateString = today.toISOString().split('T')[0]; // YYYY-MM-DD

    // 시작일과 종료일을 오늘로 설정
    if (DOM.startDatePicker) {
        DOM.startDatePicker.value = dateString;
    }
    if (DOM.endDatePicker) {
        DOM.endDatePicker.value = dateString;
    }

    // 기간 표시 업데이트
    updateDateRangeDisplay();

    // 이벤트 리스너 추가
    if (DOM.startDatePicker) {
        DOM.startDatePicker.addEventListener('change', handleStartDateChange);
    }
    if (DOM.endDatePicker) {
        DOM.endDatePicker.addEventListener('change', handleEndDateChange);
    }

    console.log(`[날짜 범위] 초기화 완료 - 시작: ${dateString}, 종료: ${dateString}`);
}

/**
 * 시작일자 변경 핸들러
 */
function handleStartDateChange(event) {
    const startDate = new Date(DOM.startDatePicker.value);
    const endDate = new Date(DOM.endDatePicker.value);

    console.log(`시작일 변경: ${DOM.startDatePicker.value}`);

    // 시작일 > 종료일이면 종료일을 시작일과 같게 설정
    if (startDate > endDate) {
        DOM.endDatePicker.value = DOM.startDatePicker.value;
        console.log(`⚠️ 자동 보정: 종료일을 ${DOM.startDatePicker.value}로 변경`);
    }

    // 기간 표시 업데이트
    updateDateRangeDisplay();

    // 범위 유효성 검사
    const validation = validateDateRange();
    if (!validation.isValid) {
        alert(validation.message);
        return; // 조회하지 않음
    }

    // 자동 조회
    handleViewResults();
}

/**
 * 종료일자 변경 핸들러
 */
function handleEndDateChange(event) {
    const startDate = new Date(DOM.startDatePicker.value);
    const endDate = new Date(DOM.endDatePicker.value);

    console.log(`종료일 변경: ${DOM.endDatePicker.value}`);

    // 종료일 < 시작일이면 시작일을 종료일과 같게 설정
    if (endDate < startDate) {
        DOM.startDatePicker.value = DOM.endDatePicker.value;
        console.log(`⚠️ 자동 보정: 시작일을 ${DOM.endDatePicker.value}로 변경`);
    }

    // 기간 표시 업데이트
    updateDateRangeDisplay();

    // 범위 유효성 검사
    const validation = validateDateRange();
    if (!validation.isValid) {
        alert(validation.message);
        return; // 조회하지 않음
    }

    // 자동 조회
    handleViewResults();
}

/**
 * 날짜 범위 표시 업데이트 및 유효성 검사
 */
function updateDateRangeDisplay() {
    const startDate = new Date(DOM.startDatePicker.value);
    const endDate = new Date(DOM.endDatePicker.value);

    // 범위 계산 (일수)
    const diffTime = Math.abs(endDate - startDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    // 범위 표시
    if (DOM.dateRangeDisplay) {
        DOM.dateRangeDisplay.textContent = `범위: ${diffDays}일`;

        // 범위 색상 변경
        if (diffDays > 7) {
            DOM.dateRangeDisplay.style.color = '#d32f2f';
            DOM.dateRangeDisplay.style.fontWeight = 'bold';
        } else {
            DOM.dateRangeDisplay.style.color = '#666';
            DOM.dateRangeDisplay.style.fontWeight = 'normal';
        }
    }

    // 경고 표시
    if (DOM.dateRangeWarning) {
        if (diffDays > 7) {
            DOM.dateRangeWarning.style.display = 'inline';
        } else {
            DOM.dateRangeWarning.style.display = 'none';
        }
    }
}

/**
 * 날짜 범위 유효성 검사 (최대 7일)
 */
function validateDateRange() {
    const startDate = new Date(DOM.startDatePicker.value);
    const endDate = new Date(DOM.endDatePicker.value);

    // 범위 계산 (일수)
    const diffTime = Math.abs(endDate - startDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays > 7) {
        console.warn(`⚠️ 범위 초과: ${diffDays}일 (최대 7일 가능)`);
        return {
            isValid: false,
            message: `최대 7일까지만 조회 가능합니다. (현재: ${diffDays}일)`,
            days: diffDays
        };
    }

    return {
        isValid: true,
        message: `범위: ${diffDays}일`,
        days: diffDays
    };
}

/**
 * 일자별 통계 아코디언 표시
 */
function displayDailyStatisticsAccordion(statisticsByDate) {
    const accordionDiv = document.getElementById('daily-statistics-accordion');
    const itemsContainer = document.getElementById('accordion-items');

    if (!accordionDiv || !itemsContainer) return;

    // 날짜 정렬
    const dates = Object.keys(statisticsByDate).sort();
    const totalDates = dates.length;

    // 날짜를 한국식 형식으로 변환하는 함수
    const formatKoreanDate = (dateStr) => {
        const [year, month, day] = dateStr.split('-');
        return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일`;
    };

    // 각 날짜별 아코디언 항목 생성
    let html = '';
    dates.forEach((date, index) => {
        const stats = statisticsByDate[date];
        const itemNumber = index + 1;
        const isFirst = index === 0;
        const koreanDate = formatKoreanDate(date);

        // 아코디언 헤더
        html += `
            <div style="margin-bottom: 8px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden;">
                <div class="accordion-header" onclick="toggleAccordion(this)"
                     style="padding: 12px 16px; background: #f5f5f5; cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none;">
                    <div style="display: flex; align-items: center; gap: 16px; flex: 1;">
                        <span style="font-size: 18px; color: #667eea; font-weight: bold;">${isFirst ? '▼' : '▶'}</span>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-weight: bold; color: #333; font-size: 14px;">${koreanDate}</span>
                            <span style="font-size: 12px; background: #667eea; color: white; padding: 4px 10px; border-radius: 12px; font-weight: 600;">
                                ${itemNumber}/${totalDates}
                            </span>
                        </div>
                        <span style="font-size: 12px; background: #e74c3c; color: white; padding: 4px 10px; border-radius: 12px;">${stats.count}건</span>
                    </div>
                </div>

                <!-- 아코디언 콘텐츠 -->
                <div class="accordion-content" style="display: ${isFirst ? 'block' : 'none'}; padding: 16px; background: white; border-top: 1px solid #ddd;">
                    <!-- 위험도 분포 (체크박스 필터) -->
                    <div style="margin-bottom: 16px;">
                        <h4 style="margin: 0 0 8px 0; font-size: 12px; color: #666; font-weight: bold;">위험도 분포 (클릭하여 필터)</h4>
                        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                            ${Object.entries(stats.risk_distribution).map(([level, count]) => `
                                <label style="display: flex; align-items: center; gap: 6px; font-size: 12px; cursor: pointer; user-select: none;">
                                    <input type="checkbox" class="risk-filter-checkbox" data-level="${level}" checked
                                        style="cursor: pointer; width: 14px; height: 14px;">
                                    <span style="width: 8px; height: 8px; background: #667eea; border-radius: 2px;"></span>
                                    <span>${level}: ${count}건</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>

                    <!-- 항공사 분포 -->
                    <div>
                        <h4 style="margin: 0 0 8px 0; font-size: 12px; color: #666; font-weight: bold;">항공사 (상위 5개)</h4>
                        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                            ${stats.top_airlines.map((airlineObj) => {
            const airline = Object.keys(airlineObj)[0];
            const count = airlineObj[airline];
            return `
                                    <div style="display: flex; align-items: center; gap: 6px; font-size: 12px;">
                                        <span style="width: 8px; height: 8px; background: #e74c3c; border-radius: 2px;"></span>
                                        <span>${airline}: ${count}건</span>
                                    </div>
                                `;
        }).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    itemsContainer.innerHTML = html;
    accordionDiv.style.display = 'block';

    // 위험도 필터 체크박스 이벤트 리스너 추가
    const riskCheckboxes = document.querySelectorAll('.risk-filter-checkbox');
    riskCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            applyRiskFilters();
        });
    });
}

/**
 * 위험도 필터 적용
 */
function applyRiskFilters() {
    // 선택된 위험도 레벨 수집
    const selectedLevels = Array.from(document.querySelectorAll('.risk-filter-checkbox:checked'))
        .map(cb => cb.getAttribute('data-level'));

    console.log('필터 적용:', {
        선택된레벨: selectedLevels,
        전체데이터: appState.simulationResults?.coexistences?.length
    });

    // 시뮬레이션 결과가 없으면 반환
    if (!appState.simulationResults || !appState.simulationResults.coexistences) {
        console.warn('시뮬레이션 결과가 없습니다');
        return;
    }

    // 선택된 위험도에 해당하는 데이터만 필터링
    const filteredResults = appState.simulationResults.coexistences.filter(coex => {
        const level = coex.similarity_level;
        return selectedLevels.includes(level);
    });

    console.log('필터링 결과:', {
        선택된개수: filteredResults.length,
        제외된개수: appState.simulationResults.coexistences.length - filteredResults.length
    });

    // 필터된 결과로 테이블 업데이트
    displayTableResults(filteredResults);

    // 결과 개수 업데이트
    const resultCount = document.getElementById('result-count');
    if (resultCount) {
        resultCount.textContent = `결과: ${filteredResults.length}개`;
    }

    // 필터된 데이터로 통계 생성 및 업데이트
    if (filteredResults.length > 0) {
        const filteredStats = generateStatisticsFromResults(filteredResults);
        updateStatisticsUI(filteredStats);

        // 차트 업데이트
        if (typeof updateCharts === 'function') {
            updateCharts(filteredStats);
        }
    } else {
        // 필터된 결과가 없으면 초기화
        const resultCount = document.getElementById('result-count');
        if (resultCount) {
            resultCount.textContent = '결과: 0개';
        }
    }

    // 페이지네이션 초기화
    appState.pagination.page = 1;
    updatePaginationUI();

    // 필터 적용 후 차트 및 결과 영역으로 스크롤
    setTimeout(() => {
        const chartsSection = document.querySelector('.charts-section');
        if (chartsSection) {
            chartsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 300);
}

/**
 * 필터된 결과에서 통계 생성
 */
function generateStatisticsFromResults(results) {
    // 원본 데이터
    const originalStats = appState.simulationResults?.statistics || {};

    // 필터된 결과에서 unique aircraft 수 계산
    const uniqueAircraft = new Set();
    results.forEach(sim => {
        if (sim.callsign1) uniqueAircraft.add(sim.callsign1);
        if (sim.callsign2) uniqueAircraft.add(sim.callsign2);
    });

    // 기본 통계
    const stats = {
        total_similarities: results.length,
        total_flights: uniqueAircraft.size,
        filtered_similarities: results.length,

        // 피크 시간 계산
        peak_hour: calculatePeakHour(results),

        // 평균 공존 시간
        avg_overlap_minutes: calculateAverageOverlap(results),

        // 최다 빈도 섹터
        top_sectors: calculateTopSectors(results),
        top_sector: '',

        // 시간대별 분포
        hourly_distribution_by_date: calculateHourlyDistribution(results),

        // 최근 유사호출
        recent_similarities: results,

        // 페이지네이션
        pagination: {
            current_page: 1,
            total_pages: Math.ceil(results.length / 20),
            per_page: 20,
            total_count: results.length
        }
    };

    // top_sector 설정
    if (stats.top_sectors.length > 0) {
        stats.top_sector = stats.top_sectors[0].sector_name || '-';
    }

    console.log('필터링된 통계:', {
        '선택된 개수': results.length,
        '분석 항공기': uniqueAircraft.size,
        '원본 데이터': originalStats.total_similarities,
        '필터링 결과': stats
    });

    return stats;
}

/**
 * 피크 시간 계산
 */
function calculatePeakHour(results) {
    const hourCounts = {};
    results.forEach(sim => {
        if (sim.sector_overlaps && Array.isArray(sim.sector_overlaps)) {
            sim.sector_overlaps.forEach(overlap => {
                // overlap_start 형식: "HH:MM:SS" 또는 "YYYY-MM-DDTHH:MM:SS"
                let hour = null;
                if (overlap.overlap_start) {
                    if (overlap.overlap_start.includes('T')) {
                        // ISO 형식에서 시간 추출
                        const timePart = overlap.overlap_start.split('T')[1];
                        hour = timePart ? timePart.split(':')[0] : null;
                    } else {
                        // HH:MM:SS 형식에서 시간 추출
                        hour = overlap.overlap_start.split(':')[0];
                    }
                }

                if (hour) {
                    hourCounts[hour] = (hourCounts[hour] || 0) + 1;
                }
            });
        }
    });

    let peakHour = '-';
    let maxCount = 0;
    for (const [hour, count] of Object.entries(hourCounts)) {
        if (count > maxCount) {
            maxCount = count;
            peakHour = hour + '시';  // 시간 형식으로 표시
        }
    }

    return peakHour;
}

/**
 * 평균 공존 시간 계산
 */
function calculateAverageOverlap(results) {
    let totalMinutes = 0;
    let count = 0;

    results.forEach(sim => {
        if (sim.total_overlap_minutes) {
            totalMinutes += sim.total_overlap_minutes;
            count++;
        }
    });

    return count > 0 ? Math.round(totalMinutes / count) : 0;
}

/**
 * 최다 빈도 섹터 계산
 */
function calculateTopSectors(results) {
    const sectorCounts = {};

    results.forEach(sim => {
        if (sim.sector_overlaps && Array.isArray(sim.sector_overlaps)) {
            sim.sector_overlaps.forEach(overlap => {
                // 섹터명 추출 (여러 필드명 지원)
                const sector = overlap.sector_name || overlap.sector || overlap.name;
                if (sector) {
                    sectorCounts[sector] = (sectorCounts[sector] || 0) + 1;
                }
            });
        }
    });

    const topSectors = Object.entries(sectorCounts)
        .map(([sector, count]) => ({
            sector_name: sector,
            count: count
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 3);

    console.log('최다 빈도 섹터:', { sectorCounts, topSectors });
    return topSectors;
}

/**
 * 시간대별 분포 계산
 */
function calculateHourlyDistribution(results) {
    const distribution = {};

    results.forEach(sim => {
        if (sim.sector_overlaps && Array.isArray(sim.sector_overlaps)) {
            sim.sector_overlaps.forEach(overlap => {
                // overlap_start 또는 다른 시간 필드에서 시간 추출
                const timeString = overlap.overlap_start || overlap.start_time || overlap.time;

                let hour = null;
                if (timeString) {
                    if (timeString.includes('T')) {
                        // ISO 형식 (YYYY-MM-DDTHH:MM:SS)에서 시간 추출
                        const timePart = timeString.split('T')[1];
                        hour = timePart ? timePart.split(':')[0] : null;
                    } else if (timeString.includes(':')) {
                        // HH:MM:SS 형식에서 시간 추출
                        hour = timeString.split(':')[0];
                    }
                }

                if (hour) {
                    const hourKey = hour.padStart(2, '0');  // 시간 포맷: "00", "01", ..., "23"
                    if (!distribution[hourKey]) {
                        distribution[hourKey] = 0;
                    }
                    distribution[hourKey]++;
                }
            });
        }
    });

    console.log('시간대별 분포:', { 결과개수: results.length, distribution });
    return distribution;
}

/**
 * 대시보드 왼쪽 메뉴 업데이트
 */
function updateDashboardMenus(statistics) {
    if (!statistics) return;

    // 1. 항공사별 검출순위
    updateAirlineRankingMenu(statistics);

    // 2. 유사도레벨 랭킹
    updateSimilarityLevelMenu(statistics);

    // 3. 콜사인 유사도 TOP 10
    updateCallsignTop10Menu(statistics);
}

/**
 * 시간대별 현황 (UTC) 메뉴 업데이트
 */
function updateHourlyStatusMenu(statistics) {
    const container = document.getElementById('hourly-status-list');
    if (!container) return;

    // 백엔드에서 전달받은 실제 데이터
    const hourlyData = (statistics && statistics.hourly_status) ? statistics.hourly_status : [];

    if (hourlyData.length === 0) {
        container.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">데이터 없음</div>';
        return;
    }

    // 최대값 구하기 (퍼센트 계산용)
    const maxCount = Math.max(...hourlyData.map(item => item.count), 1);

    let html = '';
    hourlyData.forEach((item) => {
        const percentage = (item.count / maxCount) * 100;
        const hour = String(item.hour).padStart(2, '0');
        html += `
            <div style="margin-bottom: 10px; padding: 8px 10px; background: white; border-radius: 4px; border-left: 3px solid #667eea;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 600; font-size: 13px; font-family: monospace;">${hour}:00 UTC</span>
                    <span style="background: #667eea; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: 600;">${item.count}</span>
                </div>
                <div style="height: 4px; background: #f0f0f0; border-radius: 2px; overflow: hidden;">
                    <div style="height: 100%; background: #667eea; width: ${percentage}%;"></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * 항공사별 검출순위 메뉴 업데이트
 */
function updateAirlineRankingMenu(statistics) {
    const container = document.getElementById('airline-ranking-list');
    if (!container) return;

    // 백엔드에서 전달받은 실제 데이터 (최대 5개)
    const airlineData = (statistics && statistics.airline_ranking) ? statistics.airline_ranking.slice(0, 5) : [];

    if (airlineData.length === 0) {
        container.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">데이터 없음</div>';
        return;
    }

    // 항공사 색상 정의
    const colorMap = {
        'KAL': '#3498db', 'AAL': '#e74c3c', 'UAL': '#f39c12',
        'DLH': '#27ae60', 'DAL': '#9b59b6', 'BAW': '#e67e22',
        'SWR': '#1abc9c', 'AFR': '#34495e', 'LHA': '#3498db',
        'IBE': '#e74c3c', 'KLM': '#f39c12', 'AZA': '#27ae60'
    };

    const maxCount = Math.max(...airlineData.map(item => item.count), 1);

    let html = '';
    airlineData.forEach((item, idx) => {
        const percentage = (item.count / maxCount) * 100;
        const color = colorMap[item.airline] || '#95a5a6';
        html += `
            <div style="margin-bottom: 10px; padding: 8px 10px; background: white; border-radius: 4px; border-left: 3px solid ${color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 600; font-size: 13px;">${idx + 1}. ${item.airline}</span>
                    <span style="background: ${color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: 600;">${item.count}</span>
                </div>
                <div style="height: 4px; background: #f0f0f0; border-radius: 2px; overflow: hidden;">
                    <div style="height: 100%; background: ${color}; width: ${percentage}%;"></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * 유사도레벨 랭킹 메뉴 업데이트
 */
function updateSimilarityLevelMenu(statistics) {
    const container = document.getElementById('similarity-level-list');
    if (!container) return;

    // 백엔드에서 전달받은 실제 데이터 (최대 5개)
    const levelData = (statistics && statistics.level_ranking) ? statistics.level_ranking.slice(0, 5) : [];

    if (levelData.length === 0) {
        container.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">데이터 없음</div>';
        return;
    }

    // 유사도 레벨 색상 정의
    const colorMap = {
        'CRITICAL': '#c0392b',
        'HIGH': '#e74c3c',
        'MEDIUM': '#f39c12',
        'LOW': '#f1c40f',
        'VERY_HIGH': '#c0392b',
        'VERY_LOW': '#95a5a6'
    };

    const maxCount = Math.max(...levelData.map(item => item.count), 1);

    let html = '';
    levelData.forEach((item, idx) => {
        const percentage = (item.count / maxCount) * 100;
        const color = colorMap[item.level] || '#95a5a6';
        html += `
            <div style="margin-bottom: 10px; padding: 8px 10px; background: white; border-radius: 4px; border-left: 3px solid ${color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 600; font-size: 13px;">${item.level}</span>
                    <span style="background: ${color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: 600;">${item.count}건</span>
                </div>
                <div style="height: 4px; background: #f0f0f0; border-radius: 2px; overflow: hidden;">
                    <div style="height: 100%; background: ${color}; width: ${percentage}%;"></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * 콜사인 TOP 10 메뉴 업데이트
 */
function updateCallsignTop10Menu(statistics) {
    const container = document.getElementById('callsign-top10-list');
    if (!container) return;

    // 백엔드에서 전달받은 실제 데이터 (최대 5개)
    const callsignData = (statistics && statistics.callsign_top10) ? statistics.callsign_top10.slice(0, 5) : [];

    if (callsignData.length === 0) {
        container.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">데이터 없음</div>';
        return;
    }

    // 유사도 레벨별 색상 정의
    const levelColorMap = {
        'CRITICAL': '#c0392b',
        'HIGH': '#e74c3c',
        'MEDIUM': '#f39c12',
        'LOW': '#f1c40f',
        'VERY_HIGH': '#c0392b',
        'VERY_LOW': '#95a5a6'
    };

    let html = '';
    callsignData.forEach((item, idx) => {
        const similarity = item.similarity_score || 0;
        const level = item.similarity_level || 'UNKNOWN';
        const levelColor = levelColorMap[level] || '#95a5a6';
        const bgColor = similarity >= 95 ? '#fff5f5' : '#f9f9f9';

        html += `
            <div style="margin-bottom: 10px; padding: 10px; background: ${bgColor}; border-radius: 4px; border: 1px solid #e0e0e0;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <span style="font-weight: 700; font-size: 12px; color: #2c3e50;">🏆 ${idx + 1}</span>
                    <span style="font-family: monospace; font-weight: 600; font-size: 12px; color: #3498db;">${item.callsign1}</span>
                    <span style="color: #bdc3c7;">↔</span>
                    <span style="font-family: monospace; font-weight: 600; font-size: 12px; color: #e74c3c;">${item.callsign2}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <div style="flex: 1; height: 6px; background: #e0e0e0; border-radius: 3px; margin-right: 8px; overflow: hidden;">
                        <div style="height: 100%; background: ${levelColor}; width: ${similarity}%;"></div>
                    </div>
                    <span style="font-weight: 700; font-size: 12px; color: #2c3e50; min-width: 35px; text-align: right;">${similarity.toFixed(1)}%</span>
                </div>
                <div style="font-size: 11px; color: #666;">
                    <span style="display: inline-block; background: ${levelColor}; color: white; padding: 2px 6px; border-radius: 2px; font-weight: 600;">${level}</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * 아코디언 토글
 */
function toggleAccordion(headerElement) {
    const content = headerElement.nextElementSibling;
    const isOpen = content.style.display !== 'none';

    // 모든 아코디언 닫기
    document.querySelectorAll('.accordion-content').forEach(el => {
        el.style.display = 'none';
    });
    document.querySelectorAll('.accordion-header').forEach(el => {
        const span = el.querySelector('span:first-child');
        if (span) span.textContent = '▶';
    });

    // 선택한 아코디언 열기
    if (!isOpen) {
        content.style.display = 'block';
        const span = headerElement.querySelector('span:first-child');
        if (span) span.textContent = '▼';
    }
}

/**
 * CSV 파일 선택 핸들러
 */
function handleCsvFileSelect() {
    const csvFileInput = document.getElementById('csv-file-input');
    const csvSelectedFile = document.getElementById('csv-selected-file');
    const csvFilename = document.getElementById('csv-filename');
    const csvUploadBtn = document.getElementById('csv-upload-btn');

    if (csvFileInput.files.length > 0) {
        const file = csvFileInput.files[0];
        csvFilename.textContent = file.name;
        csvSelectedFile.style.display = 'flex';
        csvUploadBtn.disabled = false;

        // 파일 크기로 예상 항공편 수 추정 (대략 1건당 80-100바이트)
        // 실제 CSV는 매우 가변적이지만, 추정치를 표시
        const estimatedRows = Math.round(file.size / 85);
        showCsvTimeEstimate(estimatedRows);
    }
}

/**
 * CSV 처리 예상 시간 표시
 */
async function showCsvTimeEstimate(recordCount) {
    const csvStatus = document.getElementById('csv-status');
    if (!csvStatus) return;

    try {
        const response = await fetch(`${window.location.origin}/api/processing/time-prediction?record_count=${recordCount}`);
        const result = await response.json();

        if (result.status === 'success') {
            const data = result.data;
            let estimateHtml = `
                <div style="background: #e3f2fd; color: #01579b; padding: 12px; border-radius: 4px; border-left: 4px solid #01579b; display: flex; gap: 8px; align-items: center;">
                    <i class="fas fa-hourglass-half"></i>
                    <span>
                        약 <strong>${data.total_formatted}</strong> 내에 처리 예상 
                        (${recordCount.toLocaleString()}건 ≈ ${data.rate_per_second.toFixed(0)}건/초)
                    </span>
                </div>
            `;
            csvStatus.innerHTML = estimateHtml;
        }
    } catch (error) {
        console.error('처리 시간 예측 오류:', error);
    }
}

/**
 * CLI 파일 선택 핸들러 (호환성 유지)
 */
function handleCliFileSelect() {
    const cliFileInput = document.getElementById('cli-file-input');
    const cliSelectedFile = document.getElementById('cli-selected-file');
    const cliFilename = document.getElementById('cli-filename');
    const cliRunBtn = document.getElementById('cli-run-btn');

    if (cliFileInput && cliFileInput.files.length > 0) {
        const file = cliFileInput.files[0];
        if (cliFilename) cliFilename.textContent = file.name;
        if (cliSelectedFile) cliSelectedFile.style.display = 'flex';
        if (cliRunBtn) cliRunBtn.disabled = false;
    }
}

/**
 * CSV 파일 업로드 핸들러
 */
async function handleCsvFileUpload() {
    const csvFileInput = document.getElementById('csv-file-input');
    const csvStatus = document.getElementById('csv-status');
    const csvProgressContainer = document.getElementById('csv-progress-container');
    const csvProgressBar = document.getElementById('csv-progress-bar');
    const csvProgressText = document.getElementById('csv-progress-text');
    const csvUploadBtn = document.getElementById('csv-upload-btn');

    if (csvFileInput.files.length === 0) {
        showCsvStatus('파일을 선택해주세요', 'error');
        return;
    }

    const file = csvFileInput.files[0];
    csvUploadBtn.disabled = true;
    csvProgressContainer.style.display = 'block';

    try {
        const result = await api.uploadFile(file, 'replace');

        if (result.status === 'success' || result.data) {
            const processId = result.data.process_id;
            showCsvStatus(`파일 업로드 시작 (${file.name}, ${result.data.record_count}건)`, 'success');

            // 진행 상황 모니터링
            monitorCsvUploadProgress(processId);
        } else {
            // 검증 실패시 상세 오류 표시
            let errorDetails = result.message || '업로드 실패';
            if (result.data && result.data.errors && result.data.errors.length > 0) {
                errorDetails = result.data.errors.join('\n');
            }
            showCsvStatus(`업로드 실패:\n${errorDetails}`, 'error');
            csvProgressContainer.style.display = 'none';
            csvUploadBtn.disabled = false;
            console.error('Upload error details:', result.data);
        }
    } catch (error) {
        showCsvStatus(`업로드 오류: ${error.message}`, 'error');
        csvProgressContainer.style.display = 'none';
        csvUploadBtn.disabled = false;
        console.error('Upload exception:', error);
    }
}

/**
 * CLI 파일 업로드 핸들러
 */
async function handleCliFileUpload() {
    const cliFileInput = document.getElementById('cli-file-input');
    const cliStatus = document.getElementById('cli-status');
    const cliProgressContainer = document.getElementById('cli-progress-container');
    const cliProgressBar = document.getElementById('cli-progress-bar');
    const cliProgressText = document.getElementById('cli-progress-text');
    const cliRunBtn = document.getElementById('cli-run-btn');

    if (!cliFileInput || cliFileInput.files.length === 0) {
        showCliStatus('파일을 선택해주세요', 'error');
        return;
    }

    const file = cliFileInput.files[0];
    if (cliRunBtn) cliRunBtn.disabled = true;
    if (cliProgressContainer) cliProgressContainer.style.display = 'block';

    try {
        const result = await api.uploadFile(file, 'replace');

        if (result.status === 'success' || result.data) {
            const processId = result.data.process_id;
            showCliStatus(`파일 업로드 시작 (${file.name}, ${result.data.record_count}건)`, 'success');

            // 진행 상황 모니터링
            monitorCliUploadProgress(processId);
        } else {
            showCliStatus(result.message || '업로드 실패', 'error');
            if (cliProgressContainer) cliProgressContainer.style.display = 'none';
            if (cliRunBtn) cliRunBtn.disabled = false;
        }
    } catch (error) {
        showCliStatus(`업로드 오류: ${error.message}`, 'error');
        if (cliProgressContainer) cliProgressContainer.style.display = 'none';
        if (cliRunBtn) cliRunBtn.disabled = false;
    }
}

/**
 * CLI 업로드 진행 상황 모니터링
 */
async function monitorCliUploadProgress(processId) {
    const cliProgressBar = document.getElementById('cli-progress-bar');
    const cliProgressText = document.getElementById('cli-progress-text');
    const cliStatus = document.getElementById('cli-status');
    const cliRunBtn = document.getElementById('cli-run-btn');

    const checkProgress = async () => {
        try {
            const progress = await api.getUploadProgress(processId);

            if (progress.status === 'in_progress') {
                const percent = progress.percent || 0;
                cliProgressBar.style.width = percent + '%';
                cliProgressText.textContent = `${progress.stage} (${percent}%)`;

                // 500ms 후 다시 확인
                setTimeout(checkProgress, 500);
            } else if (progress.status === 'completed') {
                cliProgressBar.style.width = '100%';
                cliProgressText.textContent = '완료!';
                showCliStatus('파일 업로드 및 분석 완료!', 'success');

                // 1초 후 진행률 창 숨기기
                setTimeout(() => {
                    document.getElementById('cli-progress-container').style.display = 'none';
                    cliRunBtn.disabled = false;
                }, 1000);

                // 대시보드 새로고침
                setTimeout(() => {
                    loadDashboardData();
                }, 1500);
            } else if (progress.status === 'error') {
                cliProgressBar.style.width = '0%';
                showCliStatus(`업로드 오류: ${progress.stage}`, 'error');
                cliRunBtn.disabled = false;
            }
        } catch (error) {
            console.error('진행 상황 조회 오류:', error);
            setTimeout(checkProgress, 1000);
        }
    };

    checkProgress();
}

/**
 * CLI 상태 메시지 표시
 */
function showCliStatus(message, type) {
    const cliStatus = document.getElementById('cli-status');
    if (!cliStatus) return;

    let bgColor = '#e8f5e9';
    let textColor = '#2e7d32';
    let icon = '<i class="fas fa-check-circle"></i>';

    if (type === 'error') {
        bgColor = '#ffebee';
        textColor = '#c62828';
        icon = '<i class="fas fa-exclamation-circle"></i>';
    } else if (type === 'warning') {
        bgColor = '#fff3e0';
        textColor = '#e65100';
        icon = '<i class="fas fa-exclamation-triangle"></i>';
    }

    cliStatus.innerHTML = `
        <div style="background: ${bgColor}; color: ${textColor}; padding: 10px 12px; border-radius: 4px; border-left: 4px solid ${textColor}; display: flex; gap: 8px; align-items: center;">
            ${icon}
            <span>${message}</span>
        </div>
    `;
}

/**
 * CSV 업로드 진행 상황 모니터링
 */
async function monitorCsvUploadProgress(processId) {
    const csvProgressBar = document.getElementById('csv-progress-bar');
    const csvProgressText = document.getElementById('csv-progress-text');
    const csvUploadBtn = document.getElementById('csv-upload-btn');

    const checkProgress = async () => {
        try {
            const progress = await api.getUploadProgress(processId);

            if (progress.status === 'in_progress') {
                const percent = progress.percent || 0;
                if (csvProgressBar) csvProgressBar.style.width = percent + '%';

                // 예상 남은 시간 표시
                let progressText = `${progress.stage} (${percent}%)`;
                if (progress.predicted_completion_time) {
                    progressText += ` | 예상 남은 시간: ${progress.predicted_completion_time}`;
                }

                if (csvProgressText) csvProgressText.textContent = progressText;

                setTimeout(checkProgress, 500);
            } else if (progress.status === 'completed') {
                if (csvProgressBar) csvProgressBar.style.width = '100%';
                if (csvProgressText) csvProgressText.textContent = '업로드 완료! 시뮬레이션 실행 중...';
                showCsvStatus('파일 업로드 완료! 자동으로 시뮬레이션을 실행하고 있습니다...', 'success');

                // 1초 후 자동 시뮬레이션 시작
                setTimeout(async () => {
                    try {
                        if (csvProgressText) csvProgressText.textContent = '시뮬레이션 중... (0%)';

                        // 시뮬레이션 실행
                        const simulationResult = await api.runSimulation({}, 2);

                        if (simulationResult.status === 'success') {
                            appState.simulationResults = simulationResult.data;
                            showCsvStatus('업로드 및 시뮬레이션 완료!', 'success');
                            if (csvProgressText) csvProgressText.textContent = '완료!';
                        } else {
                            showCsvStatus('시뮬레이션 중 오류가 발생했습니다. 대시보드에서 다시 시도하세요.', 'warning');
                            if (csvProgressText) csvProgressText.textContent = '업로드만 완료됨';
                        }
                    } catch (simError) {
                        console.error('자동 시뮬레이션 오류:', simError);
                        showCsvStatus('시뮬레이션 중 오류. 대시보드에서 수동으로 시도하세요.', 'warning');
                    }

                    // 최종 정리
                    setTimeout(() => {
                        if (document.getElementById('csv-progress-container')) {
                            document.getElementById('csv-progress-container').style.display = 'none';
                        }
                        if (csvUploadBtn) csvUploadBtn.disabled = false;
                        loadDashboardData();
                    }, 1500);
                }, 1000);
            } else if (progress.status === 'error') {
                if (csvProgressBar) csvProgressBar.style.width = '0%';
                showCsvStatus(`업로드 오류: ${progress.stage}`, 'error');
                if (csvUploadBtn) csvUploadBtn.disabled = false;
            }
        } catch (error) {
            console.error('진행 상황 조회 오류:', error);
            setTimeout(checkProgress, 1000);
        }
    };

    checkProgress();
}

/**
 * CSV 상태 메시지 표시
 */
function showCsvStatus(message, type) {
    const csvStatus = document.getElementById('csv-status');
    if (!csvStatus) return;

    let bgColor = '#e8f5e9';
    let textColor = '#2e7d32';
    let icon = '<i class="fas fa-check-circle"></i>';

    if (type === 'error') {
        bgColor = '#ffebee';
        textColor = '#c62828';
        icon = '<i class="fas fa-exclamation-circle"></i>';
    } else if (type === 'warning') {
        bgColor = '#fff3e0';
        textColor = '#e65100';
        icon = '<i class="fas fa-exclamation-triangle"></i>';
    }

    csvStatus.innerHTML = `
        <div style="background: ${bgColor}; color: ${textColor}; padding: 12px; border-radius: 4px; border-left: 4px solid ${textColor}; display: flex; gap: 8px; align-items: center;">
            ${icon}
            <span>${message}</span>
        </div>
    `;
}

/**
 * CSV 삭제 모달 표시
 */
function showCsvDeleteModal(deleteType) {
    // 동적으로 모달 생성
    const existingModal = document.getElementById('csv-delete-modal');
    if (existingModal) existingModal.remove();

    const modal = document.createElement('div');
    modal.id = 'csv-delete-modal';
    modal.style.cssText = 'display: flex; background: rgba(0,0,0,0.5); position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1000; flex-direction: column; align-items: center; justify-content: center;';

    const modalContent = document.createElement('div');
    modalContent.style.cssText = 'background: white; padding: 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); min-width: 350px;';

    if (deleteType === 'date') {
        modalContent.innerHTML = `
            <h3 style="margin-top: 0; color: #2c3e50;">입력 일자별 삭제</h3>
            <p style="color: #666; margin-bottom: 15px;">삭제할 날짜를 선택해주세요. 해당 날짜의 데이터가 모두 삭제됩니다.</p>
            <label style="display: block; font-size: 12px; color: #666; margin-bottom: 5px; font-weight: 600;">삭제할 날짜</label>
            <input type="date" id="csv-delete-date" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; margin-bottom: 15px;">
            <div style="display: flex; gap: 8px;">
                <button id="csv-delete-confirm" class="btn" style="flex: 1; background: #e74c3c; color: white; cursor: pointer; padding: 8px; border-radius: 4px; border: none;">삭제</button>
                <button id="csv-delete-cancel" class="btn" style="flex: 1; background: #95a5a6; color: white; cursor: pointer; padding: 8px; border-radius: 4px; border: none;">취소</button>
            </div>
        `;
    } else {
        modalContent.innerHTML = `
            <h3 style="margin-top: 0; color: #2c3e50;">전체 데이터 삭제</h3>
            <p style="color: #e74c3c; margin-bottom: 15px;"><i class="fas fa-exclamation-circle"></i> 모든 데이터가 삭제됩니다. 이 작업은 되돌릴 수 없습니다!</p>
            <div style="display: flex; gap: 8px;">
                <button id="csv-delete-confirm" class="btn" style="flex: 1; background: #e74c3c; color: white; cursor: pointer; padding: 8px; border-radius: 4px; border: none;">삭제</button>
                <button id="csv-delete-cancel" class="btn" style="flex: 1; background: #95a5a6; color: white; cursor: pointer; padding: 8px; border-radius: 4px; border: none;">취소</button>
            </div>
        `;
    }

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    const confirmBtn = document.getElementById('csv-delete-confirm');
    const cancelBtn = document.getElementById('csv-delete-cancel');
    const deleteDate = document.getElementById('csv-delete-date');

    if (confirmBtn) {
        confirmBtn.addEventListener('click', async () => {
            if (deleteType === 'date' && deleteDate && !deleteDate.value) {
                showCsvStatus('날짜를 선택해주세요', 'error');
                return;
            }

            const warningMessage = deleteType === 'date'
                ? `${deleteDate.value} 날짜의 데이터를 삭제합니다. 계속하시겠습니까?`
                : '모든 데이터를 삭제합니다. 이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?';
            if (!window.confirm(warningMessage)) {
                return;
            }

            modal.remove();
            await handleCsvDatabaseDelete(deleteType, deleteDate ? deleteDate.value : null);
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            modal.remove();
        });
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }
}

/**
 * CSV 데이터베이스 삭제 핸들러
 */
async function handleCsvDatabaseDelete(deleteType, date = null) {
    try {
        let message = '';
        if (deleteType === 'date') {
            message = `${date} 날짜의 데이터를 삭제 중...`;
        } else {
            message = '모든 데이터를 삭제 중...';
        }

        showCsvStatus(message, 'warning');

        const result = await api.deleteDatabase(deleteType, date);

        if (result.status === 'success') {
            if (deleteType === 'date') {
                showCsvStatus(`${date} 날짜의 데이터가 삭제되었습니다.`, 'success');
            } else {
                showCsvStatus('모든 데이터가 삭제되었습니다.', 'success');
            }

            setTimeout(() => {
                loadDashboardData();
            }, 1500);
        } else {
            showCsvStatus(result.message || '삭제 실패', 'error');
        }
    } catch (error) {
        showCsvStatus(`삭제 오류: ${error.message}`, 'error');
    }
}

/**
 * 데이터베이스 삭제 핸들러 (CLI 모드용)
 */
async function handleDatabaseDelete(deleteType, date = null) {
    try {
        let message = '';
        if (deleteType === 'date') {
            message = `${date} 날짜의 데이터를 삭제 중...`;
        } else {
            message = '모든 데이터를 삭제 중...';
        }

        showCliStatus(message, 'warning');

        const result = await api.deleteDatabase(deleteType, date);

        if (result.status === 'success') {
            if (deleteType === 'date') {
                showCliStatus(`${date} 날짜의 데이터가 삭제되었습니다.`, 'success');
            } else {
                showCliStatus('모든 데이터가 삭제되었습니다.', 'success');
            }

            setTimeout(() => {
                loadDashboardData();
            }, 1500);
        } else {
            showCliStatus(result.message || '삭제 실패', 'error');
        }
    } catch (error) {
        showCliStatus(`삭제 오류: ${error.message}`, 'error');
    }
}

window.bootstrapUI = async function bootstrapUI() {
    if (window.__uiBootstrapped) {
        return;
    }

    window.__uiBootstrapped = true;
    await initializeUI();
    setupChartToggleButtons();
};

/**
 * 모델링 테스트 뷰 로드 및 초기화
 */
let isTestViewLoaded = false;
async function loadTestView() {
    const container = document.getElementById('test-view-content');
    if (!container) return;

    // 이미 로드된 경우 초기화만 수행 (필요 시)
    if (isTestViewLoaded) {
        if (window.TestTab && typeof window.TestTab.init === 'function') {
            // TestTab.init(); // 필요시 매번 초기화하거나 상태 유지
        }
        return;
    }

    try {
        console.log("Loading Test View content...");
        const response = await fetch('views/test-tab.html');
        if (!response.ok) throw new Error("Failed to load test-tab.html");

        const html = await response.text();
        container.innerHTML = html;

        // 스크립트가 이미 로드되어 있어야 함 (index.html에서 추가함)
        if (window.TestTab && typeof window.TestTab.init === 'function') {
            window.TestTab.init();
            isTestViewLoaded = true;
            console.log("Test View initialized");
        } else {
            // 스크립트가 아직 로드되지 않은 경우를 위한 재시도 로직
            let retryCount = 0;
            const retryInterval = setInterval(() => {
                if (window.TestTab && typeof window.TestTab.init === 'function') {
                    window.TestTab.init();
                    isTestViewLoaded = true;
                    clearInterval(retryInterval);
                    console.log("Test View initialized (after retry)");
                }
                if (++retryCount > 10) clearInterval(retryInterval);
            }, 100);
        }
    } catch (error) {
        console.error("Test View 로드 중 오류:", error);
        container.innerHTML = `<div class="error-state">뷰를 로드할 수 없습니다: ${error.message}</div>`;
    }
}

/**
 * 항공기 기종 관리 뷰 로드 및 초기화
 */
let isAircraftViewLoaded = false;
async function loadAircraftView() {
    const container = document.getElementById('aircraft-view-content');
    if (!container) return;

    if (isAircraftViewLoaded) {
        return;
    }

    try {
        console.log('Loading Aircraft View content...');
        const response = await fetch('views/aircraft-tab.html');
        if (!response.ok) throw new Error('Failed to load aircraft-tab.html');

        const html = await response.text();
        container.innerHTML = html;

        const initialize = () => {
            if (window.AircraftTab && typeof window.AircraftTab.init === 'function') {
                window.AircraftTab.init();
                isAircraftViewLoaded = true;
                console.log('Aircraft View initialized');
                return true;
            }
            return false;
        };

        if (!initialize()) {
            let retries = 0;
            const retryInterval = setInterval(() => {
                if (initialize() || ++retries > 10) {
                    clearInterval(retryInterval);
                }
            }, 100);
        }
    } catch (error) {
        console.error('Aircraft View 로드 중 오류:', error);
        container.innerHTML = `<div class="error-state">뷰를 로드할 수 없습니다: ${error.message}</div>`;
    }
}

/**
 * 단일 항공편 상세 정보 팝업 열기
 */
async function openSingleFlightModal(flightId, callsign) {
    const modal = document.getElementById('single-flight-modal');
    if (!modal) return;

    try {
        console.log('Loading single flight details:', { flightId, callsign });

        // 제목 설정
        document.getElementById('single-flight-title').textContent = callsign;

        // API 호출 - 단일 항공편 상세정보 조회
        // 두 개의 같은 ID를 전달하여 flight_id_1 = flight_id_2로 설정
        const response = await api.getFlightPairDetails(flightId, flightId);
        console.log('Single flight response:', response);

        if (response.status === 'success') {
            const flightData = response.data.flight1;
            const info = flightData.info;

            // 기본 정보 표시
            const basicInfoHtml = `
                <strong>${callsign}</strong> (${info.aircraft_type || 'Unknown'})<br>
                <span style="color:#666;">
                    ${info.dept_airport_cd || '?'} <span style="color:#2c3e50; font-weight:bold;">(${info.eobt ? info.eobt.substring(0, 5) : '-'})</span>
                    →
                    ${info.dest_airport_cd || '?'}
                </span><br>
                <small style="color:#999;">EOBD: ${info.eobd || '-'}</small>
            `;
            document.getElementById('single-flight-basic-info').innerHTML = basicInfoHtml;

            // 경로 정보
            document.getElementById('single-flight-dept').textContent = info.dept_airport_cd || '-';
            document.getElementById('single-flight-dest').textContent = info.dest_airport_cd || '-';
            document.getElementById('single-flight-route').textContent = info.enr || '-';
            document.getElementById('single-flight-aircraft').textContent = `${info.aircraft_type || '-'}`;
            document.getElementById('single-flight-speed-alt').textContent = `${info.spd || '-'} / ${info.alt || '-'}`;

            // 지점별 통과 시간
            const waypointBody = document.getElementById('single-flight-waypoint-table');
            let waypointHtml = '';
            if (flightData.waypoints && flightData.waypoints.length > 0) {
                waypointHtml = flightData.waypoints.map(w => {
                    const time = w.estimated_time || w.actual_time || '-';
                    return `
                        <tr>
                            <td>${w.waypoint_name}</td>
                            <td>${time}</td>
                        </tr>
                    `;
                }).join('');
            } else if (info.waypoint_times && info.waypoint_times.trim()) {
                // 폴백: 문자열 형식
                const parts = info.waypoint_times.trim().split(/\s+/);
                for (let i = 0; i < parts.length; i += 2) {
                    if (i + 1 < parts.length) {
                        const pointName = parts[i];
                        const timeStr = parts[i + 1];
                        const formattedTime = timeStr.length === 4 ? `${timeStr.substring(0, 2)}:${timeStr.substring(2, 4)}` : timeStr;
                        waypointHtml += `<tr><td>${pointName}</td><td>${formattedTime}</td></tr>`;
                    }
                }
            }
            waypointBody.innerHTML = waypointHtml || '<tr><td colspan="2" style="text-align:center; color:#999;">지점 정보 없음</td></tr>';

            // 섹터 정보
            const sectorBody = document.getElementById('single-flight-sector-table');
            let sectorHtml = '';
            if (flightData.sectors && flightData.sectors.length > 0) {
                sectorHtml = flightData.sectors.map(s => {
                    const entryTime = (s.entry_time || '').substring(0, 5);
                    const exitTime = (s.exit_time || '').substring(0, 5);
                    // 체류 시간 계산
                    let durationStr = '-';
                    if (s.entry_time && s.exit_time) {
                        try {
                            const entry = new Date(`2000-01-01T${s.entry_time}`);
                            const exit = new Date(`2000-01-01T${s.exit_time}`);
                            const durationMin = Math.round((exit - entry) / 60000);
                            if (durationMin >= 0) {
                                durationStr = `${durationMin}분`;
                            }
                        } catch (e) {
                            // 계산 실패 시 대시 유지
                        }
                    }
                    return `
                        <tr>
                            <td><strong>${s.sector_name}</strong></td>
                            <td>${entryTime}</td>
                            <td>${exitTime}</td>
                            <td>${durationStr}</td>
                        </tr>
                    `;
                }).join('');
            }
            sectorBody.innerHTML = sectorHtml || '<tr><td colspan="4" style="text-align:center; color:#999;">섹터 정보 없음</td></tr>';

            // 유사호출 정보 표시 (있으면)
            const similaritySection = document.getElementById('single-flight-similarity-section');
            if (flightData.similarities && flightData.similarities.length > 0) {
                similaritySection.style.display = 'block';
                let similarityHtml = '';
                flightData.similarities.forEach(sim => {
                    const otherCallsign = sim.other_callsign || '알 수 없음';
                    const level = formatSimilarityLevel(sim.similarity_level);
                    const overlap = sim.has_sector_overlap ? `✓ 섹터 겹침(${sim.total_overlap_minutes || 0}분)` : '○ 섹터 겹침 없음';
                    similarityHtml += `
                        <div style="margin-bottom: 8px; padding: 8px; background: rgba(255,255,255,0.5); border-radius: 4px;">
                            <strong>${otherCallsign}</strong> - ${level}<br>
                            <small>${overlap}</small>
                        </div>
                    `;
                });
                document.getElementById('single-flight-similarity-info').innerHTML = similarityHtml;
            } else {
                similaritySection.style.display = 'none';
            }

            // 모달 표시
            modal.style.display = 'block';
        } else {
            alert('데이터를 불러오는데 실패했습니다.');
            modal.style.display = 'none';
        }
    } catch (error) {
        console.error('항공편 상세정보 로드 실패:', error);
        alert('서버 통신 오류가 발생했습니다.');
        const modal = document.getElementById('single-flight-modal');
        if (modal) modal.style.display = 'none';
    }
}

/**
 * 단일 항공편 팝업 닫기
 */
function closeSingleFlightModal() {
    const modal = document.getElementById('single-flight-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * 샘플 CSV 파일 다운로드
 */
function downloadSampleCSV() {
    try {
        // API에서 샘플 CSV 가져오기
        fetch(`${API_BASE_URL}/sample/flight-csv`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('샘플 파일을 불러올 수 없습니다');
                }
                return response.blob();
            })
            .then(blob => {
                // 파일 다운로드
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'Airspace_Flight_Sample.csv';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                console.log('샘플 CSV 파일이 다운로드되었습니다');
            })
            .catch(error => {
                console.error('샘플 파일 다운로드 오류:', error);
                alert('샘플 파일을 다운로드하는 데 실패했습니다.');
            });
    } catch (error) {
        console.error('샘플 파일 다운로드 오류:', error);
        alert('오류가 발생했습니다.');
    }
}

/**
 * 관리자 라이선스 관리
 */

// 라이선스 생성 폼 이벤트
function setupAdminLicenseManagement() {
    const orgNameInput = document.getElementById('license-org-name');
    const daysInput = document.getElementById('license-days');
    const expiryDisplay = document.getElementById('license-expiry-display');
    const previewOrg = document.getElementById('preview-org');
    const previewDays = document.getElementById('preview-days');
    const previewExpiry = document.getElementById('preview-expiry');
    const genBtn = document.getElementById('license-gen-btn');
    const copyBtn = document.getElementById('license-copy-btn');
    const downloadBtn = document.getElementById('license-download-btn');

    if (!orgNameInput) return;

    // 유효기간 변경 시 만료일 계산
    const updateExpiryDate = () => {
        const days = parseInt(daysInput.value) || 365;
        const today = new Date();
        const expiryDate = new Date(today.getTime() + days * 24 * 60 * 60 * 1000);

        const dateStr = expiryDate.toISOString().split('T')[0];
        expiryDisplay.value = dateStr;
        previewExpiry.textContent = dateStr;
    };

    // 조직명 변경 시 미리보기 업데이트
    orgNameInput.addEventListener('change', () => {
        previewOrg.textContent = orgNameInput.value || '입력 대기 중...';
    });

    // 일수 변경 시 만료일 계산
    daysInput.addEventListener('change', () => {
        const days = parseInt(daysInput.value) || 365;
        previewDays.textContent = days;
        updateExpiryDate();
    });

    // 초기 만료일 계산
    updateExpiryDate();

    // 라이선스 생성 버튼
    if (genBtn) {
        genBtn.addEventListener('click', generateLicense);
    }

    // 복사 버튼
    if (copyBtn) {
        copyBtn.addEventListener('click', copyLicenseJSON);
    }

    // 다운로드 버튼
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadLicenseJSON);
    }
}

/**
 * 라이선스 생성
 */
function generateLicense() {
    const orgName = document.getElementById('license-org-name').value.trim();
    const days = parseInt(document.getElementById('license-days').value) || 365;

    if (!orgName) {
        alert('조직명을 입력하세요.');
        return;
    }

    // API 호출
    fetch(`${API_BASE_URL}/admin/license/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            organization: orgName,
            days: days
        })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('라이선스 생성 실패');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // 결과 표시
                appState.generatedLicense = data.data;

                const resultSection = document.getElementById('license-result-section');
                const jsonDisplay = document.getElementById('license-display-json');

                jsonDisplay.textContent = JSON.stringify(data.data, null, 2);
                resultSection.style.display = 'block';

                // 페이지 스크롤
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

                console.log('라이선스 생성 완료');
            } else {
                alert(`라이선스 생성 실패: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('라이선스 생성 오류:', error);
            alert('라이선스 생성에 실패했습니다.');
        });
}

/**
 * 라이선스 JSON 복사
 */
function copyLicenseJSON() {
    if (!appState.generatedLicense) {
        alert('생성된 라이선스가 없습니다.');
        return;
    }

    const jsonStr = JSON.stringify(appState.generatedLicense, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
        alert('JSON이 클립보드에 복사되었습니다.');
    }).catch(err => {
        alert('복사 실패');
        console.error('복사 오류:', err);
    });
}

/**
 * 라이선스 JSON 파일 다운로드
 */
function downloadLicenseJSON() {
    if (!appState.generatedLicense) {
        alert('생성된 라이선스가 없습니다.');
        return;
    }

    const jsonStr = JSON.stringify(appState.generatedLicense, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'license.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

// 팝업 외부 클릭 시 닫기
document.addEventListener('DOMContentLoaded', function () {
    const singleFlightModal = document.getElementById('single-flight-modal');
    if (singleFlightModal) {
        window.addEventListener('click', function (event) {
            if (event.target === singleFlightModal) {
                singleFlightModal.style.display = 'none';
            }
        });

        // 닫기 버튼 클릭 시
        const closeBtn = singleFlightModal.querySelector('.close-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeSingleFlightModal);
        }
    }

    // 페이지 로드 시 Summary 탭이 활성화되어 있으면 데이터 로드
    const summaryView = document.getElementById('summary-view');
    if (summaryView && summaryView.classList.contains('active')) {
        loadSummaryView();
    }
});

/**
 * 요약 탭 (실시간 예측) 데이터 로드 및 렌더링
 */
async function loadSummaryView() {
    const timelineContainer = document.getElementById('summary-timeline');
    const lastUpdateEl = document.getElementById('summary-last-update');

    if (!timelineContainer) return;

    // 로딩 상태 표시
    timelineContainer.innerHTML = `
        <div class="timeline-loading">
            <i class="fas fa-circle-notch fa-spin"></i>
            <p>데이터 분석 중...</p>
        </div>
    `;

    try {
        // 선택된 오프셋 확인
        let offsetMinutes = 0;
        const activeOffsetBtn = document.querySelector('.offset-btn.active');
        if (activeOffsetBtn) {
            offsetMinutes = parseInt(activeOffsetBtn.dataset.offset || '0');
        }

        // base_time 계산 (현재 시간 + 오프셋)
        const baseTime = new Date();
        baseTime.setMinutes(baseTime.getMinutes() + offsetMinutes);
        const baseTimeStr = baseTime.toISOString();

        const response = await fetch(`${API_BASE_URL}/summary/forecast?base_time=${encodeURIComponent(baseTimeStr)}`);

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            renderSummaryMatrix(result);

            // 마지막 업데이트 시간 갱신
            const now = new Date();
            if (lastUpdateEl) {
                lastUpdateEl.textContent = now.toLocaleTimeString();
            }
        } else {
            throw new Error(result.message || '데이터 로드 실패');
        }

    } catch (error) {
        console.error('Summary load error:', error);
        timelineContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle" style="font-size: 24px; color: #ef4444; margin-bottom: 8px;"></i>
                <p>데이터를 불러오지 못했습니다.</p>
                <p style="font-size: 12px; color: var(--text-tertiary);">${error.message}</p>
            </div>
        `;
    }
}

/**
 * 요약 탭 매트릭스 렌더링 (Sectors x Time)
 */
function renderSummaryMatrix(data) {
    const container = document.getElementById('summary-timeline');
    if (!container) return;

    const { time_labels, time_ranges, sectors } = data;

    container.innerHTML = '';

    // 매트릭스 컨테이너 생성
    const matrixContainer = document.createElement('div');
    matrixContainer.className = 'summary-matrix-container';

    if (!sectors || sectors.length === 0) {
        container.innerHTML = '<div class="empty-state">표시할 데이터가 없습니다.</div>';
        return;
    }

    // 헤더 행 (시간 라벨)
    const headerRow = document.createElement('div');
    headerRow.className = 'matrix-header-row';

    // 첫 컬럼 (섹터명) 빈칸
    const emptyHeader = document.createElement('div');
    emptyHeader.className = 'matrix-header-cell sector-col';
    emptyHeader.textContent = '관제 섹터';
    headerRow.appendChild(emptyHeader);

    time_labels.forEach((label, idx) => {
        const cell = document.createElement('div');
        cell.className = 'matrix-header-cell time-col';
        cell.innerHTML = `
            <div class="time-main">${label}</div>
            <div class="time-sub">${time_ranges[idx]}</div>
        `;
        headerRow.appendChild(cell);
    });
    matrixContainer.appendChild(headerRow);

    // 데이터 행 (섹터별)
    sectors.forEach(sector => {
        const row = document.createElement('div');
        row.className = 'matrix-row';

        // 섹터명 컬럼
        const nameCell = document.createElement('div');
        nameCell.className = 'matrix-cell sector-name-cell';
        nameCell.textContent = sector.name;
        row.appendChild(nameCell);

        // 시간 슬롯 컬럼
        // 시간 슬롯 컬럼
        sector.slots.forEach(slot => {
            const cell = document.createElement('div');
            // 위험도 클래스 (high, medium, low, none)
            const riskLevel = slot.max_risk ? slot.max_risk.toLowerCase() : 'none';
            cell.className = `matrix-cell risk-cell ${riskLevel}`;

            let riskText = '';
            if (slot.max_risk === 'HIGH') riskText = '심각';
            else if (slot.max_risk === 'MEDIUM') riskText = '경계';
            else if (slot.max_risk === 'LOW') riskText = '주의';

            if (slot.count > 0) {
                cell.innerHTML = `
                    <div class="risk-count">${slot.count}</div>
                    <div class="risk-label">${riskText}</div>
                `;
            } else {
                cell.innerHTML = '<span class="dash">-</span>';
            }

            row.appendChild(cell);
        });

        matrixContainer.appendChild(row);
    });

    container.appendChild(matrixContainer);
}
