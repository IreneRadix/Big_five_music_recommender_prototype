from flask import Blueprint, request, jsonify
from database import get_db_connection
from psycopg2.extras import RealDictCursor
from auth import token_required
import logging

logger = logging.getLogger(__name__)
history_bp = Blueprint('history', __name__)

@history_bp.route('/history', methods=['GET'])
@token_required
def get_history(current_user_id):
    """Получить историю прослушиваний текущего пользователя"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT lh.id, lh.track_id, lh.played_at,
                   t.title, t.artist, t.genre, t.cover_url, t.file_url
            FROM listening_history lh
            JOIN tracks t ON lh.track_id = t.id
            WHERE lh.user_id = %s
            ORDER BY lh.played_at DESC
        """, (current_user_id,))
        history = cur.fetchall()
        return jsonify(history)
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@history_bp.route('/history', methods=['POST'])
@token_required
def add_to_history(current_user_id):
    """Добавить запись о прослушивании (всегда новая запись)"""
    data = request.get_json()
    track_id = data.get('track_id')
    if not track_id:
        return jsonify({"error": "track_id is required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        
        cur.execute("""
            INSERT INTO listening_history (user_id, track_id, played_at)
            VALUES (%s, %s, NOW())
        """, (current_user_id, track_id))
        conn.commit()
        return jsonify({"message": "Track added to history"}), 201
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка добавления в историю: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@history_bp.route('/history/<int:track_id>', methods=['DELETE'])
@token_required
def remove_from_history(current_user_id, track_id):
    """Удалить конкретный трек из истории (удаляется первое вхождение или все?)"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        
        cur.execute("""
            DELETE FROM listening_history
            WHERE user_id = %s AND track_id = %s
        """, (current_user_id, track_id))
        deleted = cur.rowcount
        conn.commit()
        if deleted:
            return jsonify({"message": "Track(s) removed from history"})
        else:
            return jsonify({"error": "Track not found in history"}), 404
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка удаления из истории: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@history_bp.route('/history', methods=['DELETE'])
@token_required
def clear_history(current_user_id):
    """Очистить всю историю пользователя"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM listening_history WHERE user_id = %s", (current_user_id,))
        deleted = cur.rowcount
        conn.commit()
        return jsonify({"message": f"History cleared, {deleted} records deleted"})
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка очистки истории: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()