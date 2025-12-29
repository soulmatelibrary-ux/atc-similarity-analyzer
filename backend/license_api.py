"""
라이선스 관련 API 엔드포인트
"""

from flask import Blueprint, jsonify, request
from utils.license_manager import get_license_manager

license_bp = Blueprint('license', __name__, url_prefix='/api/license')


@license_bp.route('/info', methods=['GET'])
def get_license_info():
    """라이선스 정보 조회"""
    manager = get_license_manager()
    return jsonify({
        'status': 'success',
        'data': manager.get_license_info()
    }), 200


@license_bp.route('/limits', methods=['GET'])
def get_license_limits():
    """라이선스 기능 제한 조회"""
    manager = get_license_manager()
    limits = manager.get_limits()
    return jsonify({
        'status': 'success',
        'data': {
            'license_type': manager.license_type,
            'limits': limits
        }
    }), 200


@license_bp.route('/status', methods=['GET'])
def get_license_status():
    """라이선스 상태 조회"""
    manager = get_license_manager()
    return jsonify({
        'status': 'success',
        'data': {
            'is_valid': manager.is_valid,
            'is_development': manager.is_development(),
            'is_commercial': manager.is_commercial(),
            'message': manager.message,
            'limits': manager.get_limits()
        }
    }), 200


# 관리자 라이선스 관리 API
admin_license_bp = Blueprint('admin_license', __name__, url_prefix='/api/admin/license')


@admin_license_bp.route('/generate', methods=['POST'])
def generate_license():
    """라이선스 생성 (관리자용)"""
    try:
        data = request.get_json()

        # 필수 파라미터 확인
        organization = data.get('organization')
        days = data.get('days', 365)

        if not organization:
            return jsonify({
                'status': 'error',
                'message': 'Organization name is required'
            }), 400

        # 일수 범위 확인
        if not isinstance(days, int) or days < 1 or days > 3650:
            return jsonify({
                'status': 'error',
                'message': 'Days must be between 1 and 3650'
            }), 400

        # 라이선스 생성
        manager = get_license_manager()
        license_data = manager.generate_license_key(organization, days)

        return jsonify({
            'status': 'success',
            'data': license_data
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'License generation failed: {str(e)}'
        }), 500
