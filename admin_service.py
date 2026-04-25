from database import get_db_connection
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

def get_overview_stats():
    """Общая статистика"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        stats = {}
        cur.execute("SELECT COUNT(*) as total FROM users")
        stats['total_users'] = cur.fetchone()['total']

        cur.execute("""
            SELECT COUNT(DISTINCT user_id) as active 
            FROM listening_history 
            WHERE played_at > NOW() - INTERVAL '7 days'
        """)
        stats['active_users'] = cur.fetchone()['active'] or 0

        cur.execute("SELECT COUNT(*) as total FROM tracks")
        stats['total_tracks'] = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) as total FROM listening_history")
        stats['total_listens'] = cur.fetchone()['total']

        cur.execute("""
            SELECT COALESCE(AVG(fav_count), 0) as avg_favorites 
            FROM (SELECT user_id, COUNT(*) as fav_count FROM favorites GROUP BY user_id) t
        """)
        stats['avg_favorites_per_user'] = round(cur.fetchone()['avg_favorites'], 2)

        return {'success': True, 'stats': stats}
    except Exception as e:
        logger.error(f"get_overview_stats error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_popular_tracks(limit, filter_type):
    """
    filter_type: 'overall', 'by_age', 'by_gender'
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if filter_type == 'overall':
            cur.execute("""
                SELECT 
                    t.id, t.title, t.artist, t.genre, t.cover_url,
                    COUNT(DISTINCT f.user_id) as favorites_count,
                    COUNT(lh.id) as listens_count
                FROM tracks t
                LEFT JOIN favorites f ON t.id = f.track_id
                LEFT JOIN listening_history lh ON t.id = lh.track_id
                GROUP BY t.id
                ORDER BY favorites_count DESC, listens_count DESC
                LIMIT %s
            """, (limit,))
            tracks = cur.fetchall()
            
            return {'success': True, 'tracks': tracks, 'filter': filter_type}

        elif filter_type == 'by_age':
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
                )
                SELECT 
                    t.id, t.title, t.artist, t.genre, t.cover_url,
                    ua.age_group,
                    COUNT(DISTINCT f.user_id) as favorites_count
                FROM tracks t
                JOIN favorites f ON t.id = f.track_id
                JOIN user_ages ua ON f.user_id = ua.user_id
                GROUP BY t.id, t.title, t.artist, t.genre, t.cover_url, ua.age_group
                ORDER BY favorites_count DESC
                LIMIT %s
            """, (limit,))
            tracks = cur.fetchall()
            return {'success': True, 'tracks': tracks, 'filter': filter_type}

        elif filter_type == 'by_gender':
            cur.execute("""
                SELECT 
                    t.id, t.title, t.artist, t.genre, t.cover_url,
                    uf.gender,
                    COUNT(DISTINCT f.user_id) as favorites_count
                FROM tracks t
                JOIN favorites f ON t.id = f.track_id
                JOIN user_features uf ON f.user_id = uf.user_id
                WHERE uf.gender IS NOT NULL
                GROUP BY t.id, t.title, t.artist, t.genre, t.cover_url, uf.gender
                ORDER BY favorites_count DESC
                LIMIT %s
            """, (limit,))
            tracks = cur.fetchall()
            return {'success': True, 'tracks': tracks, 'filter': filter_type}
        else:
            return {'success': False, 'error': 'Invalid filter'}
    except Exception as e:
        logger.error(f"get_popular_tracks error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_genre_analysis():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        
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

        cur.execute("""
            SELECT 
                t.genre,
                uf.gender,
                COUNT(DISTINCT f.user_id) as listeners_count,
                COUNT(*) as favorites_count
            FROM tracks t
            JOIN favorites f ON t.id = f.track_id
            JOIN user_features uf ON f.user_id = uf.user_id
            WHERE t.genre IS NOT NULL AND t.genre != '' AND uf.gender IS NOT NULL
            GROUP BY t.genre, uf.gender
            ORDER BY t.genre, favorites_count DESC
        """)
        genre_by_gender = cur.fetchall()

        cur.execute("""
            SELECT 
                t.genre,
                COUNT(DISTINCT f.user_id) as unique_listeners,
                COUNT(*) as total_favorites
            FROM tracks t
            JOIN favorites f ON t.id = f.track_id
            WHERE t.genre IS NOT NULL AND t.genre != ''
            GROUP BY t.genre
            ORDER BY total_favorites DESC
        """)
        overall_genre = cur.fetchall()

        return {
            'success': True,
            'genre_by_age': genre_by_age,
            'genre_by_gender': genre_by_gender,
            'overall_genre': overall_genre
        }
    except Exception as e:
        logger.error(f"get_genre_analysis error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_user_segments():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        
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

        cur.execute("""
            SELECT gender, COUNT(*) as count
            FROM user_features
            WHERE gender IS NOT NULL
            GROUP BY gender
        """)
        gender_distribution = cur.fetchall()

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

        cur.execute("""
            WITH user_personality AS (
                SELECT 
                    u.id as user_id,
                    CASE 
                        WHEN uf.extraversion >= 4 THEN 'Экстраверты'
                        WHEN uf.extraversion <= 2 THEN 'Интроверты'
                        ELSE 'Амбиверты'
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
        rows = cur.fetchall()
        personality_genres = {}
        for row in rows:
            p = row['personality']
            if p not in personality_genres:
                personality_genres[p] = []
            if len(personality_genres[p]) < 5:
                personality_genres[p].append({
                    'genre': row['genre'],
                    'count': row['favorites_count']
                })

        return {
            'success': True,
            'age_distribution': age_distribution,
            'gender_distribution': gender_distribution,
            'personality_distribution': personality_distribution,
            'openness_distribution': openness_distribution,
            'personality_genres': personality_genres
        }
    except Exception as e:
        logger.error(f"get_user_segments error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_users_list(page, per_page, search):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        offset = (page - 1) * per_page
        query = """
            SELECT 
                u.id, u.username, u.email, u.created_at, u.is_admin,
                uf.gender, uf.age, uf.extraversion, uf.openness,
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

        count_query = "SELECT COUNT(*) as total FROM users"
        if search:
            count_query += " WHERE username ILIKE %s OR email ILIKE %s"
            cur.execute(count_query, [f'%{search}%', f'%{search}%'])
        else:
            cur.execute(count_query)
        total = cur.fetchone()['total']

        return {
            'success': True,
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    except Exception as e:
        logger.error(f"get_users_list error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def toggle_admin_status(user_id):
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
            return {'success': True, 'is_admin': result[0], 'message': 'Статус администратора обновлен'}
        else:
            return {'success': False, 'error': 'Пользователь не найден'}, 404
    except Exception as e:
        conn.rollback()
        logger.error(f"toggle_admin_status error: {e}")
        raise
    finally:
        cur.close()
        conn.close()