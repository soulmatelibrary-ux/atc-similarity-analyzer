/**
 * API 클라이언트 - Flask 백엔드와 통신
 */

// API 베이스 URL 동적 설정 (프로토콜과 호스트는 현재 페이지와 같음, 포트는 8888)
const API_BASE_URL = (() => {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    const port = 8888; // Flask 백엔드 포트
    return `${protocol}//${hostname}:${port}/api`;
})();

/**
 * 내부용: API 기본 요청 함수
 */
function notifyAuthRequired(status, endpoint) {
    if (status === 401) {
        window.dispatchEvent(new CustomEvent('auth:required', {
            detail: { source: 'api', endpoint }
        }));
    }
}

async function _request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    try {
        const response = await fetch(url, {
            credentials: options.credentials ?? 'include',
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        // 응답 처리
        let responseData;
        try {
            responseData = await response.json();
        } catch (e) {
            responseData = null;
        }

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`;
            if (responseData && responseData.message) {
                errorMessage = responseData.message;
            } else if (responseData && responseData.error) {
                errorMessage = responseData.error;
            }

            const error = new Error(errorMessage);
            error.status = response.status;
            error.data = responseData;
            notifyAuthRequired(response.status, endpoint);
            throw error;
        }

        return responseData || {};
    } catch (error) {
        if (error && error.status === 401) {
            notifyAuthRequired(401, endpoint);
        }
        console.error(`API 요청 실패: ${endpoint}`, error.message || error);
        throw error;
    }
}

/**
 * API 네임스페이스 객체
 */
const api = {
    /**
     * 헬스 체크
     */
    async healthCheck() {
        return _request('/health', { method: 'GET' });
    },

    /**
     * 유사도 레벨 및 정의 조회
     */
    async getSimilarityLevels() {
        return _request('/similarity-levels', { method: 'GET' });
    },

    /**
     * 유사호출 판정 (단순 조회용)
     */
    async checkSimilarity(callsign1, callsign2) {
        return _request('/similarity/check', {
            method: 'POST',
            body: JSON.stringify({
                callsign1,
                callsign2
            })
        });
    },

    /**
     * 파일 업로드
     */
    async uploadFile(file, mode = 'replace') {
        const maxSize = 16 * 1024 * 1024; // 16MB
        if (file.size > maxSize) {
            throw new Error(`파일 크기가 너무 큽니다. (최대 16MB)`);
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', mode);

        const url = `${API_BASE_URL}/upload/flights`;
        
        console.log('Upload request:', {
            url,
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type,
            mode
        });

        // 타임아웃 설정
        let timeoutMs = file.size > 5 * 1024 * 1024 ? 90000 : (file.size > 1024 * 1024 ? 60000 : 30000);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                signal: controller.signal,
                credentials: 'include'
            });
            clearTimeout(timeoutId);

            let data;
            try { data = await response.json(); } catch (e) { 
                console.error('Response JSON parse error:', e);
                data = { status: 'error', message: '서버 응답 파싱 실패', response_text: await response.text() }; 
            }

            console.log('Upload response:', { status: response.status, data });

            if (!response.ok) {
                const errorMsg = data && data.message ? data.message : `Upload failed: ${response.status}`;
                console.error('Upload error:', errorMsg, data);
                throw new Error(errorMsg);
            }
            return data || {};
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error(`업로드 시간 초과 (${timeoutMs / 1000}초).`);
            }
            console.error('Upload exception:', error);
            throw error;
        }
    },

    /**
     * 시뮬레이션 실행
     */
    async runSimulation(filters = {}, minOverlapMinutes = 2) {
        return _request('/simulation/run', {
            method: 'POST',
            body: JSON.stringify({
                filters: filters,
                min_overlap_minutes: minOverlapMinutes
            })
        });
    },

    /**
     * 통계 요약 조회
     */
    async getStatisticsSummary() {
        return _request('/statistics/summary', { method: 'GET' });
    },

    /**
     * 상세 통계 조회 (페이지네이션 포함)
     */
    async getStatisticsDetailed(minOverlap = 2, page = 1, limit = 10000, eobd = null, hour = null) {
        let url = `/statistics/detailed?min_overlap_minutes=${minOverlap}&page=${page}&limit=${limit}`;
        if (eobd) {
            url += `&eobd=${encodeURIComponent(eobd)}`;
        }
        if (hour) {
            url += `&hour=${encodeURIComponent(hour)}`;
        }
        return _request(url, { method: 'GET' });
    },

    /**
     * 기간 분석 데이터 조회
     */
    async getPeriodAnalysis(startDate, endDate, minOverlap = 2) {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate,
            min_overlap_minutes: minOverlap
        });
        return _request(`/statistics/period?${params.toString()}`, { method: 'GET' });
    },

    /**
     * 업로드 진행 상황 조회
     */
    async getUploadProgress(processId) {
        return _request(`/upload/progress/${processId}`, { method: 'GET' });
    },

    /**
     * JSON 내보내기
     */
    async exportJSON() {
        return _request('/export/json', { method: 'GET' });
    },

    /**
     * 전체 항공편 조회 (페이지네이션 포함)
     */
    async getAllFlights(page = 1, limit = 50, eobd = null) {
        let url = `/flights/all?page=${page}&limit=${limit}`;
        if (eobd) {
            url += `&eobd=${encodeURIComponent(eobd)}`;
        }
        return _request(url, { method: 'GET' });
    },

    /**
     * 사용 가능한 항공편 날짜 목록 조회
     */
    async getAvailableDates() {
        return _request('/flights/dates', { method: 'GET' });
    },

    /**
     * 상세 비교 정보 조회 (팝업용)
     */
    async getFlightPairDetails(flightId1, flightId2) {
        return _request(`/flights/pair-details?flight_id_1=${flightId1}&flight_id_2=${flightId2}`, { method: 'GET' });
    },

    /**
     * 데이터베이스 삭제
     * @param {string} deleteType - 'all' (전체 삭제) 또는 'date' (일자별 삭제)
     * @param {string} date - deleteType이 'date'일 때 삭제할 날짜 (YYYY-MM-DD)
     */
    async deleteDatabase(deleteType, date = null) {
        let url = '/database/delete?type=' + encodeURIComponent(deleteType);
        if (deleteType === 'date' && date) {
            url += '&date=' + encodeURIComponent(date);
        }
        return _request(url, { method: 'POST' });
    },

    /**
     * 단일 항공편 궤적 계산 (테스트용)
     */
    async calculateFlight(flightData) {
        return _request('/test/calculate-flight', {
            method: 'POST',
            body: JSON.stringify(flightData)
        });
    },

    /**
     * 항공기 기종 관리
     */
    async getAircraftProfiles(page = 1, perPage = 100, search = '') {
        let url = `/aircraft?page=${page}&per_page=${perPage}`;
        if (search) {
            url += `&search=${encodeURIComponent(search)}`;
        }
        return _request(url, { method: 'GET' });
    },

    async getAircraftProfile(icaoCode) {
        return _request(`/aircraft/${encodeURIComponent(icaoCode)}`, { method: 'GET' });
    },

    async createAircraftProfile(profile) {
        return _request('/aircraft', {
            method: 'POST',
            body: JSON.stringify(profile)
        });
    },

    async updateAircraftProfile(icaoCode, profile) {
        return _request(`/aircraft/${encodeURIComponent(icaoCode)}`, {
            method: 'PUT',
            body: JSON.stringify(profile)
        });
    },

    async deleteAircraftProfile(icaoCode) {
        return _request(`/aircraft/${encodeURIComponent(icaoCode)}`, {
            method: 'DELETE'
        });
    },

    /**
     * 인증 - 로그인
     */
    async login(email, password) {
        return _request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },

    /**
     * 인증 - 로그아웃
     */
    async logout() {
        return _request('/auth/logout', {
            method: 'POST'
        });
    },

    /**
     * 인증 - 세션 확인
     */
    async getSession() {
        return _request('/auth/session', { method: 'GET' });
    }
};
