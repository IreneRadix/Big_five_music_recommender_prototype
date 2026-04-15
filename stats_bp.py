# stats_bp.py
from flask import Blueprint, request, jsonify, render_template
from database import get_db_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)

stats_bp = Blueprint('stats', __name__)


class UserStatsService:
    """Сервис для работы со статистикой пользователя"""
    
    def __init__(self):
        pass
    
    def get_user_id_by_username(self, username):
        """Получает user_id по username"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            result = cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения user_id: {e}")
            return None
        finally:
            cur.close()
            conn.close()
    
    def get_favorite_tracks(self, user_id):
        """Получает избранные треки пользователя"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT t.*, f.added_at
                FROM tracks t
                JOIN favorites f ON t.id = f.track_id
                WHERE f.user_id = %s
                ORDER BY f.added_at DESC
            """, (user_id,))
            return cur.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения избранных треков: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    def get_listening_history(self, user_id, days=None):
        """Получает историю прослушиваний пользователя"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            if days:
                cur.execute("""
                    SELECT h.*, t.title, t.artist, t.genre, t.cover_url, t.file_url
                    FROM listening_history h
                    JOIN tracks t ON h.track_id = t.id
                    WHERE h.user_id = %s AND h.played_at >= NOW() - INTERVAL '%s days'
                    ORDER BY h.played_at DESC
                """, (user_id, days))
            else:
                cur.execute("""
                    SELECT h.*, t.title, t.artist, t.genre, t.cover_url, t.file_url
                    FROM listening_history h
                    JOIN tracks t ON h.track_id = t.id
                    WHERE h.user_id = %s
                    ORDER BY h.played_at DESC
                """, (user_id,))
            
            return cur.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения истории прослушиваний (возможно таблица не создана): {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    def get_mood_from_track(self, track):
        """Определяет настроение трека по его характеристикам"""
        title = (track.get('title') or '').lower()
        artist = (track.get('artist') or '').lower()
        genre = (track.get('genre') or '').lower()
        
        energetic_keywords = ['rock', 'metal', 'punk', 'dance', 'electronic', 'techno', 
                            'энергич', 'электро', 'драйв', 'fast', 'heavy']
        calm_keywords = ['ambient', 'chill', 'acoustic', 'instrumental', 'meditation',
                        'спокойн', 'расслаб', 'медитац', 'slow', 'soft']
        sad_keywords = ['blues', 'sad', 'melancholy', 'грустн', 'меланхол', 'тоск', 
                       'печаль', 'депресс', 'slow', 'minor']
        happy_keywords = ['pop', 'funk', 'disco', 'happy', 'радост', 'весел', 'позитив',
                         'upbeat', 'dance', 'party']
        romantic_keywords = ['love', 'romantic', 'soul', 'ballad', 'романтич', 'любов',
                            'нежн', 'чувств', 'slow', 'passion']
        
        text = f"{title} {artist} {genre}"
        
        if any(kw in text for kw in energetic_keywords):
            return 'energetic'
        elif any(kw in text for kw in calm_keywords):
            return 'calm'
        elif any(kw in text for kw in sad_keywords):
            return 'sad'
        elif any(kw in text for kw in happy_keywords):
            return 'happy'
        elif any(kw in text for kw in romantic_keywords):
            return 'romantic'
        else:
            moods = ['energetic', 'calm', 'happy', 'sad', 'romantic', 'other']
            return random.choice(moods)
    
    def calculate_mood_stats(self, tracks):
        """Подсчитывает статистику по настроениям"""
        mood_stats = {
            'energetic': 0, 'calm': 0, 'happy': 0,
            'sad': 0, 'romantic': 0, 'other': 0
        }
        
        artists_count = {}
        genres_count = {}
        
        for track in tracks:
            mood = self.get_mood_from_track(track)
            mood_stats[mood] = mood_stats.get(mood, 0) + 1
            
            artist = track.get('artist', 'Неизвестный исполнитель')
            artists_count[artist] = artists_count.get(artist, 0) + 1
            
            genre = track.get('genre', 'Без жанра')
            if genre:
                genres_count[genre] = genres_count.get(genre, 0) + 1
        
        # Сортировка топов
        top_artists = sorted(
            [{'artist': k, 'count': v} for k, v in artists_count.items()],
            key=lambda x: x['count'], reverse=True
        )[:15]
        
        top_genres = sorted(
            [{'genre': k, 'count': v} for k, v in genres_count.items()],
            key=lambda x: x['count'], reverse=True
        )[:15]
        
        return mood_stats, top_artists, top_genres
    
    def generate_daily_activity(self, history, days=30):
        """Генерирует активность по дням"""
        now = datetime.now()
        activity = {}
        
        # Инициализация всех дней
        for i in range(days, -1, -1):
            date = (now - timedelta(days=i)).strftime('%d.%m')
            activity[date] = 0
        
        # Заполнение из истории
        for item in history:
            if item.get('played_at'):
                played_date = item['played_at'].strftime('%d.%m')
                if played_date in activity:
                    activity[played_date] += 1
        
        # Преобразование в список
        result = []
        for i in range(days, -1, -1):
            date = (now - timedelta(days=i)).strftime('%d.%m')
            result.append({
                'date': date,
                'count': activity.get(date, 0)
            })
        
        return result
    
    def get_full_stats(self, username):
        """Получает полную статистику пользователя"""
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            raise ValueError('Пользователь не найден')
        
        # Получаем избранные треки
        favorite_tracks = self.get_favorite_tracks(user_id)
        favorites_count = len(favorite_tracks)
        
        # Получаем историю прослушиваний
        all_history = self.get_listening_history(user_id)
        
        # Если истории нет, генерируем примерные данные на основе избранного
        if not all_history:
            total_plays = favorites_count * 3 + random.randint(10, 50)
            all_history = self._generate_mock_history(user_id, favorite_tracks, total_plays)
        
        total_plays = len(all_history)
        total_listening_time = sum(h.get('duration_seconds', 180) for h in all_history)
        
        # Статистика по настроениям для прослушиваний
        plays_mood_stats, plays_top_artists, plays_top_genres = self.calculate_mood_stats(all_history)
        
        # Статистика по настроениям для избранного
        favorites_mood_stats, fav_top_artists, fav_top_genres = self.calculate_mood_stats(favorite_tracks)
        
        # Уникальные исполнители
        unique_artists = len(set(
            h.get('artist', '') for h in all_history if h.get('artist')
        ))
        
        # Генерация активности по дням
        daily_activity = self.generate_daily_activity(all_history, 30)
        
        # Формирование статистики по периодам
        def get_period_stats(days):
            period_history = [h for h in all_history 
                            if h.get('played_at') and 
                            (datetime.now() - h['played_at']).days <= days]
            
            if not period_history:
                # Если нет данных за период, возвращаем пропорциональную часть
                multiplier = days / 365
                return {
                    'total_plays': int(total_plays * multiplier),
                    'favorites_count': favorites_count,
                    'total_listening_time': int(total_listening_time * multiplier),
                    'unique_artists': max(1, int(unique_artists * multiplier)),
                    'plays_by_mood': {k: int(v * multiplier) for k, v in plays_mood_stats.items()},
                    'favorites_by_mood': favorites_mood_stats,
                    'top_artists': plays_top_artists[:10],
                    'top_genres': plays_top_genres[:10],
                    'daily_activity': self.generate_daily_activity(period_history, min(days, 30))
                }
            
            period_plays = len(period_history)
            period_mood_stats, period_top_artists, period_top_genres = self.calculate_mood_stats(period_history)
            period_daily = self.generate_daily_activity(period_history, min(days, 30))
            
            return {
                'total_plays': period_plays,
                'favorites_count': favorites_count,
                'total_listening_time': sum(h.get('duration_seconds', 180) for h in period_history),
                'unique_artists': len(set(h.get('artist', '') for h in period_history if h.get('artist'))),
                'plays_by_mood': period_mood_stats,
                'favorites_by_mood': favorites_mood_stats,
                'top_artists': period_top_artists[:10],
                'top_genres': period_top_genres[:10],
                'daily_activity': period_daily
            }
        
        return {
            'week': get_period_stats(7),
            'month': get_period_stats(30),
            'year': get_period_stats(365),
            'all_time': {
                'total_plays': total_plays,
                'favorites_count': favorites_count,
                'total_listening_time': total_listening_time,
                'unique_artists': unique_artists,
                'plays_by_mood': plays_mood_stats,
                'favorites_by_mood': favorites_mood_stats,
                'top_artists': plays_top_artists,
                'top_genres': plays_top_genres,
                'daily_activity': daily_activity
            }
        }
    
    def _generate_mock_history(self, user_id, favorite_tracks, total_plays):
        """Генерирует тестовую историю прослушиваний"""
        mock_history = []
        now = datetime.now()
        
        for i in range(total_plays):
            if not favorite_tracks:
                break
            
            track = random.choice(favorite_tracks)
            days_ago = random.randint(0, 60)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            played_at = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            mock_history.append({
                'track_id': track['id'],
                'title': track.get('title', ''),
                'artist': track.get('artist', ''),
                'genre': track.get('genre', ''),
                'cover_url': track.get('cover_url', ''),
                'file_url': track.get('file_url', ''),
                'played_at': played_at,
                'duration_seconds': random.randint(120, 240),
                'completed': random.choice([True, True, True, False])
            })
        
        return sorted(mock_history, key=lambda x: x['played_at'], reverse=True)


# Создаем экземпляр сервиса
stats_service = UserStatsService()


@stats_bp.route("/stats/<username>")
def stats_page(username):
    """Страница со статистикой пользователя"""
    return render_template("stats.html", username=username)


@stats_bp.route("/api/user_stats_full/<username>", methods=['GET'])
def get_user_stats_full(username):
    """Получить полную статистику пользователя за разные периоды"""
    try:
        stats = stats_service.get_full_stats(username)
        
        return jsonify({
            'success': True,
            'username': username,
            'stats': stats
        })
        
    except ValueError as e:
        logger.warning(f"Пользователь не найден: {username}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@stats_bp.route("/api/user_stats/<username>", methods=['GET'])
def get_user_stats(username):
    """Получить базовую статистику пользователя"""
    try:
        user_id = stats_service.get_user_id_by_username(username)
        if not user_id:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        favorite_tracks = stats_service.get_favorite_tracks(user_id)
        all_history = stats_service.get_listening_history(user_id)
        
        return jsonify({
            'success': True,
            'username': username,
            'favorites_count': len(favorite_tracks),
            'total_plays': len(all_history),
            'total_listening_time': sum(h.get('duration_seconds', 180) for h in all_history)
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@stats_bp.route("/api/listening_history/<username>", methods=['GET'])
def get_listening_history(username):
    """Получить историю прослушиваний пользователя"""
    try:
        user_id = stats_service.get_user_id_by_username(username)
        if not user_id:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        days = request.args.get('days', type=int)
        limit = request.args.get('limit', 50, type=int)
        
        history = stats_service.get_listening_history(user_id, days)
        
        return jsonify({
            'success': True,
            'username': username,
            'history': history[:limit],
            'total': len(history)
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500