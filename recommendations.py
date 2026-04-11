# recommendations.py
import pandas as pd
import numpy as np
from database import get_db_connection
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class MusicRecommender:
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
    
    def get_username_by_user_id(self, user_id):
        """Получает username по user_id"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else None
        finally:
            cur.close()
            conn.close()
    
    def get_user_favorites_count(self, username):
        """Получает количество избранных треков пользователя"""
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            logger.warning(f"Пользователь {username} не найден")
            return 0
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT COUNT(*) FROM favorites WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            count = result[0] if result else 0
            logger.info(f"Пользователь {username} (id={user_id}) имеет {count} треков в избранном")
            return count
        except Exception as e:
            logger.error(f"Ошибка получения количества избранного: {e}")
            return 0
        finally:
            cur.close()
            conn.close()
    
    def get_user_favorite_track_ids(self, username):
        """Получает ID избранных треков пользователя"""
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            logger.warning(f"Пользователь {username} не найден при получении треков")
            return set()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT track_id FROM favorites WHERE user_id = %s", (user_id,))
            results = cur.fetchall()
            track_ids = {row[0] for row in results}
            logger.info(f"Найдено {len(track_ids)} избранных треков для {username}")
            return track_ids
        except Exception as e:
            logger.error(f"Ошибка получения избранных треков: {e}")
            return set()
        finally:
            cur.close()
            conn.close()
    
    def load_users_data(self):
        """Загружает данные пользователей (только экстраверсия и открытость)"""
        conn = get_db_connection()
        
        try:
            query = """
                SELECT 
                    u.id as user_id,
                    u.username,
                    uf.extraversion,
                    uf.openness
                FROM users u
                JOIN user_features uf ON u.id = uf.user_id
                WHERE uf.extraversion IS NOT NULL AND uf.openness IS NOT NULL
            """
            df = pd.read_sql(query, conn)
            
            if df.empty:
                return df
            
            # Нормализуем признаки для корректного сравнения
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            df[['extraversion', 'openness']] = scaler.fit_transform(df[['extraversion', 'openness']])
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def load_favorites_data(self):
        """Загружает данные об избранных треках"""
        conn = get_db_connection()
        
        try:
            query = """
                SELECT 
                    f.user_id,
                    u.username,
                    f.track_id,
                    t.title,
                    t.artist,
                    t.genre,
                    t.cover_url,
                    t.file_url
                FROM favorites f
                JOIN users u ON f.user_id = u.id
                JOIN tracks t ON f.track_id = t.id
            """
            df = pd.read_sql(query, conn)
            return df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки избранного: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def find_similar_users(self, target_username, top_n=20):
        """
        Находит похожих пользователей по экстраверсии и открытости
        """
        # Получаем user_id по username
        target_user_id = self.get_user_id_by_username(target_username)
        if not target_user_id:
            return []
        
        df = self.load_users_data()
        
        if df.empty:
            return []
        
        if target_user_id not in df['user_id'].values:
            return []
        
        # Получаем данные целевого пользователя
        target = df[df['user_id'] == target_user_id].iloc[0]
        
        # Вычисляем евклидово расстояние для всех остальных
        results = []
        for _, user in df.iterrows():
            if user['user_id'] == target_user_id:
                continue
            
            # Евклидово расстояние между точками (extraversion, openness)
            distance = np.sqrt(
                (target['extraversion'] - user['extraversion'])**2 + 
                (target['openness'] - user['openness'])**2
            )
            
            # Чем меньше расстояние, тем больше похожесть
            similarity = 1 / (1 + distance)
            
            results.append({
                'user_id': user['user_id'],
                'username': user['username'],
                'similarity': similarity,
                'distance': distance
            })
        
        # Сортируем по похожести
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Возвращаем топ-N пользователей (с username)
        return results[:top_n]
    
    def get_popular_tracks_among_users(self, similar_users_list, favorites_df, top_n=20):
        """
        Получает самые популярные треки среди списка похожих пользователей
        similar_users_list - список словарей с ключом 'user_id'
        """
        if not similar_users_list:
            return set()
        
        user_ids = [u['user_id'] for u in similar_users_list]
        
        # Фильтруем треки только для указанных пользователей
        filtered_tracks = favorites_df[favorites_df['user_id'].isin(user_ids)]
        
        if filtered_tracks.empty:
            return set()
        
        # Подсчитываем сколько пользователей лайкнуло каждый трек
        track_popularity = filtered_tracks.groupby('track_id')['user_id'].nunique()
        track_popularity = track_popularity.sort_values(ascending=False)
        
        # Берем топ-N
        top_tracks = track_popularity.head(top_n)
        
        return set(top_tracks.index.tolist())
    
    def get_tracks_details(self, track_ids):
        """Получает детальную информацию о треках"""
        if not track_ids:
            return []
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            query = """
                SELECT 
                    id,
                    title,
                    artist,
                    genre,
                    cover_url,
                    file_url
                FROM tracks
                WHERE id = ANY(%s)
            """
            cur.execute(query, (list(track_ids),))
            tracks = cur.fetchall()
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей треков: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    def get_global_popular_tracks(self, top_n=20):
        """Получает глобально популярные треки (запасной вариант)"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            query = """
                SELECT 
                    t.id,
                    t.title,
                    t.artist,
                    t.genre,
                    t.cover_url,
                    t.file_url,
                    COUNT(f.user_id) as likes_count
                FROM tracks t
                LEFT JOIN favorites f ON t.id = f.track_id
                GROUP BY t.id
                ORDER BY likes_count DESC, RANDOM()
                LIMIT %s
            """
            cur.execute(query, (top_n,))
            tracks = cur.fetchall()
            
            for track in tracks:
                track['recommendation_reason'] = 'Популярный трек'
            
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    def get_recommendations(self, username, top_n=20):
        """
        Главная функция получения рекомендаций по username
        """
        # Проверяем, существует ли пользователь
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            return []
        
        # Загружаем избранное
        favorites_df = self.load_favorites_data()
        
        if favorites_df.empty:
            return self.get_global_popular_tracks(top_n)
        
        # Получаем ID треков пользователя в избранном
        user_track_ids = self.get_user_favorite_track_ids(username)
        
        # Проверяем, есть ли у пользователя избранные треки
        user_favorites_count = len(user_track_ids)
        
        # Находим похожих пользователей
        similar_users = self.find_similar_users(username, top_n=30)
        
        if not similar_users:
            # Если нет похожих, показываем глобально популярные (исключая избранное)
            recommendations = self.get_global_popular_tracks(top_n * 2)  # Берем с запасом
            
            # Фильтруем треки, которые уже в избранном
            recommendations = [t for t in recommendations if t['id'] not in user_track_ids]
            
            for rec in recommendations[:top_n]:
                rec['recommendation_reason'] = 'Нет данных о похожих пользователях'
            return recommendations[:top_n]
        
        # Получаем популярные треки среди похожих пользователей (с запасом)
        popular_tracks = self.get_popular_tracks_among_users(similar_users, favorites_df, top_n * 3)
        
        if not popular_tracks:
            recommendations = self.get_global_popular_tracks(top_n * 2)
            recommendations = [t for t in recommendations if t['id'] not in user_track_ids]
            return recommendations[:top_n]
        
        # Получаем детали треков
        all_recommendations = self.get_tracks_details(list(popular_tracks))
        
        # Фильтруем треки, которые уже в избранном у пользователя
        recommendations = [t for t in all_recommendations if t['id'] not in user_track_ids]
        
        # Добавляем пояснение к рекомендациям
        for rec in recommendations:
            if user_favorites_count == 0:
                rec['recommendation_reason'] = f'Нравится {len(similar_users)} людям с похожим характером'
            else:
                rec['recommendation_reason'] = f'Советуют {len(similar_users)} пользователей с похожим характером'
        
        # Ограничиваем количество
        recommendations = recommendations[:top_n]
        
        # Если рекомендаций меньше top_n, дополняем глобально популярными (исключая избранное)
        if len(recommendations) < top_n:
            existing_ids = [t['id'] for t in recommendations]
            additional_needed = top_n - len(recommendations)
            
            # Получаем глобально популярные треки, исключая избранное и уже добавленные
            additional = self.get_global_popular_tracks(additional_needed * 2)
            
            for track in additional:
                if track['id'] not in existing_ids and track['id'] not in user_track_ids:
                    track['recommendation_reason'] = 'Популярный трек'
                    recommendations.append(track)
                    if len(recommendations) >= top_n:
                        break
        
        return recommendations

    def get_mood_based_recommendations(self, username, mood, top_n=10):
        """
        Получить рекомендации на основе настроения для возрастной категории 35-50 лет
        mood: 'energetic', 'calm', 'sad', 'happy', 'romantic'
        """
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            return []
        
        # Маппинг настроений на конкретные песни и исполнителей для возраста 35-50
        mood_songs = {
            'energetic': {
                'songs': [
                    'Nirvana', 'Smells Like Teen Spirit', 'Metallica', 'Enter Sandman',
                    'AC/DC', 'Back in Black', 'Queen', 'We Will Rock You',
                    'Guns N Roses', 'Welcome to the Jungle', 'The Prodigy', 'Smack My Bitch Up'
                ],
                'description': 'Энергичные хиты 80-90х'
            },
            'calm': {
                'songs': [
                    'Enya', 'Only Time', 'Sting', 'Fields of Gold', 'Eric Clapton', 'Tears in Heaven',
                    'Norah Jones', 'Come Away With Me', 'Simon & Garfunkel', 'The Sound of Silence',
                    'George Michael', 'Careless Whisper', 'Radiohead', 'Creep'
                ],
                'description': 'Спокойная классика для релаксации'
            },
            'sad': {
                'songs': [
                    'Gary Moore', 'Still Got the Blues', 'Eric Clapton', 'Tears in Heaven',
                    'Nirvana', 'Something in the Way', 'Adele', 'Someone Like You',
                    'Sinead O\'Connor', 'Nothing Compares 2 U', 'The Cranberries', 'Zombie',
                    'Radiohead', 'No Surprises', 'Coldplay', 'The Scientist'
                ],
                'description': 'Душевные баллады и блюз'
            },
            'happy': {
                'songs': [
                    'ABBA', 'Dancing Queen', 'The Beatles', 'Here Comes the Sun',
                    'Michael Jackson', 'Billie Jean', 'Pharrell Williams', 'Happy',
                    'Queen', 'Don\'t Stop Me Now', 'Bruno Mars', 'Uptown Funk',
                    'Earth Wind & Fire', 'September', 'Mark Ronson', 'Uptown Funk'
                ],
                'description': 'Позитивные хиты для хорошего настроения'
            },
            'romantic': {
                'songs': [
                    'Whitney Houston', 'I Will Always Love You', 'Elvis Presley', 'Can\'t Help Falling in Love',
                    'Bryan Adams', 'Everything I Do', 'Celine Dion', 'My Heart Will Go On',
                    'The Beatles', 'Something', 'Lionel Richie', 'Hello',
                    'Berlin', 'Take My Breath Away', 'Aerosmith', 'I Don\'t Want to Miss a Thing'
                ],
                'description': 'Романтические баллады'
            }
        }
        
        if mood not in mood_songs:
            mood = 'happy'
        
        mood_config = mood_songs[mood]
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Получаем избранные треки пользователя
            user_track_ids = self.get_user_favorite_track_ids(username)
            
            # Формируем условие для поиска песен
            search_conditions = []
            search_params = []
            
            for item in mood_config['songs']:
                search_conditions.append("(t.title ILIKE %s OR t.artist ILIKE %s)")
                search_params.append(f'%{item}%')
                search_params.append(f'%{item}%')
            
            # Исправленный запрос - убираем ORDER BY RANDOM() и используем просто ORDER BY likes_count
            # и добавляем LIMIT с запасом, потом перемешаем в Python
            query = f"""
                SELECT DISTINCT 
                    t.id,
                    t.title,
                    t.artist,
                    t.genre,
                    t.cover_url,
                    t.file_url,
                    COALESCE(COUNT(f.user_id), 0) as likes_count
                FROM tracks t
                LEFT JOIN favorites f ON t.id = f.track_id
                WHERE ({' OR '.join(search_conditions)})
                AND t.id != ALL(%s)
                GROUP BY t.id, t.title, t.artist, t.genre, t.cover_url, t.file_url
                ORDER BY likes_count DESC
                LIMIT %s
            """
            
            cur.execute(query, search_params + [list(user_track_ids) if user_track_ids else [-1], top_n * 2])
            
            tracks = cur.fetchall()
            
            # Перемешиваем результаты для разнообразия
            import random
            random.shuffle(tracks)
            
            # Добавляем пояснение к рекомендациям
            for track in tracks[:top_n]:
                track['recommendation_reason'] = mood_config['description']
            
            return tracks[:top_n]
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций по настроению: {e}")
            return []
        finally:
            cur.close()
            conn.close()


    def get_diverse_recommendations(self, username, top_n=20):
        """
        Получить разнообразные рекомендации (хиты 80-90-х для возрастной категории 35-50)
        """
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            return []
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Получаем избранные треки пользователя
            user_track_ids = self.get_user_favorite_track_ids(username)
            
            # Список популярных исполнителей и песен для возраста 35-50
            popular_songs = [
                'Queen', 'Freddie Mercury', 'Bohemian Rhapsody', 'The Beatles', 'Let It Be',
                'Michael Jackson', 'Thriller', 'Madonna', 'Like a Prayer', 'Prince', 'Purple Rain',
                'U2', 'With or Without You', 'Bon Jovi', 'Livin\' on a Prayer', 'Guns N Roses',
                'Sweet Child O Mine', 'Nirvana', 'Come as You Are', 'Metallica', 'Nothing Else Matters',
                'Red Hot Chili Peppers', 'Californication', 'Radiohead', 'Karma Police',
                'Oasis', 'Wonderwall', 'Blur', 'Song 2', 'Spice Girls', 'Wannabe',
                'Backstreet Boys', 'I Want It That Way', 'Britney Spears', 'Baby One More Time'
            ]
            
            # Формируем условия поиска
            search_conditions = []
            search_params = []
            
            for song in popular_songs:
                search_conditions.append("(t.title ILIKE %s OR t.artist ILIKE %s)")
                search_params.append(f'%{song}%')
                search_params.append(f'%{song}%')
            
            # Исправленный запрос
            query = f"""
                SELECT DISTINCT 
                    t.id,
                    t.title,
                    t.artist,
                    t.genre,
                    t.cover_url,
                    t.file_url,
                    COALESCE(COUNT(f.user_id), 0) as likes_count
                FROM tracks t
                LEFT JOIN favorites f ON t.id = f.track_id
                WHERE ({' OR '.join(search_conditions)})
                AND t.id != ALL(%s)
                GROUP BY t.id, t.title, t.artist, t.genre, t.cover_url, t.file_url
                ORDER BY likes_count DESC
                LIMIT %s
            """
            
            cur.execute(query, search_params + [list(user_track_ids) if user_track_ids else [-1], top_n])
            
            tracks = cur.fetchall()
            
            for track in tracks:
                track['recommendation_reason'] = 'Хиты 80-90-х, проверенные временем'
            
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка получения разнообразных рекомендаций: {e}")
            return self.get_global_popular_tracks(top_n)
        finally:
            cur.close()
            conn.close()