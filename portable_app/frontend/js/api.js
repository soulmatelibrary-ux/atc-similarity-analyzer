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
async function _request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    try {
        const response = await fetch(url, {
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
            throw error;
        }

        return responseData || {};
    } catch (error) {
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

        // 타임아웃 설정
        let timeoutMs = file.size > 5 * 1024 * 1024 ? 90000 : (file.size > 1024 * 1024 ? 60000 : 30000);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            let data;
            try { data = await response.json(); } catch (e) { data = null; }

            if (!response.ok) {
                throw new Error(data && data.message ? data.message : `Upload failed: ${response.status}`);
            }
            return data || {};
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error(`업로드 시간 초과 (${timeoutMs / 1000}초).`);
            }
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
    async getStatisticsDetailed(minOverlap = 2, page = 1, limit = 20, eobd = null, hour = null) {
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
     * 통계 요약 조회 (항공사별, 유사도, 콜사인10 데이터 포함)
     */
    async getStatisticsSummary() {
        return _request('/statistics/summary', { method: 'GET' });
    },

    /**
     * 항공편 고도 상승 계산 비교 결과 조회
     */
    async getClimbComparison(flightId) {
        return _request(`/flights/${flightId}/climb-comparison`, { method: 'GET' });
    },

    /**
     * 항공기 기종 프로필 목록 조회
     */
    async getAircraftProfiles() {
        return _request('/aircraft-profiles', { method: 'GET' });
    },

    /**
     * 특정 항공기 기종 프로필 조회
     */
    async getAircraftProfile(icaoCode) {
        return _request(`/aircraft-profiles/${icaoCode}`, { method: 'GET' });
    },

    /**
     * 항공기 기종 프로필 생성
     */
    async createAircraftProfile(profileData) {
        return _request('/aircraft-profiles', {
            method: 'POST',
            body: JSON.stringify(profileData)
        });
    },

    /**
     * 항공기 기종 프로필 업데이트
     */
    async updateAircraftProfile(icaoCode, profileData) {
        return _request(`/aircraft-profiles/${icaoCode}`, {
            method: 'PUT',
            body: JSON.stringify(profileData)
        });
    },

    /**
     * 항공기 기종 프로필 삭제
     */
    async deleteAircraftProfile(icaoCode) {
        return _request(`/aircraft-profiles/${icaoCode}`, {
            method: 'DELETE'
        });
    },

    /**
     * 모델링 테스트: 기종 고려 고도 상승 계산
     */
    async calculateFlight(flightData) {
        return _request('/test/calculate-flight', {
            method: 'POST',
            body: JSON.stringify(flightData)
        });
    }
};
