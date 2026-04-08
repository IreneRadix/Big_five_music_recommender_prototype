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
        except Exception as e:
            logger.error(f"Ошибка получения username: {e}")
            return None
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
            cur.execute(query, (track_ids,))
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
    
    def get_user_favorites_count(self, username):
        """Получает количество избранных треков пользователя"""
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            return 0
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT COUNT(*) FROM favorites WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return 0
        finally:
            cur.close()
            conn.close()
    
    def get_user_favorite_track_ids(self, username):
        """Получает ID избранных треков пользователя"""
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            return set()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT track_id FROM favorites WHERE user_id = %s", (user_id,))
            results = cur.fetchall()
            return {row[0] for row in results}
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return set()
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
        
        # Проверяем, есть ли у пользователя избранные треки
        user_favorites_count = self.get_user_favorites_count(username)
        
        # Находим похожих пользователей
        similar_users = self.find_similar_users(username, top_n=30)
        
        if not similar_users:
            # Если нет похожих, показываем глобально популярные
            recommendations = self.get_global_popular_tracks(top_n)
            for rec in recommendations:
                rec['recommendation_reason'] = 'Нет данных о похожих пользователях'
            return recommendations
        
        # Получаем популярные треки среди похожих пользователей
        popular_tracks = self.get_popular_tracks_among_users(similar_users, favorites_df, top_n * 2)
        
        if not popular_tracks:
            return self.get_global_popular_tracks(top_n)
        
        # Получаем детали треков
        recommendations = self.get_tracks_details(list(popular_tracks))
        
        # Если у пользователя уже есть избранное, исключаем его треки
        if user_favorites_count > 0:
            user_track_ids = self.get_user_favorite_track_ids(username)
            recommendations = [t for t in recommendations if t['id'] not in user_track_ids]
        
        # Добавляем пояснение к рекомендациям
        for rec in recommendations:
            if user_favorites_count == 0:
                rec['recommendation_reason'] = f'Нравится {len(similar_users)} людям с похожим характером'
            else:
                rec['recommendation_reason'] = f'Советуют {len(similar_users)} пользователей с похожим характером'
        
        # Ограничиваем количество
        recommendations = recommendations[:top_n]
        
        # Если рекомендаций меньше top_n, дополняем глобально популярными
        if len(recommendations) < top_n:
            existing_ids = [t['id'] for t in recommendations]
            additional = self.get_global_popular_tracks(top_n - len(recommendations))
            for track in additional:
                if track['id'] not in existing_ids:
                    track['recommendation_reason'] = 'Популярный трек'
                    recommendations.append(track)
        
        return recommendations