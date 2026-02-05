/**
 * 비행계획서 모델링 테스트 탭 로직
 */

const TestTab = {
    init() {
        console.log("TestTab initialized");
        this.cacheDOM();
        this.bindEvents();
        this.setDefaultDate();

        // FIX 이동시간 관리 모듈 초기화
        if (window.FixTravelTimesManager) {
            FixTravelTimesManager.init();
        }
    },

    cacheDOM() {
        this.form = document.getElementById('test-flight-form');
        this.clearBtn = document.getElementById('test-clear-btn');
        this.sectorCard = document.getElementById('test-sector-card');
        this.waypointCard = document.getElementById('test-waypoint-card');
        this.emptyState = document.getElementById('test-empty-state');
        this.loading = document.getElementById('test-loading');

        this.sectorTableBody = document.querySelector('#test-sector-table tbody');
        this.waypointTableBody = document.querySelector('#test-waypoint-table tbody');
        this.routeExpansion = document.getElementById('test-route-expansion');
    },

    bindEvents() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCalculate();
            });
        }

        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => {
                this.form.reset();
                this.setDefaultDate();
                this.resetResults();
            });
        }
    },

    setDefaultDate() {
        const dateInput = document.getElementById('test-eobd');
        if (dateInput) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }
    },

    resetResults() {
        this.sectorCard.style.display = 'none';
        this.waypointCard.style.display = 'none';
        this.emptyState.style.display = 'flex';
        this.sectorTableBody.innerHTML = '';
        this.waypointTableBody.innerHTML = '';
    },

    async handleCalculate() {
        const formData = {
            callsign: document.getElementById('test-callsign').value,
            aircraft_type: document.getElementById('test-aircraft-type').value,
            speed: document.getElementById('test-speed').value,
            altitude: document.getElementById('test-altitude').value,
            dept: document.getElementById('test-dept').value,
            dest: document.getElementById('test-dest').value,
            eobd: document.getElementById('test-eobd').value,
            eobt: document.getElementById('test-eobt').value,
            route: document.getElementById('test-route').value,
            eet: document.getElementById('test-eet').value,
            info_cn: document.getElementById('test-info-cn').value
        };

        this.showLoading(true);
        this.emptyState.style.display = 'none';

        try {
            const result = await api.calculateFlight(formData);

            if (result.status === 'success') {
                this.renderResults(result.data);
            } else {
                alert("계산 오류: " + result.message);
                this.emptyState.style.display = 'flex';
            }
        } catch (error) {
            console.error("Calculation failed:", error);
            alert("서버 통신 오류가 발생했습니다.");
            this.emptyState.style.display = 'flex';
        } finally {
            this.showLoading(false);
        }
    },

    showLoading(show) {
        if (this.loading) {
            this.loading.style.display = show ? 'flex' : 'none';
        }
    },

    renderResults(data) {
        // 섹터 렌더링
        this.sectorTableBody.innerHTML = '';
        if (data.sectors && data.sectors.length > 0) {
            data.sectors.forEach(s => {
                const entry = s.entry;
                const exit = s.exit;
                const duration = this.calculateDuration(entry, exit);

                const row = `
                    <tr>
                        <td><strong>${s.name}</strong></td>
                        <td>${entry}</td>
                        <td>${exit}</td>
                        <td><span class="badge badge-primary">${duration}분</span></td>
                    </tr>
                `;
                this.sectorTableBody.insertAdjacentHTML('beforeend', row);
            });
            this.sectorCard.style.display = 'block';
        } else {
            this.sectorCard.style.display = 'none';
        }

        // 웨이포인트 렌더링
        this.waypointTableBody.innerHTML = '';
        if (data.waypoints && data.waypoints.length > 0) {
            data.waypoints.forEach((w, index) => {
                const row = `
                    <tr>
                        <td>${index + 1}</td>
                        <td><strong>${w.name}</strong></td>
                        <td class="text-primary font-weight-bold">${w.time}</td>
                        <td class="text-muted small">${w.lat.toFixed(4)}, ${w.lon.toFixed(4)}</td>
                    </tr>
                `;
                this.waypointTableBody.insertAdjacentHTML('beforeend', row);
            });
            this.routeExpansion.textContent = data.route_expansion;
            this.waypointCard.style.display = 'block';
        } else {
            this.waypointCard.style.display = 'none';
        }
    },

    calculateDuration(entry, exit) {
        try {
            const [h1, m1] = entry.split(':').map(Number);
            const [h2, m2] = exit.split(':').map(Number);
            let diff = (h2 * 60 + m2) - (h1 * 60 + m1);
            if (diff < 0) diff += 24 * 60; // 다음날
            return diff;
        } catch (e) {
            return 0;
        }
    }
};

// 탭 로드 시 자동 실행 로직은 app.js에서 담당
window.TestTab = TestTab;


// ============================================================================
// FIX 이동시간 관리 모듈
// ============================================================================

const FixTravelTimesManager = {
    data: [],           // 현재 로드된 데이터
    filteredData: [],   // 필터링된 데이터
    isExpanded: false,  // 섹션 확장 상태
    editingItem: null,  // 현재 편집 중인 항목

    init() {
        console.log("FixTravelTimesManager initialized");
        this.cacheDOM();
        this.bindEvents();
    },

    cacheDOM() {
        this.toggleBtn = document.getElementById('fix-times-toggle-btn');
        this.content = document.getElementById('fix-times-content');
        this.fileInput = document.getElementById('fix-times-file-input');
        this.uploadBtn = document.getElementById('fix-times-upload-btn');
        this.methodSelect = document.getElementById('fix-times-method');
        this.refreshBtn = document.getElementById('fix-times-refresh-btn');
        this.downloadBtn = document.getElementById('fix-times-download-btn');
        this.addBtn = document.getElementById('fix-times-add-btn');
        this.searchInput = document.getElementById('fix-times-search');
        this.countSpan = document.getElementById('fix-times-count');
        this.tbody = document.getElementById('fix-times-tbody');
        this.statusDiv = document.getElementById('fix-times-status');
        this.statsDiv = document.getElementById('fix-times-stats');
        this.modal = document.getElementById('fix-time-modal');
        this.modalTitle = document.getElementById('fix-time-modal-title');
        this.saveBtn = document.getElementById('fix-time-save-btn');
    },

    bindEvents() {
        // 섹션 토글
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggleSection());
        }

        // 파일 업로드
        if (this.uploadBtn && this.fileInput) {
            this.uploadBtn.addEventListener('click', () => this.fileInput.click());
            this.fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }

        // 새로고침
        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => this.loadData());
        }

        // JSON 다운로드
        if (this.downloadBtn) {
            this.downloadBtn.addEventListener('click', () => this.downloadJson());
        }

        // 추가 버튼
        if (this.addBtn) {
            this.addBtn.addEventListener('click', () => this.openModal());
        }

        // 검색
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.filterData());
        }

        // 모달 저장
        if (this.saveBtn) {
            this.saveBtn.addEventListener('click', () => this.saveItem());
        }

        // 모달 외부 클릭 닫기
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.closeModal();
                }
            });
        }
    },

    toggleSection() {
        this.isExpanded = !this.isExpanded;
        if (this.content) {
            this.content.style.display = this.isExpanded ? 'block' : 'none';
        }
        if (this.toggleBtn) {
            const icon = this.toggleBtn.querySelector('i');
            if (icon) {
                icon.className = this.isExpanded ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
            }
        }

        // 확장 시 데이터 로드
        if (this.isExpanded && this.data.length === 0) {
            this.loadData();
        }
    },

    showStatus(message, type = 'info') {
        if (this.statusDiv) {
            this.statusDiv.textContent = message;
            this.statusDiv.className = `fix-times-status ${type}`;
            this.statusDiv.style.display = 'block';

            // 5초 후 자동 숨김
            setTimeout(() => {
                this.statusDiv.style.display = 'none';
            }, 5000);
        }
    },

    async loadData() {
        try {
            this.showStatus('데이터를 불러오는 중...', 'info');

            const response = await fetch(`${API_BASE_URL}/fix-travel-times`, {
                credentials: 'include'
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.data = result.data || [];
                this.filterData();
                this.showStatus(`${this.data.length}개의 FIX 쌍 로드 완료`, 'success');
            } else {
                this.showStatus(result.message || '데이터 로드 실패', 'error');
            }
        } catch (error) {
            console.error('FIX 이동시간 로드 오류:', error);
            this.showStatus('서버 통신 오류', 'error');
        }
    },

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            this.showStatus('파일을 업로드하는 중...', 'info');

            const formData = new FormData();
            formData.append('file', file);
            formData.append('method', this.methodSelect?.value || 'average');

            const response = await fetch(`${API_BASE_URL}/fix-travel-times/upload`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.data = result.data || [];
                this.filterData();
                this.showStats(result.statistics);
                this.showStatus(result.message || '업로드 완료', 'success');
            } else {
                this.showStatus(result.message || '업로드 실패', 'error');
            }
        } catch (error) {
            console.error('파일 업로드 오류:', error);
            this.showStatus('파일 업로드 오류', 'error');
        }

        // 파일 입력 초기화
        this.fileInput.value = '';
    },

    showStats(stats) {
        if (this.statsDiv && stats) {
            this.statsDiv.innerHTML = `
                <div class="stat-item"><i class="fas fa-file-alt"></i> 처리된 라인: ${stats.total_lines || 0}개</div>
                <div class="stat-item"><i class="fas fa-exchange-alt"></i> FIX 쌍: ${stats.total_fix_pairs || 0}개</div>
                <div class="stat-item"><i class="fas fa-database"></i> 총 샘플: ${stats.total_samples || 0}개</div>
                <div class="stat-item"><i class="fas fa-map-marker-alt"></i> 고유 FIX: ${stats.unique_fixes || 0}개</div>
            `;
            this.statsDiv.style.display = 'flex';
        }
    },

    filterData() {
        const query = (this.searchInput?.value || '').toUpperCase().trim();

        if (query) {
            this.filteredData = this.data.filter(item =>
                item.from_fix.includes(query) || item.to_fix.includes(query)
            );
        } else {
            this.filteredData = [...this.data];
        }

        this.renderTable();
        this.updateCount();
    },

    updateCount() {
        if (this.countSpan) {
            this.countSpan.textContent = `총 ${this.filteredData.length}개`;
        }
    },

    renderTable() {
        if (!this.tbody) return;

        if (this.filteredData.length === 0) {
            this.tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="4" style="text-align: center; color: #999; padding: 40px;">
                        <i class="fas fa-database" style="font-size: 2em; margin-bottom: 10px; display: block;"></i>
                        데이터가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }

        this.tbody.innerHTML = this.filteredData.map((item, index) => `
            <tr data-index="${index}">
                <td><strong>${item.from_fix}</strong></td>
                <td><strong>${item.to_fix}</strong></td>
                <td>
                    <input type="number" class="form-control edit-input"
                           value="${item.time_minutes}"
                           step="0.1" min="0"
                           data-from="${item.from_fix}"
                           data-to="${item.to_fix}"
                           onchange="FixTravelTimesManager.handleInlineEdit(this)">
                </td>
                <td style="text-align: center;">
                    <button class="btn btn-danger btn-sm" onclick="FixTravelTimesManager.deleteItem('${item.from_fix}', '${item.to_fix}')" title="삭제">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    },

    async handleInlineEdit(input) {
        const fromFix = input.dataset.from;
        const toFix = input.dataset.to;
        const newValue = parseFloat(input.value);

        if (isNaN(newValue) || newValue < 0) {
            this.showStatus('유효한 시간 값을 입력하세요', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/fix-travel-times/item`, {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_fix: fromFix,
                    to_fix: toFix,
                    time_minutes: newValue
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                // 로컬 데이터 업데이트
                const item = this.data.find(d => d.from_fix === fromFix && d.to_fix === toFix);
                if (item) item.time_minutes = newValue;
                this.showStatus(`${fromFix} → ${toFix} = ${newValue}분 저장됨`, 'success');
            } else {
                this.showStatus(result.message || '저장 실패', 'error');
            }
        } catch (error) {
            console.error('인라인 편집 오류:', error);
            this.showStatus('저장 오류', 'error');
        }
    },

    async deleteItem(fromFix, toFix) {
        if (!confirm(`${fromFix} → ${toFix} 항목을 삭제하시겠습니까?`)) {
            return;
        }

        try {
            const response = await fetch(
                `${API_BASE_URL}/fix-travel-times/item?from_fix=${encodeURIComponent(fromFix)}&to_fix=${encodeURIComponent(toFix)}`,
                {
                    method: 'DELETE',
                    credentials: 'include'
                }
            );

            const result = await response.json();

            if (result.status === 'success') {
                // 로컬 데이터에서 제거
                this.data = this.data.filter(d => !(d.from_fix === fromFix && d.to_fix === toFix));
                this.filterData();
                this.showStatus(`${fromFix} → ${toFix} 삭제됨`, 'success');
            } else {
                this.showStatus(result.message || '삭제 실패', 'error');
            }
        } catch (error) {
            console.error('삭제 오류:', error);
            this.showStatus('삭제 오류', 'error');
        }
    },

    openModal(item = null) {
        this.editingItem = item;

        if (this.modalTitle) {
            this.modalTitle.textContent = item ? 'FIX 이동시간 수정' : 'FIX 이동시간 추가';
        }

        document.getElementById('fix-time-from').value = item?.from_fix || '';
        document.getElementById('fix-time-to').value = item?.to_fix || '';
        document.getElementById('fix-time-minutes').value = item?.time_minutes || '';

        // 수정 모드에서는 FIX 필드 비활성화
        document.getElementById('fix-time-from').disabled = !!item;
        document.getElementById('fix-time-to').disabled = !!item;

        if (this.modal) {
            this.modal.style.display = 'flex';
        }
    },

    closeModal() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
        this.editingItem = null;
    },

    async saveItem() {
        const fromFix = document.getElementById('fix-time-from').value.trim().toUpperCase();
        const toFix = document.getElementById('fix-time-to').value.trim().toUpperCase();
        const timeMinutes = parseFloat(document.getElementById('fix-time-minutes').value);

        if (!fromFix || !toFix) {
            this.showStatus('출발 FIX와 도착 FIX를 입력하세요', 'error');
            return;
        }

        if (isNaN(timeMinutes) || timeMinutes < 0) {
            this.showStatus('유효한 시간 값을 입력하세요', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/fix-travel-times/item`, {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_fix: fromFix,
                    to_fix: toFix,
                    time_minutes: timeMinutes
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.closeModal();
                await this.loadData();  // 데이터 다시 로드
                this.showStatus(`${fromFix} → ${toFix} = ${timeMinutes}분 저장됨`, 'success');
            } else {
                this.showStatus(result.message || '저장 실패', 'error');
            }
        } catch (error) {
            console.error('저장 오류:', error);
            this.showStatus('저장 오류', 'error');
        }
    },

    async downloadJson() {
        try {
            window.open(`${API_BASE_URL}/fix-travel-times/download`, '_blank');
        } catch (error) {
            console.error('다운로드 오류:', error);
            this.showStatus('다운로드 오류', 'error');
        }
    }
};

// 전역 함수 (모달 닫기용)
function closeFixTimeModal() {
    FixTravelTimesManager.closeModal();
}

// 전역 등록
window.FixTravelTimesManager = FixTravelTimesManager;
