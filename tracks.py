from flask import Blueprint, jsonify, request
from database import get_db_connection
from psycopg2.extras import RealDictCursor

tracks_bp = Blueprint('tracks', __name__)

@tracks_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tracks ORDER BY RANDOM() LIMIT 10")
    tracks = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tracks)

@tracks_bp.route('/tracks', methods=['GET'])
def get_all_tracks():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tracks ORDER BY title")
    tracks = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tracks)

@tracks_bp.route('/tracks/<int:track_id>', methods=['GET'])
def get_track(track_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tracks WHERE id = %s", (track_id,))
    track = cur.fetchone()
    cur.close()
    conn.close()
    
    if track:
        return jsonify(track)
    else:
        return jsonify({"error": "Track not found"}), 404