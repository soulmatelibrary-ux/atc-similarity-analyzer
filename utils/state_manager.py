"""
상태 관리 모듈 - JSON 파일 기반 영속 저장소
"""
import os
import json
import threading
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StateManager:
    """JSON 파일 기반 상태 관리자"""

    def __init__(self, state_file='state.json'):
        """
        상태 관리자 초기화

        Args:
            state_file: 상태를 저장할 JSON 파일 경로
        """
        self.state_file = state_file
        self.lock = threading.Lock()  # 스레드 안전성
        self.default_state = {
            'flights': [],
            'coexistences': [],
            'statistics': None,
            'last_updated': None
        }

        # 파일 디렉토리 생성
        os.makedirs(os.path.dirname(state_file) if os.path.dirname(state_file) else '.', exist_ok=True)

        # 기존 파일 로드 또는 새로 생성
        if not os.path.exists(state_file):
            self._save_state(self.default_state)
            logger.info(f"상태 파일 생성: {state_file}")

    def _load_state(self):
        """
        JSON 파일에서 상태 로드

        Returns:
            dict: 상태 정보
        """
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    return state
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"상태 파일 읽기 오류: {e}")

        return self.default_state.copy()

    def _save_state(self, state):
        """
        상태를 JSON 파일에 저장

        Args:
            state: 저장할 상태 정보
        """
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"상태 파일 저장 오류: {e}")

    def get(self, key, default=None):
        """
        상태에서 값 조회

        Args:
            key: 조회할 키
            default: 기본값

        Returns:
            조회한 값
        """
        with self.lock:
            state = self._load_state()
            return state.get(key, default)

    def set(self, key, value):
        """
        상태에 값 저장

        Args:
            key: 저장할 키
            value: 저장할 값
        """
        with self.lock:
            state = self._load_state()
            state[key] = value
            state['last_updated'] = datetime.now().isoformat()
            self._save_state(state)

    def update(self, updates):
        """
        여러 값 동시 업데이트

        Args:
            updates: 업데이트할 키-값 딕셔너리
        """
        with self.lock:
            state = self._load_state()
            state.update(updates)
            state['last_updated'] = datetime.now().isoformat()
            self._save_state(state)

    def reset(self):
        """
        상태 초기화
        """
        with self.lock:
            self._save_state(self.default_state.copy())
            logger.info("상태 초기화됨")

    def get_all(self):
        """
        전체 상태 조회

        Returns:
            dict: 전체 상태
        """
        with self.lock:
            return self._load_state()

    def clear_key(self, key):
        """
        특정 키 삭제

        Args:
            key: 삭제할 키
        """
        with self.lock:
            state = self._load_state()
            if key in state:
                del state[key]
            state['last_updated'] = datetime.now().isoformat()
            self._save_state(state)
