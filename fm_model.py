import numpy as np
import pandas as pd
import pickle
import logging
from typing import List, Dict
from scipy.sparse import csr_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import CountVectorizer
from base_recommender import BaseRecommender

logger = logging.getLogger(__name__)

class FactorizationMachine(BaseRecommender):
    """
    Факторизационная машина на основе ALS (Implicit).
    Работает без LightFM, использует библиотеку implicit.
    """
    
    def __init__(self, n_factors=20, regularization=0.02, iterations=20, random_state=42):
        self.n_factors = n_factors
        self.regularization = regularization
        self.iterations = iterations
        self.random_state = random_state
        self.model = None
        self.user_id_map = {}
        self.item_id_map = {}
        self.reverse_user_map = {}
        self.reverse_item_map = {}
        
    def _prepare_user_features(self, user_features: pd.DataFrame) -> pd.DataFrame:
        """Подготовка признаков пользователей."""
        df = user_features.copy()
        
        numeric_cols = ['extraversion', 'conscientiousness', 'agreeableness',
                        'neuroticism', 'openness', 'age']
        existing_numeric = [c for c in numeric_cols if c in df.columns]
        
        if existing_numeric:
            
            scaler = StandardScaler()
            df[existing_numeric] = df[existing_numeric].fillna(0)
            df[existing_numeric] = scaler.fit_transform(df[existing_numeric])
        
        if 'gender' in df.columns:
            df['gender'] = df['gender'].fillna('unknown')
            gender_dummies = pd.get_dummies(df['gender'], prefix='gender')
            df = pd.concat([df, gender_dummies], axis=1)
            df.drop('gender', axis=1, inplace=True)
        
        return df
    
    def _prepare_item_features(self, item_features: pd.DataFrame) -> pd.DataFrame:
        """Подготовка признаков треков."""
        df = item_features.copy()
        
        if 'duration' in df.columns:
            df['duration'] = df['duration'].fillna(0)
            scaler = StandardScaler()
            df['duration'] = scaler.fit_transform(df[['duration']])
        
        if 'artist' in df.columns:
            df['artist'] = df['artist'].fillna('unknown')
            
            top_artists = df['artist'].value_counts().head(100).index
            df['artist'] = df['artist'].apply(lambda x: x if x in top_artists else 'other')
            artist_dummies = pd.get_dummies(df['artist'], prefix='artist')
            df = pd.concat([df, artist_dummies], axis=1)
            df.drop('artist', axis=1, inplace=True)
        
        if 'genre' in df.columns:
            df['genre'] = df['genre'].fillna('')
            vectorizer = CountVectorizer(token_pattern=r'(?u)\b\w+\b', binary=True, max_features=50)
            genre_matrix = vectorizer.fit_transform(df['genre'])
            genre_df = pd.DataFrame(genre_matrix.toarray(), 
                                    columns=[f'genre_{w}' for w in vectorizer.get_feature_names_out()],
                                    index=df.index)
            df = pd.concat([df, genre_df], axis=1)
            df.drop('genre', axis=1, inplace=True)
        
        return df
    
    def fit(self, interactions: pd.DataFrame, user_features: pd.DataFrame, item_features: pd.DataFrame):
        """
        Обучает модель ALS.
        
        Parameters
        ----------
        interactions : pd.DataFrame
            Колонки ['user_id', 'item_id', 'rating']
        user_features : pd.DataFrame
            Индекс = user_id, колонки с признаками пользователей
        item_features : pd.DataFrame
            Индекс = item_id, колонки с признаками треков
        """
        
        if 'track_id' in interactions.columns:
            interactions = interactions.rename(columns={'track_id': 'item_id'})
        
        self.user_feat_matrix = self._prepare_user_features(user_features)
        self.item_feat_matrix = self._prepare_item_features(item_features)
        
        all_users = interactions['user_id'].unique()
        all_items = interactions['item_id'].unique()
        
        self.user_id_map = {uid: idx for idx, uid in enumerate(all_users)}
        self.item_id_map = {iid: idx for idx, iid in enumerate(all_items)}
        self.reverse_user_map = {idx: uid for uid, idx in self.user_id_map.items()}
        self.reverse_item_map = {idx: iid for iid, idx in self.item_id_map.items()}
        
        n_users = len(all_users)
        n_items = len(all_items)
        
        rows = [self.user_id_map[uid] for uid in interactions['user_id']]
        cols = [self.item_id_map[iid] for iid in interactions['item_id']]
        data = [1.0] * len(rows)
        
        self.user_item_matrix = csr_matrix((data, (rows, cols)), shape=(n_users, n_items))
        
        try:
            from implicit.als import AlternatingLeastSquares
            
            self.model = AlternatingLeastSquares(
                factors=self.n_factors,
                regularization=self.regularization,
                iterations=self.iterations,
                random_state=self.random_state,
                num_threads=0
            )
            
            self.model.fit(self.user_item_matrix)
            logger.info(f"Модель ALS обучена: {n_users} пользователей, {n_items} треков")
            
        except ImportError:
            logger.error("Библиотека implicit не установлена. Установите: pip install implicit")
            raise
    
    def predict(self, user_id: int, item_id: int) -> float:
        """Возвращает предсказанный рейтинг."""
        if self.model is None:
            raise RuntimeError("Модель не обучена")
        
        if user_id not in self.user_id_map or item_id not in self.item_id_map:
            return 0.0
        
        u_idx = self.user_id_map[user_id]
        i_idx = self.item_id_map[item_id]
        
        try:
            score = self.model.user_factors[u_idx].dot(self.model.item_factors[i_idx])
            return float(score)
        except:
            return 0.0
    
    def recommend(self, user_id: int, candidate_items: List[int], top_n: int = 10) -> List[int]:
        """Возвращает топ-N item_id из списка кандидатов."""
        if not candidate_items or self.model is None:
            return []
        
        if user_id not in self.user_id_map:
            return candidate_items[:top_n]
        
        u_idx = self.user_id_map[user_id]
        
        valid_items = [(i, self.item_id_map.get(i)) for i in candidate_items if i in self.item_id_map]
        
        if not valid_items:
            return []
        
        scores = []
        for orig_id, idx in valid_items:
            score = self.model.user_factors[u_idx].dot(self.model.item_factors[idx])
            scores.append((orig_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scores[:top_n]]
    
    def save(self, path: str):
        """Сохраняет модель."""
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'user_id_map': self.user_id_map,
                'item_id_map': self.item_id_map,
                'reverse_user_map': self.reverse_user_map,
                'reverse_item_map': self.reverse_item_map,
                'user_feat_matrix': self.user_feat_matrix,
                'item_feat_matrix': self.item_feat_matrix,
                'n_factors': self.n_factors,
                'regularization': self.regularization,
                'iterations': self.iterations,
            }, f)
    
    @classmethod
    def load(cls, path: str):
        """Загружает модель."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        instance = cls(
            n_factors=data['n_factors'],
            regularization=data['regularization'],
            iterations=data['iterations']
        )
        instance.model = data['model']
        instance.user_id_map = data['user_id_map']
        instance.item_id_map = data['item_id_map']
        instance.reverse_user_map = data['reverse_user_map']
        instance.reverse_item_map = data['reverse_item_map']
        instance.user_feat_matrix = data.get('user_feat_matrix')
        instance.item_feat_matrix = data.get('item_feat_matrix')
        
        return instance