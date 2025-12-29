/**
 * 비행계획서 모델링 테스트 탭 로직
 */

const TestTab = {
    init() {
        console.log("TestTab initialized");
        this.cacheDOM();
        this.bindEvents();
        this.setDefaultDate();
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
