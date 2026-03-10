from flask import Blueprint, request, jsonify
from database import get_db_connection
from psycopg2.extras import RealDictCursor
from auth import token_required  # Теперь это должно работать

favorites_bp = Blueprint('favorites', __name__)

# Добавить трек в избранное
@favorites_bp.route('/favorites', methods=['POST'])
@token_required
def add_favorite(current_user_id):
    data = request.get_json()
    track_id = data.get('track_id')
    
    if not track_id:
        return jsonify({"error": "Track ID is required"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO favorites (user_id, track_id) VALUES (%s, %s)",
            (current_user_id, track_id)
        )
        conn.commit()
        return jsonify({"message": "Track added to favorites"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Track already in favorites"}), 400
    finally:
        cur.close()
        conn.close()

# Получить все избранные треки пользователя
@favorites_bp.route('/favorites', methods=['GET'])
@token_required
def get_favorites(current_user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT t.* FROM tracks t
        JOIN favorites f ON t.id = f.track_id
        WHERE f.user_id = %s
        ORDER BY f.added_at DESC
    """, (current_user_id,))
    tracks = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tracks)

# Удалить трек из избранного
@favorites_bp.route('/favorites/<int:track_id>', methods=['DELETE'])
@token_required
def delete_favorite(current_user_id, track_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM favorites WHERE user_id = %s AND track_id = %s",
        (current_user_id, track_id)
    )
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    if deleted:
        return jsonify({"message": "Track removed from favorites"})
    else:
        return jsonify({"error": "Track not found in favorites"}), 404