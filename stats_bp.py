from flask import Blueprint, jsonify
from database import get_db_connection
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)
stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/user_stats_full/<username>', methods=['GET'])
def get_user_stats_full(username):
    """Получить полную статистику пользователя из материализованного представления"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                total_plays,
                unique_artists,
                total_listening_time,
                plays_by_mood,
                favorites_by_mood,
                top_artists,
                top_genres
            FROM user_stats_mv
            WHERE username = %s
        """, (username,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify({
                'success': False,
                'error': f'Пользователь {username} не найден или статистика отсутствует'
            }), 404
        
        stats = {
            'all_time': {
                'total_plays': row['total_plays'],
                'unique_artists': row['unique_artists'],
                'total_listening_time': row['total_listening_time'],
                'plays_by_mood': row['plays_by_mood'],
                'favorites_by_mood': row['favorites_by_mood'],
                'top_artists': row['top_artists'],
                'top_genres': row['top_genres'],
                'favorites_count': 0  
            }
            
        }
        
        conn2 = get_db_connection()
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM favorites f JOIN users u ON u.id = f.user_id WHERE u.username = %s", (username,))
        fav_count = cur2.fetchone()[0]
        cur2.close()
        conn2.close()
        stats['all_time']['favorites_count'] = fav_count
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики для {username}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500