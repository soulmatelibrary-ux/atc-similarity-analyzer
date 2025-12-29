/**
 * 항공기 기종 관리 탭 로직
 */
const AircraftTab = {
    state: {
        page: 1,
        perPage: 100,
        totalPages: 1,
        totalCount: 0,
        search: '',
        editingIcao: null,
        list: []
    },

    init() {
        console.log('AircraftTab initialized');
        this.cacheDOM();
        this.bindEvents();
        this.initCSVImport();
        this.loadProfiles();
    },

    cacheDOM() {
        this.container = document.querySelector('.aircraft-tab-container');
        this.statusBox = document.getElementById('aircraft-status');
        this.tableBody = document.getElementById('aircraft-table-body');
        this.totalCountLabel = document.getElementById('aircraft-total-count');
        this.pageInfo = document.getElementById('aircraft-page-info');
        this.prevBtn = document.getElementById('aircraft-prev-btn');
        this.nextBtn = document.getElementById('aircraft-next-btn');
        this.pageSizeSelect = document.getElementById('aircraft-page-size');
        if (this.pageSizeSelect) {
            this.pageSizeSelect.value = String(this.state.perPage);
        }
        this.searchInput = document.getElementById('aircraft-search');
        this.refreshBtn = document.getElementById('aircraft-refresh-btn');
        this.loadingLayer = document.getElementById('aircraft-loading');

        this.form = document.getElementById('aircraft-form');
        this.formTitle = document.getElementById('aircraft-form-title');
        this.resetBtn = document.getElementById('aircraft-reset-btn');
        this.cancelEditBtn = document.getElementById('aircraft-cancel-edit');
        this.submitBtn = document.getElementById('aircraft-submit-btn');
        this.currentIcaoInput = document.getElementById('aircraft-current-icao');

        this.icaoInput = document.getElementById('aircraft-icao');
        this.iataInput = document.getElementById('aircraft-iata');
        this.manufacturerInput = document.getElementById('aircraft-manufacturer');
        this.modelInput = document.getElementById('aircraft-model');
        this.typeInput = document.getElementById('aircraft-type-description');
        this.speedKmhInput = document.getElementById('aircraft-speed-kmh');
        this.speedKnotsInput = document.getElementById('aircraft-speed-knots');
        this.climbInput = document.getElementById('aircraft-climb');
        this.ceilingInput = document.getElementById('aircraft-ceiling');
        this.notesInput = document.getElementById('aircraft-notes');
    },

    bindEvents() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSubmit();
            });
        }

        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', () => this.resetForm());
        }

        if (this.cancelEditBtn) {
            this.cancelEditBtn.addEventListener('click', () => this.resetForm());
        }

        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => {
                if (this.state.page > 1) {
                    this.state.page -= 1;
                    this.loadProfiles();
                }
            });
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => {
                if (this.state.page < this.state.totalPages) {
                    this.state.page += 1;
                    this.loadProfiles();
                }
            });
        }

        if (this.pageSizeSelect) {
            this.pageSizeSelect.addEventListener('change', () => {
                this.state.perPage = Number(this.pageSizeSelect.value) || this.state.perPage;
                this.state.page = 1;
                this.loadProfiles();
            });
        }

        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.handleSearchChange());
        }

        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => this.loadProfiles());
        }

        if (this.tableBody) {
            this.tableBody.addEventListener('click', (event) => {
                const target = event.target.closest('button');
                if (!target) return;
                const icao = target.dataset.icao;

                if (target.classList.contains('btn-edit')) {
                    const profile = this.state.list?.find(item => item.icao_code === icao);
                    if (profile) {
                        this.populateForm(profile);
                    }
                }

                if (target.classList.contains('btn-delete')) {
                    this.handleDelete(icao);
                }
            });
        }
    },

    async loadProfiles() {
        if (!this.container) return;
        this.toggleLoading(true);
        this.showStatus('기종 정보를 불러오는 중입니다...', 'info');

        try {
            const response = await api.getAircraftProfiles(this.state.page, this.state.perPage, this.state.search);
            if (response.status !== 'success') {
                throw new Error(response.message || '조회에 실패했습니다.');
            }

            const profiles = response.data || [];
            this.state.list = profiles;
            this.state.totalCount = response.pagination?.total || profiles.length;
            this.state.totalPages = response.pagination?.total_pages || 1;

            this.renderTable(profiles);
            this.updatePagination();
            this.showStatus(`${profiles.length}건을 불러왔습니다.`, 'success');
        } catch (error) {
            console.error('Aircraft profiles load failed:', error);
            this.renderErrorRow(error.message);
            this.showStatus(`목록 조회 실패: ${error.message}`, 'error');
        } finally {
            this.toggleLoading(false);
        }
    },

    renderTable(profiles) {
        if (!this.tableBody) return;
        if (!profiles.length) {
            this.tableBody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px 0; color:#999;">표시할 기종이 없습니다.</td></tr>';
            return;
        }

        const rows = profiles.map((profile, index) => {
            const safe = (value) => value ?? '-';
            const icaoValue = profile.icao_code || '';
            // 페이지네이션을 고려한 번호 계산
            const rowNumber = (this.state.page - 1) * this.state.perPage + index + 1;
            return `
                <tr>
                    <td style="text-align: center; color: #666;"><strong>${rowNumber}</strong></td>
                    <td><strong>${safe(profile.icao_code)}</strong></td>
                    <td>${safe(profile.iata_code)}</td>
                    <td>${safe(profile.manufacturer)}</td>
                    <td>${safe(profile.model)}</td>
                    <td>${safe(profile.default_speed_kmh)}</td>
                    <td>${safe(profile.default_speed_knots)}</td>
                    <td>${safe(profile.default_climb_fpm)}</td>
                    <td>${safe(profile.default_ceiling_fl)}</td>
                    <td>
                        <div class="aircraft-table-actions">
                            <button class="btn-edit" data-icao="${icaoValue}">
                                <i class="fas fa-pen"></i> 수정
                            </button>
                            <button class="btn-delete" data-icao="${icaoValue}">
                                <i class="fas fa-trash"></i> 삭제
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        this.tableBody.innerHTML = rows;
    },

    updatePagination() {
        if (this.totalCountLabel) {
            this.totalCountLabel.textContent = this.state.totalCount.toLocaleString();
        }
        if (this.pageInfo) {
            this.pageInfo.textContent = `${this.state.page} / ${this.state.totalPages}`;
        }
        if (this.prevBtn) {
            this.prevBtn.disabled = this.state.page <= 1;
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = this.state.page >= this.state.totalPages;
        }
    },

    renderErrorRow(message) {
        if (this.tableBody) {
            this.tableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:30px 0; color:#d7263d;">${message}</td></tr>`;
        }
    },

    handleSearchChange() {
        clearTimeout(this.searchTimer);
        this.searchTimer = setTimeout(() => {
            this.state.search = (this.searchInput?.value || '').trim();
            this.state.page = 1;
            this.loadProfiles();
        }, 300);
    },

    async handleSubmit() {
        const payload = this.collectFormData();
        if (!payload) return;

        const isEditing = Boolean(this.state.editingIcao);
        this.toggleFormDisabled(true);
        this.showStatus(isEditing ? '기종 정보를 수정하는 중입니다...' : '새 기종을 등록하는 중입니다...', 'info');

        try {
            if (isEditing) {
                const updatePayload = { ...payload };
                delete updatePayload.icao_code;
                await api.updateAircraftProfile(this.state.editingIcao, updatePayload);
                this.showStatus('기종 정보가 업데이트되었습니다.', 'success');
            } else {
                await api.createAircraftProfile(payload);
                this.showStatus('새 기종이 등록되었습니다.', 'success');
            }

            this.resetForm(false);
            this.loadProfiles();
        } catch (error) {
            console.error('Aircraft profile save failed:', error);
            const message = error?.message || '저장 중 오류가 발생했습니다.';
            this.showStatus(message, 'error');
        } finally {
            this.toggleFormDisabled(false);
        }
    },

    collectFormData() {
        const icao = (this.icaoInput?.value || '').trim().toUpperCase();
        if (!icao) {
            alert('ICAO 코드를 입력하세요.');
            return null;
        }

        return {
            icao_code: icao,
            iata_code: (this.iataInput?.value || '').trim().toUpperCase() || null,
            manufacturer: (this.manufacturerInput?.value || '').trim() || null,
            model: (this.modelInput?.value || '').trim() || null,
            type_description: (this.typeInput?.value || '').trim() || null,
            default_speed_kmh: this.parseNumber(this.speedKmhInput?.value),
            default_speed_knots: this.parseNumber(this.speedKnotsInput?.value),
            default_climb_fpm: this.parseNumber(this.climbInput?.value),
            default_ceiling_fl: this.parseNumber(this.ceilingInput?.value),
            notes: (this.notesInput?.value || '').trim() || null
        };
    },

    parseNumber(value) {
        if (value === undefined || value === null || value === '') {
            return null;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    },

    populateForm(profile) {
        this.state.editingIcao = profile.icao_code;
        if (this.formTitle) {
            this.formTitle.innerHTML = '<i class="fas fa-pen"></i> 기종 정보 수정';
        }
        if (this.cancelEditBtn) {
            this.cancelEditBtn.style.display = 'inline-flex';
        }
        if (this.submitBtn) {
            this.submitBtn.innerHTML = '<i class="fas fa-save"></i> 수정 저장';
        }
        if (this.icaoInput) {
            this.icaoInput.value = profile.icao_code || '';
            this.icaoInput.disabled = true;
        }
        if (this.currentIcaoInput) {
            this.currentIcaoInput.value = profile.icao_code || '';
        }

        if (this.iataInput) this.iataInput.value = profile.iata_code || '';
        if (this.manufacturerInput) this.manufacturerInput.value = profile.manufacturer || '';
        if (this.modelInput) this.modelInput.value = profile.model || '';
        if (this.typeInput) this.typeInput.value = profile.type_description || '';
        if (this.speedKmhInput) this.speedKmhInput.value = profile.default_speed_kmh ?? '';
        if (this.speedKnotsInput) this.speedKnotsInput.value = profile.default_speed_knots ?? '';
        if (this.climbInput) this.climbInput.value = profile.default_climb_fpm ?? '';
        if (this.ceilingInput) this.ceilingInput.value = profile.default_ceiling_fl ?? '';
        if (this.notesInput) this.notesInput.value = profile.notes || '';
    },

    resetForm(resetSearch = false) {
        this.form?.reset();
        this.state.editingIcao = null;
        if (this.formTitle) {
            this.formTitle.innerHTML = '<i class="fas fa-plus-circle"></i> 새 기종 등록';
        }
        if (this.cancelEditBtn) {
            this.cancelEditBtn.style.display = 'none';
        }
        if (this.submitBtn) {
            this.submitBtn.innerHTML = '<i class="fas fa-save"></i> 저장';
        }
        if (this.icaoInput) {
            this.icaoInput.disabled = false;
        }
        if (this.currentIcaoInput) {
            this.currentIcaoInput.value = '';
        }

        if (resetSearch && this.searchInput) {
            this.searchInput.value = '';
            this.state.search = '';
        }
    },

    async handleDelete(icao) {
        if (!icao) return;
        const confirmed = confirm(`${icao} 기종을 삭제하시겠습니까?`);
        if (!confirmed) return;

        this.showStatus('기종을 삭제하는 중입니다...', 'info');
        try {
            await api.deleteAircraftProfile(icao);
            this.showStatus('기종이 삭제되었습니다.', 'success');
            if (this.state.list?.length === 1 && this.state.page > 1) {
                this.state.page -= 1;
            }
            this.loadProfiles();
        } catch (error) {
            console.error('Aircraft profile delete failed:', error);
            this.showStatus(error?.message || '삭제 실패', 'error');
        }
    },

    toggleLoading(show) {
        if (this.loadingLayer) {
            this.loadingLayer.style.display = show ? 'flex' : 'none';
        }
    },

    toggleFormDisabled(disabled) {
        if (!this.form) return;
        Array.from(this.form.elements).forEach((el) => {
            el.disabled = disabled && el.id !== 'aircraft-cancel-edit';
        });
        if (this.cancelEditBtn && this.state.editingIcao) {
            this.cancelEditBtn.disabled = false;
        }
    },

    showStatus(message, type = 'info') {
        if (!this.statusBox) return;
        const colors = {
            info: '#3498db',
            success: '#27ae60',
            error: '#e74c3c'
        };
        this.statusBox.textContent = message;
        this.statusBox.style.color = colors[type] || '#2c3e50';
    },

    // CSV Import Methods
    initCSVImport() {
        // Use bind(this) for better compatibility
        const self = this;

        const importBtn = document.getElementById('aircraft-import-csv-btn');
        const closeBtn = document.getElementById('aircraft-import-modal-close');
        const cancelBtn = document.getElementById('aircraft-import-cancel');
        const submitBtn = document.getElementById('aircraft-import-submit');
        const csvFile = document.getElementById('aircraft-csv-file');
        const dropZone = document.getElementById('csv-drop-zone');
        const fileClick = document.getElementById('csv-file-click');
        const fileClearBtn = document.getElementById('csv-file-clear');

        if (importBtn) {
            importBtn.addEventListener('click', function() {
                self.openCSVModal();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                self.closeCSVModal();
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                self.closeCSVModal();
            });
        }

        if (fileClick) {
            fileClick.addEventListener('click', function(e) {
                e.preventDefault();
                csvFile?.click();
            });
        }

        if (csvFile) {
            csvFile.addEventListener('change', function(e) {
                self.handleFileSelect(e.target.files[0]);
            });
        }

        if (dropZone) {
            dropZone.addEventListener('dragover', function(e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });

            dropZone.addEventListener('dragleave', function(e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });

            dropZone.addEventListener('drop', function(e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
                const files = e.dataTransfer?.files;
                if (files?.[0]) {
                    self.handleFileSelect(files[0]);
                }
            });
        }

        if (fileClearBtn) {
            fileClearBtn.addEventListener('click', function() {
                self.clearCSVFile();
            });
        }

        if (submitBtn) {
            console.log('Submit button found, binding event listener');
            submitBtn.addEventListener('click', function() {
                console.log('Submit button clicked!');
                self.submitCSVImport();
            });
        } else {
            console.warn('Submit button not found - ID: aircraft-import-submit');
        }
    },

    openCSVModal() {
        const modal = document.getElementById('aircraft-import-modal');
        if (modal) {
            modal.style.display = 'flex';
            this.clearCSVFile();
        }
    },

    closeCSVModal() {
        const modal = document.getElementById('aircraft-import-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    handleFileSelect(file) {
        if (!file) return;

        // Validate file type
        if (!file.name.endsWith('.csv')) {
            alert('CSV 파일만 지원됩니다.');
            return;
        }

        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('파일 크기는 10MB 이하여야 합니다.');
            return;
        }

        this.csvImportFile = file;

        // Show file info
        const fileInfo = document.getElementById('csv-file-info');
        const fileName = document.getElementById('csv-file-name');
        const fileSize = document.getElementById('csv-file-size');
        const submitBtn = document.getElementById('aircraft-import-submit');

        if (fileInfo) fileInfo.style.display = 'block';
        if (fileName) fileName.textContent = file.name;
        if (fileSize) fileSize.textContent = (file.size / 1024).toFixed(1) + ' KB';
        if (submitBtn) submitBtn.disabled = false;
    },

    clearCSVFile() {
        this.csvImportFile = null;

        const csvFile = document.getElementById('aircraft-csv-file');
        const fileInfo = document.getElementById('csv-file-info');
        const submitBtn = document.getElementById('aircraft-import-submit');

        if (csvFile) csvFile.value = '';
        if (fileInfo) fileInfo.style.display = 'none';
        if (submitBtn) submitBtn.disabled = true;

        // Clear progress and result
        const progress = document.getElementById('csv-import-progress');
        const result = document.getElementById('csv-import-result');
        if (progress) progress.style.display = 'none';
        if (result) result.style.display = 'none';
    },

    async submitCSVImport() {
        if (!this.csvImportFile) {
            alert('파일을 선택해주세요.');
            return;
        }

        const mode = document.querySelector('input[name="aircraft-import-mode"]:checked')?.value || 'replace';
        const recalcWaypoints = document.getElementById('aircraft-recalc-waypoints')?.checked || false;

        const formData = new FormData();
        formData.append('file', this.csvImportFile);
        formData.append('mode', mode);
        formData.append('recalculate_waypoints', recalcWaypoints ? 'true' : 'false');

        const submitBtn = document.getElementById('aircraft-import-submit');
        const progress = document.getElementById('csv-import-progress');
        const result = document.getElementById('csv-import-result');

        if (submitBtn) submitBtn.disabled = true;
        if (progress) progress.style.display = 'block';
        if (result) result.style.display = 'none';

        try {
            const response = await fetch('/api/aircraft/import/csv', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Hide progress
            if (progress) progress.style.display = 'none';

            // Show result
            const resultBox = document.getElementById('csv-import-result-box');
            if (resultBox) {
                const stats = data.data || {};
                let gridCols = stats.waypoints_recalculated > 0 ? 'repeat(4, 1fr)' : 'repeat(3, 1fr)';
                let resultHTML = `
                    <div style="margin-bottom: 12px;">
                        <strong style="font-size: 1.1em;">가져오기 완료!</strong>
                    </div>
                    <div style="display: grid; grid-template-columns: ${gridCols}; gap: 12px; margin-top: 12px;">
                        <div style="padding: 8px; background: rgba(34, 197, 94, 0.1); border-radius: 4px;">
                            <div style="font-size: 0.85rem; color: #666; margin-bottom: 4px;">신규 등록</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #22c55e;">${stats.inserted || 0}</div>
                        </div>
                        <div style="padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 4px;">
                            <div style="font-size: 0.85rem; color: #666; margin-bottom: 4px;">업데이트</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #3b82f6;">${stats.updated || 0}</div>
                        </div>
                        <div style="padding: 8px; background: rgba(156, 163, 175, 0.1); border-radius: 4px;">
                            <div style="font-size: 0.85rem; color: #666; margin-bottom: 4px;">스킵됨</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #9ca3af;">${stats.skipped || 0}</div>
                        </div>`;
                if (stats.waypoints_recalculated > 0) {
                    resultHTML += `
                        <div style="padding: 8px; background: rgba(139, 92, 246, 0.1); border-radius: 4px;">
                            <div style="font-size: 0.85rem; color: #666; margin-bottom: 4px;">웨이포인트 재계산</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #8b5cf6;">${stats.waypoints_recalculated}</div>
                        </div>`;
                }
                resultHTML += `
                    </div>
                    <div style="margin-top: 12px; padding: 10px; background: #f0f8ff; border-radius: 4px;">
                        <small style="color: #666;">총 ${(stats.inserted || 0) + (stats.updated || 0) + (stats.skipped || 0)}건이 처리되었습니다.</small>
                    </div>
                `;
                resultBox.innerHTML = resultHTML;
                resultBox.className = 'import-result-box success';
                if (result) result.style.display = 'block';
            }

            // Reload aircraft list
            setTimeout(() => {
                this.loadProfiles();
                this.closeCSVModal();
                this.showStatus('항공기 프로필이 성공적으로 업데이트되었습니다.', 'success');
            }, 1500);

        } catch (error) {
            console.error('CSV import failed:', error);
            if (progress) progress.style.display = 'none';

            const resultBox = document.getElementById('csv-import-result-box');
            if (resultBox) {
                resultBox.innerHTML = `<strong>오류 발생:</strong> ${error.message || '파일을 가져오지 못했습니다.'}`;
                resultBox.className = 'import-result-box error';
                if (result) result.style.display = 'block';
            }

            this.showStatus(`CSV 가져오기 실패: ${error.message}`, 'error');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    }
};

window.AircraftTab = AircraftTab;
