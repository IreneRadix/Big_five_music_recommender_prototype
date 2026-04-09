from flask import Blueprint, request, jsonify, render_template
from auth import token_required
from admin_service import (
    get_overview_stats,
    get_popular_tracks,
    get_genre_analysis,
    get_user_segments,
    get_users_list,
    toggle_admin_status
)
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/api/stats/overview', methods=['GET'])
def overview_stats():
    try:
        result = get_overview_stats()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Overview stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/stats/popular-tracks', methods=['GET'])
def popular_tracks():
    limit = request.args.get('limit', 20, type=int)
    filter_type = request.args.get('filter', 'overall')
    try:
        result = get_popular_tracks(limit, filter_type)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Popular tracks error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/stats/genre-analysis', methods=['GET'])
def genre_analysis():
    try:
        result = get_genre_analysis()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Genre analysis error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/stats/user-segments', methods=['GET'])
def user_segments():
    try:
        result = get_user_segments()
        return jsonify(result)
    except Exception as e:
        logger.error(f"User segments error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/users', methods=['GET'])
def users_list():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    try:
        result = get_users_list(page, per_page, search)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Users list error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/users/<int:user_id>/toggle-admin', methods=['POST'])
def toggle_admin(user_id):
    try:
        
        result = toggle_admin_status(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Toggle admin error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500