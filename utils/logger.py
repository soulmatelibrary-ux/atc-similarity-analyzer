"""
로깅 설정
"""
import logging
import os
from datetime import datetime
from utils.constants import LOG_LEVEL, LOG_FILE

def setup_logger(name):
    """
    로거 설정

    Args:
        name: 로거 이름 (보통 __name__)

    Returns:
        logging.Logger: 설정된 로거 객체
    """

    # 로그 폴더 생성
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로거 객체 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # 로그 포맷 정의
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 파일 핸들러 (파일에 기록)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(getattr(logging, LOG_LEVEL))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러 (화면에 출력)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 기본 로거
logger = setup_logger(__name__)
