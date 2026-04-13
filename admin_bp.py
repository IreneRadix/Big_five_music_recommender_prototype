from flask import Blueprint, request, jsonify, render_template
from database import get_db_connection
from psycopg2.extras import RealDictCursor
from auth import token_required
from functools import wraps
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Получаем user_id из токена
        from flask import request
        import jwt
        from flask import current_app
        
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid token format"}), 401
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = data['user_id']
            
            # Проверяем, является ли пользователь администратором
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if not result or not result[0]:
                return jsonify({"error": "Admin access required"}), 403
                
        except Exception as e:
            return jsonify({"error": str(e)}), 401
            
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
def admin_dashboard():
    """Страница админ-панели"""
    return render_template('admin/dashboard.html')


@admin_bp.route('/api/stats/overview', methods=['GET'])
@admin_required
def get_overview_stats():
    """Получить общую статистику"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        stats = {}
        
        # Общее количество пользователей
        cur.execute("SELECT COUNT(*) as total FROM users")
        stats['total_users'] = cur.fetchone()['total']
        
        # Активные пользователи (заходили за последние 7 дней)
        cur.execute("""
            SELECT COUNT(DISTINCT user_id) as active 
            FROM listening_history 
            WHERE played_at > NOW() - INTERVAL '7 days'
        """)
        stats['active_users'] = cur.fetchone()['active']
        
        # Общее количество треков
        cur.execute("SELECT COUNT(*) as total FROM tracks")
        stats['total_tracks'] = cur.fetchone()['total']
        
        # Общее количество прослушиваний
        cur.execute("SELECT COUNT(*) as total FROM listening_history")
        stats['total_listens'] = cur.fetchone()['total']
        
        # Среднее количество избранных треков на пользователя
        cur.execute("""
            SELECT AVG(fav_count) as avg_favorites 
            FROM (
                SELECT user_id, COUNT(*) as fav_count 
                FROM favorites 
                GROUP BY user_id
            ) t
        """)
        result = cur.fetchone()
        stats['avg_favorites_per_user'] = round(result['avg_favorites'] or 0, 2)
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/api/stats/popular-tracks', methods=['GET'])
@admin_required
def get_popular_tracks_stats():
    """Получить статистику по популярным трекам"""
    limit = request.args.get('limit', 20, type=int)
    filter_type = request.args.get('filter', 'overall')  # overall, by_age, by_gender
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if filter_type == 'overall':
            # Общая популярность треков
            cur.execute("""
                SELECT 
                    t.id,
                    t.title,
                    t.artist,
                    t.genre,
                    t.cover_url,
                    COUNT(f.user_id) as favorites_count,
                    COUNT(lh.id) as listens_count,
                    ROUND(AVG(CASE WHEN f.user_id IS NOT NULL THEN 1 ELSE 0 END) * 100, 2) as like_rate
                FROM tracks t
                LEFT JOIN favorites f ON t.id = f.track_id
                LEFT JOIN listening_history lh ON t.id = lh.track_id
                GROUP BY t.id, t.title, t.artist, t.genre, t.cover_url
                ORDER BY favorites_count DESC, listens_count DESC
                LIMIT %s
            """, (limit,))
            
        elif filter_type == 'by_age':
            # Популярность по возрастным группам
            cur.execute("""
                WITH user_ages AS (
                    SELECT 
                        u.id as user_id,
                        CASE 
                            WHEN uf.age < 25 THEN '18-24'
                            WHEN uf.age BETWEEN 25 AND 34 THEN '25-34'
                            WHEN uf.age BETWEEN 35 AND 44 THEN '35-44'
                            WHEN uf.age BETWEEN 45 AND 54 THEN '45-54'
                            ELSE '55+'
                        END as age_group
                    FROM users u
                    JOIN user_features uf ON u.id = uf.user_id
                    WHERE uf.age IS NOT NULL
                ),
                track_stats AS (
                    SELECT 
                        t.id,
                        t.title,
                        t.artist,
                        t.genre,
                        ua.age_group,
                        COUNT(DISTINCT f.user_id) as favorites_count
                    FROM tracks t
                    CROSS JOIN (SELECT DISTINCT age_group FROM user_ages) ag
                    LEFT JOIN favorites f ON t.id = f.track_id
                    LEFT JOIN user_ages ua ON f.user_id = ua.user_id
                    GROUP BY t.id, t.title, t.artist, t.genre, ua.age_group
                )
                SELECT * FROM track_stats
                WHERE favorites_count > 0
                ORDER BY favorites_count DESC
                LIMIT %s
            """, (limit,))
            
        elif filter_type == 'by_gender':
            # Популярность по полу
            cur.execute("""
                SELECT 
                    t.id,
                    t.title,
                    t.artist,
                    t.genre,
                    uf.gender,
                    COUNT(DISTINCT f.user_id) as favorites_count
                FROM tracks t
                JOIN favorites f ON t.id = f.track_id
                JOIN user_features uf ON f.user_id = uf.user_id
                WHERE uf.gender IS NOT NULL
                GROUP BY t.id, t.title, t.artist, t.genre, uf.gender
                ORDER BY favorites_count DESC
                LIMIT %s
            """, (limit,))
        
        tracks = cur.fetchall()
        return jsonify({'success': True, 'tracks': tracks, 'filter': filter_type})
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики треков: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/api/stats/genre-analysis', methods=['GET'])
@admin_required
def get_genre_analysis():
    """Анализ популярности жанров"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Популярность жанров по возрастным группам
        cur.execute("""
            WITH user_age_groups AS (
                SELECT 
                    u.id as user_id,
                    CASE 
                        WHEN uf.age < 25 THEN '18-24'
                        WHEN uf.age BETWEEN 25 AND 34 THEN '25-34'
                        WHEN uf.age BETWEEN 35 AND 44 THEN '35-44'
                        WHEN uf.age BETWEEN 45 AND 54 THEN '45-54'
                        ELSE '55+'
                    END as age_group
                FROM users u
                JOIN user_features uf ON u.id = uf.user_id
                WHERE uf.age IS NOT NULL
            )
            SELECT 
                t.genre,
                uag.age_group,
                COUNT(DISTINCT f.user_id) as listeners_count,
                COUNT(*) as favorites_count
            FROM tracks t
            JOIN favorites f ON t.id = f.track_id
            JOIN user_age_groups uag ON f.user_id = uag.user_id
            WHERE t.genre IS NOT NULL AND t.genre != ''
            GROUP BY t.genre, uag.age_group
            ORDER BY t.genre, favorites_count DESC
        """)
        
        genre_by_age = cur.fetchall()
        
        # Популярность жанров по полу
        cur.execute("""
            SELECT 
                t.genre,
                uf.gender,
                COUNT(DISTINCT f.user_id) as listeners_count,
                COUNT(*) as favorites_count
            FROM tracks t
            JOIN favorites f ON t.id = f.track_id
            JOIN user_features uf ON f.user_id = uf.user_id
            WHERE t.genre IS NOT NULL AND t.genre != ''
                AND uf.gender IS NOT NULL
            GROUP BY t.genre, uf.gender
            ORDER BY t.genre, favorites_count DESC
        """)
        
        genre_by_gender = cur.fetchall()
        
        # Общая популярность жанров
        cur.execute("""
            SELECT 
                t.genre,
                COUNT(DISTINCT f.user_id) as unique_listeners,
                COUNT(*) as total_favorites,
                ROUND(AVG(CASE 
                    WHEN uf.extraversion > 3 THEN 'Экстраверт'
                    ELSE 'Интроверт'
                END) OVER (PARTITION BY t.genre), 2) as personality_tendency
            FROM tracks t
            JOIN favorites f ON t.id = f.track_id
            JOIN user_features uf ON f.user_id = uf.user_id
            WHERE t.genre IS NOT NULL AND t.genre != ''
            GROUP BY t.genre
            ORDER BY total_favorites DESC
        """)
        
        overall_genre = cur.fetchall()
        
        return jsonify({
            'success': True,
            'genre_by_age': genre_by_age,
            'genre_by_gender': genre_by_gender,
            'overall_genre': overall_genre
        })
        
    except Exception as e:
        logger.error(f"Ошибка анализа жанров: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/api/stats/user-segments', methods=['GET'])
@admin_required
def get_user_segments():
    """Получить сегментацию пользователей"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Распределение по возрасту
        cur.execute("""
            SELECT 
                CASE 
                    WHEN age < 25 THEN '18-24'
                    WHEN age BETWEEN 25 AND 34 THEN '25-34'
                    WHEN age BETWEEN 35 AND 44 THEN '35-44'
                    WHEN age BETWEEN 45 AND 54 THEN '45-54'
                    ELSE '55+'
                END as age_group,
                COUNT(*) as count
            FROM user_features
            WHERE age IS NOT NULL
            GROUP BY age_group
            ORDER BY age_group
        """)
        age_distribution = cur.fetchall()
        
        # Распределение по полу
        cur.execute("""
            SELECT 
                gender,
                COUNT(*) as count
            FROM user_features
            WHERE gender IS NOT NULL
            GROUP BY gender
        """)
        gender_distribution = cur.fetchall()
        
        # Распределение по типам личности (экстраверсия)
        cur.execute("""
            SELECT 
                CASE 
                    WHEN extraversion >= 4 THEN 'Экстраверты'
                    WHEN extraversion <= 2 THEN 'Интроверты'
                    ELSE 'Амбиверты'
                END as personality_type,
                COUNT(*) as count,
                ROUND(AVG(extraversion), 2) as avg_extraversion
            FROM user_features
            WHERE extraversion IS NOT NULL
            GROUP BY personality_type
            ORDER BY avg_extraversion DESC
        """)
        personality_distribution = cur.fetchall()
        
        # Распределение по открытости опыту
        cur.execute("""
            SELECT 
                CASE 
                    WHEN openness >= 4 THEN 'Высокая открытость'
                    WHEN openness <= 2 THEN 'Низкая открытость'
                    ELSE 'Средняя открытость'
                END as openness_type,
                COUNT(*) as count,
                ROUND(AVG(openness), 2) as avg_openness
            FROM user_features
            WHERE openness IS NOT NULL
            GROUP BY openness_type
            ORDER BY avg_openness DESC
        """)
        openness_distribution = cur.fetchall()
        
        # Топ жанров для каждого типа личности
        cur.execute("""
            WITH user_personality AS (
                SELECT 
                    u.id as user_id,
                    CASE 
                        WHEN uf.extraversion >= 4 THEN 'Экстраверт'
                        WHEN uf.extraversion <= 2 THEN 'Интроверт'
                        ELSE 'Амбиверт'
                    END as personality
                FROM users u
                JOIN user_features uf ON u.id = uf.user_id
            )
            SELECT 
                up.personality,
                t.genre,
                COUNT(*) as favorites_count
            FROM user_personality up
            JOIN favorites f ON up.user_id = f.user_id
            JOIN tracks t ON f.track_id = t.id
            WHERE t.genre IS NOT NULL
            GROUP BY up.personality, t.genre
            ORDER BY up.personality, favorites_count DESC
        """)
        
        personality_genres = {}
        for row in cur.fetchall():
            personality = row['personality']
            if personality not in personality_genres:
                personality_genres[personality] = []
            if len(personality_genres[personality]) < 5:  # Топ-5 жанров
                personality_genres[personality].append({
                    'genre': row['genre'],
                    'count': row['favorites_count']
                })
        
        return jsonify({
            'success': True,
            'age_distribution': age_distribution,
            'gender_distribution': gender_distribution,
            'personality_distribution': personality_distribution,
            'openness_distribution': openness_distribution,
            'personality_genres': personality_genres
        })
        
    except Exception as e:
        logger.error(f"Ошибка сегментации пользователей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/api/stats/correlation', methods=['GET'])
@admin_required
def get_correlation_analysis():
    """Корреляционный анализ характеристик пользователей и предпочтений"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Корреляция между экстраверсией и энергичностью музыки
        cur.execute("""
            SELECT 
                uf.extraversion,
                AVG(CASE 
                    WHEN t.genre IN ('Rock', 'Metal', 'Electronic', 'Dance', 'Pop') THEN 5
                    WHEN t.genre IN ('Classical', 'Ambient', 'Jazz') THEN 1
                    ELSE 3
                END) as energy_score,
                COUNT(DISTINCT t.id) as tracks_count
            FROM user_features uf
            JOIN favorites f ON uf.user_id = f.user_id
            JOIN tracks t ON f.track_id = t.id
            WHERE uf.extraversion IS NOT NULL
            GROUP BY uf.extraversion
            ORDER BY uf.extraversion
        """)
        extraversion_energy = cur.fetchall()
        
        # Корреляция между открытостью и разнообразием жанров
        cur.execute("""
            SELECT 
                uf.openness,
                COUNT(DISTINCT t.genre) as unique_genres,
                COUNT(DISTINCT t.id) as total_tracks
            FROM user_features uf
            JOIN favorites f ON uf.user_id = f.user_id
            JOIN tracks t ON f.track_id = t.id
            WHERE uf.openness IS NOT NULL AND t.genre IS NOT NULL
            GROUP BY uf.openness, uf.user_id
        """)
        openness_diversity = cur.fetchall()
        
        return jsonify({
            'success': True,
            'extraversion_energy': extraversion_energy,
            'openness_diversity': openness_diversity
        })
        
    except Exception as e:
        logger.error(f"Ошибка корреляционного анализа: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def get_users_list():
    """Получить список пользователей"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        offset = (page - 1) * per_page
        
        query = """
            SELECT 
                u.id,
                u.username,
                u.email,
                u.created_at,
                u.is_admin,
                uf.gender,
                uf.age,
                uf.extraversion,
                uf.openness,
                COUNT(DISTINCT f.track_id) as favorites_count,
                COUNT(DISTINCT lh.id) as listens_count
            FROM users u
            LEFT JOIN user_features uf ON u.id = uf.user_id
            LEFT JOIN favorites f ON u.id = f.user_id
            LEFT JOIN listening_history lh ON u.id = lh.user_id
        """
        
        params = []
        if search:
            query += " WHERE u.username ILIKE %s OR u.email ILIKE %s"
            params.extend([f'%{search}%', f'%{search}%'])
        
        query += """
            GROUP BY u.id, u.username, u.email, u.created_at, u.is_admin, 
                     uf.gender, uf.age, uf.extraversion, uf.openness
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])
        
        cur.execute(query, params)
        users = cur.fetchall()
        
        # Общее количество пользователей
        count_query = "SELECT COUNT(*) as total FROM users"
        if search:
            count_query += " WHERE username ILIKE %s OR email ILIKE %s"
            cur.execute(count_query, [f'%{search}%', f'%{search}%'])
        else:
            cur.execute(count_query)
        
        total = cur.fetchone()['total']
        
        return jsonify({
            'success': True,
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/api/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin_status(user_id):
    """Переключить статус администратора пользователя"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE users 
            SET is_admin = NOT is_admin 
            WHERE id = %s
            RETURNING is_admin
        """, (user_id,))
        
        result = cur.fetchone()
        if result:
            conn.commit()
            return jsonify({
                'success': True,
                'is_admin': result[0],
                'message': 'Статус администратора обновлен'
            })
        else:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка изменения статуса администратора: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()