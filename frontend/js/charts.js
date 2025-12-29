/**
 * 차트 초기화 및 관리 - Chart.js 통합
 */

// 차트 인스턴스 저장
const charts = {
    sidebarRiskChart: null,
    hourlyChart: null,
    dailyChart: null
};

/**
 * 위험도 분포 차트 초기화
 */
function initializeRiskChart(ctx, statistics) {
    if (!statistics) {
        ctx.textContent = '데이터를 불러오세요';
        return;
    }

    const riskDist = statistics.risk_distribution || {
        CRITICAL: 0,
        HIGH: 0,
        MEDIUM: 0,
        LOW: 0
    };

    const colors = {
        CRITICAL: '#c0392b',
        HIGH: '#e74c3c',
        MEDIUM: '#f39c12',
        LOW: '#27ae60'
    };

    const labels = Object.keys(riskDist);
    const data = Object.values(riskDist);
    const backgroundColors = labels.map(label => colors[label]);

    // 기존 차트 제거
    if (charts.sidebarRiskChart) {
        charts.sidebarRiskChart.destroy();
    }

    charts.sidebarRiskChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 시간대별 이벤트 차트 초기화
 */
/**
 * 시간대별/일자별 이벤트 차트 초기화
 */
function initializeHourlyChart(ctx, statistics) {
    if (!statistics) {
        ctx.textContent = '데이터를 불러오세요';
        return;
    }

    const hourlyByDate = statistics.hourly_distribution_by_date || {};
    const dates = Object.keys(hourlyByDate).sort();

    // 24시간 라벨 생성 (00:00 ~ 23:00) - UTC 시간대
    const labels = [];
    for (let hour = 0; hour < 24; hour++) {
        labels.push(`${String(hour).padStart(2, '0')}:00`);
    }

    // 데이터셋 생성 (일자별로)
    const datasets = dates.map((date, index) => {
        const data = [];
        for (let hour = 0; hour < 24; hour++) {
            const hourKey = String(hour).padStart(2, '0');
            data.push(hourlyByDate[date][hourKey] || 0);
        }

        // 색상 팔레트 (순환)
        const palette = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f1c40f', '#e67e22'];
        const color = palette[index % palette.length];

        return {
            label: date,
            data: data,
            backgroundColor: color,
            borderColor: color,
            borderWidth: 1,
            borderRadius: 4,
            maxBarThickness: 30
        };
    });

    // 데이터가 없는 경우 빈 차트 표시 방지 (옵션)
    if (datasets.length === 0) {
        datasets.push({
            label: '데이터 없음',
            data: new Array(24).fill(0),
            backgroundColor: '#bdc3c7'
        });
    }

    // 기존 차트 제거
    if (charts.hourlyChart) {
        charts.hourlyChart.destroy();
    }

    charts.hourlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // 높이 조절 가능하도록
            onClick: (event, activeElements) => {
                // 클릭된 막대의 시간 추출
                if (activeElements && activeElements.length > 0) {
                    const index = activeElements[0].index;
                    const hour = String(index).padStart(2, '0');

                    console.log(`차트 클릭: ${hour}:00 시간대`);

                    // UI에서 시간대 필터링 함수 호출
                    if (typeof filterByTimeRange === 'function') {
                        filterByTimeRange(hour);
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(44, 62, 80, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#ecf0f1',
                    borderColor: '#3498db',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        title: function (context) {
                            return `🕐 ${context[0].label} UTC`;
                        },
                        label: function (context) {
                            const date = context.dataset.label;
                            const count = context.parsed.y;
                            if (count === 0) {
                                return `${date}: 항공기 없음`;
                            }
                            return `${date}: 항공기 ${count}건`;
                        },
                        footer: function (context) {
                            const total = context.reduce((sum, item) => sum + item.parsed.y, 0);
                            if (total === 0) return '';
                            return `\n💡 클릭하여 해당 시간대 유사호출 조회`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        borderDash: [2, 4]
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

/**
 * 일자별 이벤트 차트 초기화 (최대 24일)
 */
function initializeDailyChart(ctx, statistics) {
    if (!statistics) {
        ctx.textContent = '데이터를 불러오세요';
        return;
    }

    const hourlyByDate = statistics.hourly_distribution_by_date || {};
    const dates = Object.keys(hourlyByDate).sort().reverse(); // 최신 순으로 정렬

    // 최대 24일까지만 표시
    const displayDates = dates.slice(0, 24);

    // 일자별 합계 계산
    const dailyData = displayDates.map(date => {
        const hourData = hourlyByDate[date] || {};
        const total = Object.values(hourData).reduce((sum, count) => sum + count, 0);
        return { date, total };
    }).reverse(); // 오래된 날짜부터 표시

    const labels = dailyData.map(d => d.date);
    const data = dailyData.map(d => d.total);

    // 최대값을 기준으로 색상 진하기 조정
    const maxValue = Math.max(...data, 1);
    const colors = data.map(value => {
        const intensity = value / maxValue;
        const r = Math.round(100 + (226 - 100) * intensity); // #647eea to #e74c3c
        const g = Math.round(126 + (76 - 126) * intensity);
        const b = Math.round(234 + (60 - 234) * intensity);
        return `rgb(${r}, ${g}, ${b})`;
    });

    // 기존 차트 제거
    if (charts.dailyChart) {
        charts.dailyChart.destroy();
    }

    charts.dailyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '유사호출 감지 건수',
                data: data,
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 1,
                borderRadius: 6,
                maxBarThickness: 50
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: data.length > 15 ? 'y' : 'x', // 많으면 가로 차트
            onClick: (event, activeElements) => {
                // 클릭된 막대의 날짜 추출
                if (activeElements && activeElements.length > 0) {
                    const index = activeElements[0].index;
                    const selectedDate = labels[index];
                    console.log(`차트 클릭: ${selectedDate} 일자`);

                    // UI에서 날짜 필터링 함수 호출
                    if (typeof filterByDate === 'function') {
                        filterByDate(selectedDate);
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        color: '#2c3e50'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(44, 62, 80, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#ecf0f1',
                    borderColor: '#667eea',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        title: function (context) {
                            return `📅 ${context[0].label}`;
                        },
                        label: function (context) {
                            const count = context.parsed.x || context.parsed.y;
                            if (count === 0) {
                                return '유사호출 없음';
                            }
                            return `유사호출: ${count}건`;
                        },
                        footer: function (context) {
                            const count = context[0].parsed.x || context[0].parsed.y;
                            if (count === 0) return '';
                            return `\n💡 클릭하여 해당 일자 상세 조회`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        borderDash: [2, 4]
                    }
                },
                x: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        display: false
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: data.length > 15 ? 'y' : 'x',
                intersect: false
            }
        }
    });
}

/**
 * 차트 업데이트
 */
function updateCharts(statistics) {
    if (!statistics) return;

    // 기존 차트 파괴 (필터 적용 시 중복 렌더링 방지)
    destroyCharts();

    // 위험도 분포 (텍스트 형식 - 사이드바) - 주석처리: 일자별 통계와 중복
    // loadRiskDistributionStats(statistics);

    // 시간대별 공존 현황 차트 (timeChart)
    const hourlyChartCanvas = document.getElementById('timeChart');
    if (hourlyChartCanvas) {
        initializeHourlyChart(hourlyChartCanvas, statistics);
    }

    // 일자별 공존 현황 차트 (dailyChart)
    const dailyChartCanvas = document.getElementById('dailyChart');
    if (dailyChartCanvas) {
        initializeDailyChart(dailyChartCanvas, statistics);
    }

    // 항공사 통계 업데이트 - 주석처리: 일자별 통계와 중복
    // loadAirlineStats(statistics);
}

/**
 * 차트 정리
 */
function destroyCharts() {
    try {
        if (charts.sidebarRiskChart) {
            charts.sidebarRiskChart.destroy();
            charts.sidebarRiskChart = null;
        }

        if (charts.hourlyChart) {
            charts.hourlyChart.destroy();
            charts.hourlyChart = null;
        }

        if (charts.dailyChart) {
            charts.dailyChart.destroy();
            charts.dailyChart = null;
        }

        // Canvas 요소 초기화 (중요: 차트 재생성 시 필수)
        const timeChartCanvas = document.getElementById('timeChart');
        if (timeChartCanvas) {
            const ctx = timeChartCanvas.getContext('2d');
            ctx.clearRect(0, 0, timeChartCanvas.width, timeChartCanvas.height);
        }

        const dailyChartCanvas = document.getElementById('dailyChart');
        if (dailyChartCanvas) {
            const ctx = dailyChartCanvas.getContext('2d');
            ctx.clearRect(0, 0, dailyChartCanvas.width, dailyChartCanvas.height);
        }

        console.log('차트 파괴 및 초기화 완료');
    } catch (error) {
        console.error('차트 정리 중 오류:', error);
    }
}

/**
 * 위험도 분포 통계 (텍스트 형식)
 */
function loadRiskDistributionStats(statistics) {
    try {
        const container = document.getElementById('sidebar-risk-stats');
        if (!container) return;

        if (!statistics || !statistics.recent_similarities) {
            container.innerHTML = '<p style="color: #999; text-align: center;">데이터 없음</p>';
            return;
        }

        // 위험도별 카운트 계산
        const riskCounts = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        };

        // 모든 유사호출의 유사도 레벨로부터 위험도 매핑 (v2.1 기준)
        statistics.recent_similarities.forEach(sim => {
            const level = sim.similarity_level || '';
            if (level.startsWith('LEVEL_5')) {
                riskCounts['HIGH']++;
            } else if (level.startsWith('LEVEL_4')) {
                riskCounts['MEDIUM']++;
            } else if (level.startsWith('LEVEL_3')) {
                riskCounts['LOW']++;
            }
        });

        // 0이 아닌 항목만 필터링하여 정렬
        const riskItems = Object.entries(riskCounts)
            .filter(([_, count]) => count > 0)
            .sort((a, b) => {
                const order = { 'HIGH': 0, 'MEDIUM': 1, 'LOW': 2, 'CRITICAL': 3 };
                return (order[a[0]] || 99) - (order[b[0]] || 99);
            })
            .slice(0, 5);  // 상위 5개만

        if (riskItems.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center;">데이터 없음</p>';
            return;
        }

        // HTML 생성 (간단한 텍스트 형식)
        container.innerHTML = riskItems.map(([level, count]) => {
            const colorMap = {
                'CRITICAL': '#c0392b',
                'HIGH': '#e74c3c',
                'MEDIUM': '#f39c12',
                'LOW': '#27ae60'
            };
            const color = colorMap[level] || '#999';

            return `<div style="margin-bottom: 8px;">
                <span style="color: ${color}; font-weight: bold;">●</span>
                <span style="color: #2c3e50;">level-${level}: ${count}건</span>
            </div>`;
        }).join('');

    } catch (error) {
        console.error('위험도 분포 통계 로드 오류:', error);
        const container = document.getElementById('sidebar-risk-stats');
        if (container) {
            container.innerHTML = '<p style="color: #999; text-align: center;">데이터 로드 실패</p>';
        }
    }
}

/**
 * 항공사별 유사호출 통계
 */
function loadAirlineStats(statistics) {
    try {
        const container = document.getElementById('sidebar-airline-stats');
        if (!container) return;

        if (!statistics || !statistics.recent_similarities || statistics.recent_similarities.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center;">데이터 없음</p>';
            return;
        }

        // 항공사별(콜사인 앞 3글자) 유사호출 수 계산
        const airlineStats = {};
        statistics.recent_similarities.forEach(sim => {
            const airline1 = (sim.callsign1 || sim.callsign_1 || '').substring(0, 3);
            const airline2 = (sim.callsign2 || sim.callsign_2 || '').substring(0, 3);

            if (airline1) {
                airlineStats[airline1] = (airlineStats[airline1] || 0) + 1;
            }
            if (airline2 && airline2 !== airline1) {
                airlineStats[airline2] = (airlineStats[airline2] || 0) + 1;
            }
        });

        // 상위 5개 정렬
        const topAirlines = Object.entries(airlineStats)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);

        if (topAirlines.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center;">데이터 없음</p>';
            return;
        }

        // HTML 생성
        container.innerHTML = topAirlines.map((entry, idx) => {
            const [airline, count] = entry;
            const barWidth = (count / topAirlines[0][1]) * 100;  // 첫 번째 항공사 기준 100%

            return `
                <div style="margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <strong style="color: #2c3e50;">${airline}</strong>
                        <span style="color: #e74c3c; font-weight: bold;">${count}건</span>
                    </div>
                    <div style="background: #eee; height: 20px; border-radius: 3px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #e74c3c, #e67e22); height: 100%; width: ${barWidth}%; transition: width 0.3s;"></div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('항공사 통계 로드 오류:', error);
        const container = document.getElementById('sidebar-airline-stats');
        if (container) {
            container.innerHTML = '<p style="color: #999; text-align: center;">데이터 로드 실패</p>';
        }
    }
}
