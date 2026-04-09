import pandas as pd
import numpy as np
from database import get_db_connection
from psycopg2.extras import RealDictCursor
import logging
import os
from typing import List, Dict, Any, Optional, Union
import random
from personality_funksvd import PersonalityFunkSVD

from base_recommender import BaseRecommender

logger = logging.getLogger(__name__)

class MusicRecommender:
    """
    Главный класс для получения музыкальных рекомендаций.
    
    Поддерживает два типа моделей:
    - 'funksvd' - PersonalityFunkSVD (только extraversion и openness)
    - 'fm' - Factorization Machine на LightFM (все доступные признаки)
    
    Parameters
    ----------
    model_type : str
        Тип модели: 'funksvd' или 'fm'
    model_path : str
        Путь для сохранения/загрузки модели
    force_retrain : bool
        Принудительно переобучить модель (игнорировать сохраненную)
    """
    
    def __init__(self, model_type: str = 'funksvd', model_path: str = 'model.pkl', force_retrain: bool = False):
        self.model_type = model_type
        self.model_path = model_path
        self.force_retrain = force_retrain
        self.model: Optional[BaseRecommender] = None
        
        if self.model_type not in ['funksvd', 'fm']:
            raise ValueError(f"Unknown model_type: {self.model_type}. Must be 'funksvd' or 'fm'")
    
    def get_user_id_by_username(self, username: str) -> Optional[int]:
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
    
    def get_username_by_user_id(self, user_id: int) -> Optional[str]:
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
    
    def get_user_favorites_count(self, username: str) -> int:
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
    
    def get_user_favorite_track_ids(self, username: str) -> set:
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
    
    def get_tracks_details(self, track_ids: List[int]) -> List[Dict[str, Any]]:
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
    
    def get_global_popular_tracks(self, top_n: int = 20, exclude_track_ids: set = None) -> List[Dict[str, Any]]:
        """Получает глобально популярные треки (запасной вариант)"""
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            
            exclude_condition = ""
            params = []
            
            if exclude_track_ids:
                exclude_condition = "AND t.id != ALL(%s)"
                params.append(list(exclude_track_ids))
            
            query = f"""
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
                WHERE 1=1 {exclude_condition}
                GROUP BY t.id
                ORDER BY likes_count DESC, RANDOM()
                LIMIT %s
            """
            params.append(top_n)
            cur.execute(query, params)
            tracks = cur.fetchall()
            
            for track in tracks:
                track['recommendation_reason'] = 'Популярный трек'
            
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка получения популярных треков: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    def _prepare_training_data(self) -> tuple:
        """
        Загружает данные для обучения модели.
        
        Returns
        -------
        tuple
            (interactions, user_features, item_features)
            interactions: DataFrame с колонками ['user_id', 'item_id', 'rating']
            user_features: DataFrame с индексом user_id и признаками пользователей
            item_features: DataFrame с индексом item_id и признаками треков
        """
        conn = get_db_connection()
        
        try:
            # 1. Взаимодействия: только лайки из favorites (история прослушиваний не используется)
            query_interactions = """
                SELECT user_id, track_id, 1 AS rating
                FROM favorites
            """
            interactions = pd.read_sql(query_interactions, conn)
            
            if interactions.empty:
                logger.warning("Нет взаимодействий для обучения модели")
                return None, None, None
            
            # 2. Признаки пользователей (все доступные)
            query_user_features = """
                SELECT 
                    u.id AS user_id,
                    uf.extraversion,
                    uf.conscientiousness,
                    uf.agreeableness,
                    uf.neuroticism,
                    uf.openness,
                    uf.age,
                    uf.gender
                FROM users u
                LEFT JOIN user_features uf ON u.id = uf.user_id
                WHERE uf.user_id IS NOT NULL  -- только те, у кого есть признаки
            """
            user_features_df = pd.read_sql(query_user_features, conn)
            
            if user_features_df.empty:
                logger.warning("Нет данных о признаках пользователей")
                return None, None, None
            
            user_features_df.set_index('user_id', inplace=True)
            
            # 3. Признаки треков
            # Вычисляем популярность трека (количество лайков)
            query_popularity = """
                SELECT track_id, COUNT(*) AS popularity
                FROM favorites
                GROUP BY track_id
            """
            pop_df = pd.read_sql(query_popularity, conn)
            pop_dict = dict(zip(pop_df['track_id'], pop_df['popularity']))
            
            query_tracks = """
                SELECT id, title, artist, genre, duration, cover_url, file_url
                FROM tracks
            """
            tracks_df = pd.read_sql(query_tracks, conn)
            tracks_df.set_index('id', inplace=True)
            
            # Добавляем популярность (если трек ни разу не лайкали - популярность 0)
            tracks_df['popularity'] = tracks_df.index.map(lambda x: pop_dict.get(x, 0))
            
            # Для FM используем artist, genre, duration, popularity
            # Для FunkSVD эти признаки не используются, но передаем для совместимости
            item_features_df = tracks_df[['artist', 'genre', 'duration', 'popularity']].copy()
            
            # Заполняем возможные пропуски
            item_features_df['artist'] = item_features_df['artist'].fillna('unknown')
            item_features_df['genre'] = item_features_df['genre'].fillna('')
            item_features_df['duration'] = item_features_df['duration'].fillna(0)
            
            logger.info(f"Подготовлены данные: {len(interactions)} взаимодействий, "
                       f"{len(user_features_df)} пользователей, {len(item_features_df)} треков")
            
            return interactions, user_features_df, item_features_df
            
        except Exception as e:
            logger.error(f"Ошибка подготовки данных: {e}")
            return None, None, None
        finally:
            conn.close()
    
    def _load_or_train_model(self) -> Optional[BaseRecommender]:
        """Загружает модель из файла или обучает, если файла нет или force_retrain=True"""
        if self.model is not None:
            return self.model
        
        # Проверяем, нужно ли загружать существующую модель
        if not self.force_retrain and os.path.exists(self.model_path):
            try:
                if self.model_type == 'funksvd':
                    self.model = PersonalityFunkSVD.load(self.model_path)
                elif self.model_type == 'fm':
                    self.model = FactorizationMachine.load(self.model_path)
                else:
                    raise ValueError(f"Unknown model_type: {self.model_type}")
                
                logger.info(f"Модель загружена из {self.model_path}")
                return self.model
            except Exception as e:
                logger.error(f"Ошибка загрузки модели: {e}, будет выполнено обучение")
        
        # Обучение новой модели
        logger.info(f"Начало обучения модели {self.model_type}...")
        
        interactions, user_features, item_features = self._prepare_training_data()
        
        if interactions is None:
            logger.error("Недостаточно данных для обучения модели")
            return None
        
        # Создаем и обучаем модель в зависимости от типа
        if self.model_type == 'funksvd':
            self.model = PersonalityFunkSVD(
                n_factors=20,
                lr=0.005,
                reg=0.02,
                n_epochs=20,
                random_state=42
            )
            # Для FunkSVD нужны только extraversion и openness
            # Проверяем наличие нужных колонок
            required_cols = ['extraversion', 'openness']
            available_cols = [col for col in required_cols if col in user_features.columns]
            
            if len(available_cols) < 2:
                logger.error(f"Для модели FunkSVD необходимы колонки {required_cols}")
                return None
            
            # Берем только нужные колонки
            user_features_subset = user_features[available_cols].copy()
            self.model.fit(interactions, user_features_subset, None)
            
        elif self.model_type == 'fm':
            self.model = FactorizationMachine(
                n_components=20,
                learning_rate=0.05,
                loss='warp',
                random_state=42
            )
            self.model.fit(interactions, user_features, item_features)
        
        # Сохраняем модель
        self.model.save(self.model_path)
        logger.info(f"Модель сохранена в {self.model_path}")
        
        return self.model
    
    def _get_fallback_recommendations(self, username: str, top_n: int = 20) -> List[Dict[str, Any]]:
        """Возвращает fallback рекомендации (глобально популярные треки)"""
        user_track_ids = self.get_user_favorite_track_ids(username)
        recommendations = self.get_global_popular_tracks(top_n=top_n * 2, exclude_track_ids=user_track_ids)
        
        # Если все равно не хватает, возвращаем без исключения
        if len(recommendations) < top_n:
            recommendations = self.get_global_popular_tracks(top_n=top_n * 2)
        
        for rec in recommendations[:top_n]:
            if 'recommendation_reason' not in rec:
                rec['recommendation_reason'] = 'Популярный трек'
        
        return recommendations[:top_n]
    
    def get_recommendations(self, username: str, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Главная функция получения рекомендаций.
        
        Если модель недоступна - использует fallback (глобально популярные треки).
        Если модель доступна - использует ее для персонализированных рекомендаций.
        
        Parameters
        ----------
        username : str
            Имя пользователя
        top_n : int
            Количество рекомендаций
        
        Returns
        -------
        list
            Список словарей с информацией о треках и причиной рекомендации
        """
        # Проверяем существование пользователя
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            logger.warning(f"Пользователь {username} не найден")
            return []
        
        # Загружаем или обучаем модель
        model = self._load_or_train_model()
        
        if model is None:
            logger.warning("Модель недоступна, используем fallback (глобально популярные треки)")
            return self._get_fallback_recommendations(username, top_n)
        
        # Получаем все возможные треки-кандидаты
        conn = get_db_connection()
        try:
            all_tracks_query = "SELECT id FROM tracks"
            all_tracks = pd.read_sql(all_tracks_query, conn)
            candidate_items = all_tracks['id'].tolist()
        except Exception as e:
            logger.error(f"Ошибка получения списка треков: {e}")
            return self._get_fallback_recommendations(username, top_n)
        finally:
            conn.close()
        
        # Исключаем уже избранные треки пользователя
        user_favorites = self.get_user_favorite_track_ids(username)
        candidate_items = [item for item in candidate_items if item not in user_favorites]
        
        if not candidate_items:
            logger.info(f"У пользователя {username} нет доступных для рекомендации треков")
            return self._get_fallback_recommendations(username, top_n)
        
        # Получаем рекомендации от модели (с запасом, чтобы после фильтрации хватило)
        try:
            recommended_ids = model.recommend(user_id, candidate_items, top_n=top_n * 2)
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций от модели: {e}")
            return self._get_fallback_recommendations(username, top_n)
        
        # Получаем детальную информацию
        recommended_tracks = self.get_tracks_details(recommended_ids)
        
        # Добавляем пояснение в зависимости от типа модели
        if self.model_type == 'funksvd':
            reason = 'Рекомендация на основе ваших черт личности (экстраверсия и открытость)'
        else:
            reason = 'Персональная рекомендация на основе ваших предпочтений и черт личности'
        
        for track in recommended_tracks:
            track['recommendation_reason'] = reason
        
        # Если рекомендаций меньше top_n, добиваем популярными
        if len(recommended_tracks) < top_n:
            existing_ids = {t['id'] for t in recommended_tracks}
            needed = top_n - len(recommended_tracks)
            
            additional = self.get_global_popular_tracks(
                top_n=needed * 2, 
                exclude_track_ids=user_favorites.union(existing_ids)
            )
            
            for track in additional:
                if track['id'] not in existing_ids and track['id'] not in user_favorites:
                    track['recommendation_reason'] = 'Популярный трек (дополнение)'
                    recommended_tracks.append(track)
                    if len(recommended_tracks) >= top_n:
                        break
        
        return recommended_tracks[:top_n]
    
    def get_mood_based_recommendations(self, username, mood, top_n=10):
        """
        Получить рекомендации на основе настроения.
        mood: 'energetic', 'calm', 'sad', 'happy', 'romantic'
        """
        user_id = self.get_user_id_by_username(username)
        if not user_id:
            return []

        # Маппинг настроений на ключевые слова жанров
        mood_genres = {
            'energetic': ['rock', 'metal', 'punk', 'hard rock', 'alternative', 'electronic', 'dance', 'edm'],
            'calm': ['ambient', 'chillout', 'classical', 'acoustic', 'folk', 'indie folk', 'lounge', 'new age'],
            'sad': ['blues', 'sad', 'melancholic', 'emo', 'ballad', 'slow', 'acoustic rock', 'indie'],
            'happy': ['pop', 'happy', 'uplifting', 'disco', 'funk', 'soul', 'reggae', 'ska', 'country'],
            'romantic': ['romance', 'love', 'ballad', 'r&b', 'soul', 'easy listening', 'soft rock', 'jazz']
        }

        if mood not in mood_genres:
            mood = 'happy'

        genre_keywords = mood_genres[mood]
        description = f'Подборка треков для настроения: {mood}'

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            user_track_ids = self.get_user_favorite_track_ids(username)

            # Строим условия поиска по жанрам
            genre_conditions = []
            params = []
            for kw in genre_keywords:
                genre_conditions.append("t.genre ILIKE %s")
                params.append(f'%{kw}%')

            where_clause = " OR ".join(genre_conditions)

            # Запрос: выбираем треки подходящих жанров, исключая избранное пользователя,
            # сортируем по убыванию популярности (likes_count) и случайно внутри одинаковой популярности.
            # Для разнообразия используем RANDOM() после сортировки по лайкам.
            query = f"""
                SELECT 
                    t.id,
                    t.title,
                    t.artist,
                    t.genre,
                    t.cover_url,
                    t.file_url,
                    COALESCE(COUNT(f.user_id), 0) as likes_count
                FROM tracks t
                LEFT JOIN favorites f ON t.id = f.track_id
                WHERE ({where_clause})
                AND t.id != ALL(%s)
                GROUP BY t.id
                ORDER BY likes_count DESC, RANDOM()
                LIMIT %s
            """
            params.append(list(user_track_ids) if user_track_ids else [-1])
            params.append(top_n * 2)  # берём с запасом, потом перемешаем

            cur.execute(query, params)
            tracks = cur.fetchall()

            # Перемешиваем для разнообразия (чтобы не всегда одни и те же топы)
            import random
            random.shuffle(tracks)

            # Добавляем пояснение
            for track in tracks[:top_n]:
                track['recommendation_reason'] = description

            return tracks[:top_n]

        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций по настроению: {e}")
            # Возвращаем глобально популярные как fallback
            return self.get_global_popular_tracks(top_n)
        finally:
            cur.close()
            conn.close()
    
    def get_recommendations_for_user_id(self, user_id: int, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Получает рекомендации по user_id (удобно для API).
        
        Parameters
        ----------
        user_id : int
            ID пользователя
        top_n : int
            Количество рекомендаций
        
        Returns
        -------
        list
            Список словарей с информацией о треках
        """
        username = self.get_username_by_user_id(user_id)
        if not username:
            logger.warning(f"Пользователь с id={user_id} не найден")
            return []
        
        return self.get_recommendations(username, top_n)
    
    def retrain_model(self) -> bool:
        """
        Принудительно переобучает модель.
        
        Returns
        -------
        bool
            True если обучение успешно, иначе False
        """
        logger.info("Принудительное переобучение модели...")
        self.force_retrain = True
        self.model = None
        
        # Удаляем старый файл модели
        if os.path.exists(self.model_path):
            try:
                os.remove(self.model_path)
                logger.info(f"Удален старый файл модели: {self.model_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить старый файл модели: {e}")
        
        # Обучаем новую модель
        model = self._load_or_train_model()
        self.force_retrain = False
        
        return model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о текущей модели.
        
        Returns
        -------
        dict
            Информация о модели
        """
        info = {
            'model_type': self.model_type,
            'model_path': self.model_path,
            'model_loaded': self.model is not None,
            'model_file_exists': os.path.exists(self.model_path)
        }
        
        if self.model_type == 'funksvd' and self.model:
            info['n_factors'] = self.model.n_factors
            info['n_users'] = len(self.model.user_vectors_)
            info['n_items'] = len(self.model.item_vectors_)
        elif self.model_type == 'fm' and self.model:
            info['n_components'] = self.model.n_components
            info['loss'] = self.model.loss
        
        return info
