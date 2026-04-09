import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple
import pickle
import os
from base_recommender import BaseRecommender

class TwoTowerDataset(Dataset):
    """Dataset для обучения двухбашенной модели с генерацией отрицательных примеров."""
    def __init__(self, interactions: pd.DataFrame, user_features: pd.DataFrame, item_texts: Dict[int, str],
                 num_negatives: int = 5):
        """
        interactions: колонки ['user_id', 'item_id', 'rating'] (rating = 1 для положительных)
        user_features: DataFrame с индексом user_id и колонками признаков
        item_texts: словарь {item_id: "автор | название"}
        num_negatives: сколько отрицательных примеров на один положительный
        """
        
        if 'track_id' in interactions.columns and 'item_id' not in interactions.columns:
            interactions = interactions.rename(columns={'track_id': 'item_id'})
        
        valid_users = set(user_features.index)
        mask = interactions['user_id'].isin(valid_users)
        interactions = interactions[mask].copy()
        
        self.user_ids = interactions['user_id'].values
        self.item_ids = interactions['item_id'].values
        self.ratings = interactions['rating'].values
        self.user_features = user_features
        self.item_texts = item_texts
        self.num_negatives = num_negatives
        self.all_item_ids = list(item_texts.keys())

    def __len__(self):
        return len(self.user_ids)

    def __getitem__(self, idx):
        user_id = self.user_ids[idx]
        pos_item_id = self.item_ids[idx]
        rating = self.ratings[idx]

        neg_item_ids = []
        while len(neg_item_ids) < self.num_negatives:
            neg_candidate = np.random.choice(self.all_item_ids)
            if neg_candidate != pos_item_id:
                neg_item_ids.append(neg_candidate)

        user_feat = self.user_features.loc[user_id].values.astype(np.float32)

        pos_text = self.item_texts[pos_item_id]
        neg_texts = [self.item_texts[neg_id] for neg_id in neg_item_ids]

        return (torch.tensor(user_feat, dtype=torch.float32),
                pos_text,
                neg_texts,
                torch.tensor(rating, dtype=torch.float32))

def collate_fn(batch, text_encoder, device):
    """Функция для коллации батча: кодирует тексты через предобученный SentenceTransformer."""
    user_feats = []
    pos_texts = []
    neg_texts_list = []
    ratings = []

    for user_feat, pos_text, neg_texts, rating in batch:
        user_feats.append(user_feat)
        pos_texts.append(pos_text)
        neg_texts_list.extend(neg_texts)
        ratings.append(rating)

    user_feats = torch.stack(user_feats).to(device)

    with torch.no_grad():
        pos_emb = text_encoder.encode(pos_texts, convert_to_tensor=True, device=device)
        neg_emb = text_encoder.encode(neg_texts_list, convert_to_tensor=True, device=device)
        
        pos_emb = pos_emb.clone().detach().requires_grad_(True)
        neg_emb = neg_emb.clone().detach().requires_grad_(True)

    num_neg_per_sample = len(neg_texts_list) // len(batch)
    neg_emb = neg_emb.view(len(batch), num_neg_per_sample, -1)

    ratings = torch.tensor(ratings, dtype=torch.float32).to(device)
    return user_feats, pos_emb, neg_emb, ratings
def collate_fn(batch, text_encoder, device):
    """Функция для коллации батча: кодирует тексты через предобученный SentenceTransformer."""
    user_feats = []
    pos_texts = []
    neg_texts_list = []
    ratings = []

    for user_feat, pos_text, neg_texts, rating in batch:
        user_feats.append(user_feat)
        pos_texts.append(pos_text)
        neg_texts_list.extend(neg_texts)
        ratings.append(rating)

    user_feats = torch.stack(user_feats).to(device)

    with torch.no_grad():
        pos_emb = text_encoder.encode(pos_texts, convert_to_tensor=True, device=device)
        neg_emb = text_encoder.encode(neg_texts_list, convert_to_tensor=True, device=device)
        
        pos_emb = pos_emb.clone().detach().requires_grad_(True)
        neg_emb = neg_emb.clone().detach().requires_grad_(True)

    num_neg_per_sample = len(neg_texts_list) // len(batch)
    neg_emb = neg_emb.view(len(batch), num_neg_per_sample, -1)

    ratings = torch.tensor(ratings, dtype=torch.float32).to(device)
    return user_feats, pos_emb, neg_emb, ratings

class UserTower(nn.Module):
    """Башня пользователя."""
    def __init__(self, input_dim: int, hidden_dims: List[int], dim_out: int):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for hdim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hdim))
            layers.append(nn.BatchNorm1d(hdim))
            layers.append(nn.ReLU())
            prev_dim = hdim
        layers.append(nn.Linear(prev_dim, dim_out))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

class ItemTower(nn.Module):
    """Башня товара."""
    def __init__(self, text_dim: int, hidden_dims: List[int], dim_out: int):
        super().__init__()
        layers = []
        prev_dim = text_dim
        for hdim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hdim))
            layers.append(nn.BatchNorm1d(hdim))
            layers.append(nn.ReLU())
            prev_dim = hdim
        layers.append(nn.Linear(prev_dim, dim_out))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

class TwoTowerModel(nn.Module):
    def __init__(self, user_input_dim: int, text_dim: int, user_hidden: List[int], item_hidden: List[int],
                 embedding_dim: int):
        super().__init__()
        self.user_tower = UserTower(user_input_dim, user_hidden, embedding_dim)
        self.item_tower = ItemTower(text_dim, item_hidden, embedding_dim)

    def forward(self, user_feats, item_embs):
        user_emb = self.user_tower(user_feats)
        item_emb = self.item_tower(item_embs)
        scores = (user_emb * item_emb).sum(dim=1)
        return scores, user_emb, item_emb

class TwoTowerRecommender(BaseRecommender):
    def __init__(self, embedding_dim=64, user_hidden=[128, 64], item_hidden=[128, 64],
                 text_encoder_name='distiluse-base-multilingual-cased-v2',
                 batch_size=256, epochs=10, lr=0.001, num_negatives=5):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.user_hidden = user_hidden
        self.item_hidden = item_hidden
        self.text_encoder_name = text_encoder_name
        self.batch_size = batch_size
        self.epochs = epochs
        self.lr = lr
        self.num_negatives = num_negatives

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.text_encoder = None
        self.model = None
        self.user_features_df = None
        self.item_texts = None
        self.user_normalizer = None

    def _prepare_features(self, user_features: pd.DataFrame, item_features: pd.DataFrame, train_users: set = None):
        """
        Подготовка признаков пользователя и текстов треков.
        train_users - множество user_id, которые есть в train_df
        """
        print(f"\n=== ПОДГОТОВКА ПРИЗНАКОВ ===")
        print(f"user_features shape: {user_features.shape}")
        if train_users:
            print(f"train_users (первые 5): {list(train_users)[:5]}")
        
        user_feats = user_features.copy()
        
        if train_users is not None and len(train_users) > 0:
            original_count = len(user_feats)
            user_feats = user_feats[user_feats.index.isin(train_users)].copy()
            print(f"После фильтрации пользователей по train_users: {len(user_feats)} (было {original_count})")
        
        if len(user_feats) == 0:
            print("ВНИМАНИЕ: Нет пользователей после фильтрации! Использую всех пользователей.")
            user_feats = user_features.copy()

        if 'gender' in user_feats.columns:
            gender_dummies = pd.get_dummies(user_feats['gender'], prefix='gender')
            user_feats = pd.concat([user_feats, gender_dummies], axis=1)
            user_feats.drop('gender', axis=1, inplace=True)

        numeric_cols = ['age', 'extraversion', 'openness']
        self.user_normalizer = {}
        for col in numeric_cols:
            if col in user_feats.columns:
                mean = user_feats[col].mean()
                std = user_feats[col].std()
                if std == 0:
                    std = 1.0
                self.user_normalizer[col] = (mean, std)
                user_feats[col] = (user_feats[col] - mean) / std
            else:
                user_feats[col] = 0.0
                self.user_normalizer[col] = (0.0, 1.0)

        user_feats = user_feats.fillna(0.0)
        self.user_features_df = user_feats
        print(f"Итоговое количество пользователей в features: {len(self.user_features_df)}")

        item_texts = {}
        print(f"Подготовка текстов для {len(item_features)} треков...")
        for item_id in item_features.index:
            artist = str(item_features.loc[item_id, 'artist']) if pd.notna(item_features.loc[item_id, 'artist']) else ''
            title = str(item_features.loc[item_id, 'title']) if pd.notna(item_features.loc[item_id, 'title']) else ''
            genre = str(item_features.loc[item_id, 'genre']) if pd.notna(item_features.loc[item_id, 'genre']) else ''
            # Добавляем жанр в текст для лучших эмбеддингов
            text = f"{artist} {title} {genre}".strip()
            if not text or text == '':
                text = "unknown music track"
            item_texts[item_id] = text
        
        self.item_texts = item_texts
        print(f"Подготовлено текстов для {len(item_texts)} треков")

        self.user_input_dim = len(user_feats.columns)
        print(f"Размерность признаков пользователя: {self.user_input_dim}")

        if self.text_encoder is None:
            print(f"Загрузка текстового энкодера {self.text_encoder_name}...")
            self.text_encoder = SentenceTransformer(self.text_encoder_name, device=self.device)
        self.text_dim = self.text_encoder.get_embedding_dimension()
        print(f"Размерность текстовых эмбеддингов: {self.text_dim}")
        print(f"=== КОНЕЦ ПОДГОТОВКИ ПРИЗНАКОВ ===\n")

    def fit(self, interactions: pd.DataFrame, user_features: pd.DataFrame, item_features: pd.DataFrame):
        """
        Обучение модели.
        """
        print(f"\n=== НАЧАЛО ОБУЧЕНИЯ ===")
        print(f"interactions shape: {interactions.shape}")
        print(f"user_features shape: {user_features.shape}")
        print(f"item_features shape: {item_features.shape}")
        
        if 'track_id' in interactions.columns and 'item_id' not in interactions.columns:
            interactions = interactions.rename(columns={'track_id': 'item_id'})
        
        print(f"Уникальные рейтинги в interactions: {sorted(interactions['rating'].unique())}")
        
        interactions_for_train = interactions.copy()
        interactions_for_train['rating'] = (interactions_for_train['rating'] > 0).astype(float)
        print(f"После бинаризации рейтингов: уникальные значения {interactions_for_train['rating'].unique()}")
        
        pos_interactions = interactions_for_train[interactions_for_train['rating'] > 0].copy()
        print(f"Положительных взаимодействий: {len(pos_interactions)}")
        
        if len(pos_interactions) == 0:
            print("ОШИБКА: Нет положительных взаимодействий для обучения!")
            print(f"Рейтинги в данных: {interactions['rating'].unique()}")
            
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        train_users = set(pos_interactions['user_id'].unique())
        print(f"Уникальных пользователей в обучающих данных: {len(train_users)}")
        print(f"Список пользователей (первые 10): {list(train_users)[:10]}")
        
        self._prepare_features(user_features, item_features, train_users)
        
        if self.user_features_df is None or len(self.user_features_df) == 0:
            print("ОШИБКА: Нет пользователей после фильтрации признаков!")
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        print(f"Пользователей в user_features_df после фильтрации: {len(self.user_features_df)}")
        print(f"Их ID: {list(self.user_features_df.index)}")
        
        users_in_features = set(self.user_features_df.index)
        train_users_set = set(train_users)
        common_users = train_users_set.intersection(users_in_features)
        print(f"Общих пользователей: {len(common_users)}")
        print(f"Общие ID: {list(common_users)}")
        
        if len(common_users) == 0:
            print("ОШИБКА: Нет общих пользователей!")
            print(f"Пользователи в train (первые 10): {list(train_users_set)[:10]}")
            print(f"Пользователи в features: {list(users_in_features)}")
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        filtered_pos = pos_interactions[pos_interactions['user_id'].isin(users_in_features)].copy()
        print(f"Положительных взаимодействий после фильтрации по пользователям: {len(filtered_pos)}")
        
        if len(filtered_pos) == 0:
            print("ОШИБКА: Нет взаимодействий после фильтрации по пользователям!")
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        print(f"Всего треков в item_features: {len(item_features)}")
        print(f"Треков в filtered_pos: {filtered_pos['item_id'].nunique()}")
        
        tracks_in_interactions = set(filtered_pos['item_id'].unique())
        tracks_in_texts = set(self.item_texts.keys())
        common_tracks = tracks_in_interactions.intersection(tracks_in_texts)
        print(f"Общих треков (interactions ∩ item_texts): {len(common_tracks)}")
        
        if len(common_tracks) == 0:
            print("ОШИБКА: Нет общих треков!")
            print(f"Треки в interactions (первые 5): {list(tracks_in_interactions)[:5]}")
            print(f"Треки в texts (первые 5): {list(tracks_in_texts)[:5]}")
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        filtered_pos = filtered_pos[filtered_pos['item_id'].isin(tracks_in_texts)].copy()
        print(f"После фильтрации по трекам: {len(filtered_pos)}")
        
        if len(filtered_pos) == 0:
            print("ОШИБКА: Нет взаимодействий после фильтрации по трекам!")
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        try:
            dataset = TwoTowerDataset(filtered_pos, self.user_features_df, self.item_texts,
                                    num_negatives=self.num_negatives)
            print(f"Размер датасета: {len(dataset)}")
        except Exception as e:
            print(f"Ошибка при создании датасета: {e}")
            import traceback
            traceback.print_exc()
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        if len(dataset) == 0:
            print("ОШИБКА: Пустой датасет!")
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            self.item_emb_dict = {}
            return
        
        self.model = TwoTowerModel(
            user_input_dim=self.user_input_dim,
            text_dim=self.text_dim,
            user_hidden=self.user_hidden,
            item_hidden=self.item_hidden,
            embedding_dim=self.embedding_dim
        ).to(self.device)
        print(f"Модель создана, параметров: {sum(p.numel() for p in self.model.parameters())}")
        
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        
        def collate(batch):
            return collate_fn(batch, self.text_encoder, self.device)
        
        batch_size = min(self.batch_size, len(dataset))
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, collate_fn=collate)
        print(f"Batch size: {batch_size}, количество батчей: {len(dataloader)}")
        
        bce_loss = nn.BCEWithLogitsLoss()
        
        print(f"Starting training on {self.device} for {self.epochs} epochs...")
        
        for epoch in range(self.epochs):
            total_loss = 0.0
            self.model.train()
            for batch_idx, (user_feats, pos_emb, neg_emb, ratings) in enumerate(dataloader):
                
                pos_emb = pos_emb.clone().detach().requires_grad_(True)
                neg_emb = neg_emb.clone().detach().requires_grad_(True)
                
                pos_scores, _, _ = self.model(user_feats, pos_emb)
                
                batch_size_curr, K, _ = neg_emb.shape
                neg_emb_flat = neg_emb.view(batch_size_curr * K, -1)
                user_feats_expanded = user_feats.repeat_interleave(K, dim=0)
                neg_scores, _, _ = self.model(user_feats_expanded, neg_emb_flat)
                neg_scores = neg_scores.view(batch_size_curr, K)
                
                pos_targets = torch.ones_like(pos_scores)
                neg_targets = torch.zeros_like(neg_scores.view(-1))
                
                loss_pos = bce_loss(pos_scores, pos_targets)
                loss_neg = bce_loss(neg_scores.view(-1), neg_targets)
                
                loss = loss_pos + loss_neg
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            avg_loss = total_loss / len(dataloader) if len(dataloader) > 0 else 0
            print(f"Epoch {epoch+1}/{self.epochs}, Loss: {avg_loss:.4f}")
        
        self._compute_all_item_embeddings()
        print(f"Обучение завершено. Эмбеддингов треков: {len(self.item_embeddings)}")
        print(f"=== КОНЕЦ ОБУЧЕНИЯ ===\n")

    def _compute_all_item_embeddings(self):
        """Предвычисляет эмбеддинги всех треков."""
        if self.model is None:
            self.item_embeddings = np.zeros((0, self.embedding_dim))
            self.item_ids_list = []
            return
            
        self.model.eval()
        all_item_embs = []
        item_ids_list = []
        print(f"Вычисление эмбеддингов для {len(self.item_texts)} треков...")
        
        with torch.no_grad():
            for item_id, text in self.item_texts.items():
                text_emb = self.text_encoder.encode(text, convert_to_tensor=True, device=self.device)
                text_emb = text_emb.unsqueeze(0)
                item_emb = self.model.item_tower(text_emb)
                all_item_embs.append(item_emb.cpu().numpy())
                item_ids_list.append(item_id)
        
        self.item_embeddings = np.vstack(all_item_embs) if all_item_embs else np.zeros((0, self.embedding_dim))
        self.item_ids_list = item_ids_list
        self.item_emb_dict = {iid: emb for iid, emb in zip(self.item_ids_list, self.item_embeddings)}
        print(f"Вычислено {len(self.item_embeddings)} эмбеддингов треков")

    def predict(self, user_id: int, item_id: int) -> float:
        """Предсказать score для пары пользователь-трек."""
        if self.model is None:
            return 0.0
        
        if user_id not in self.user_features_df.index:
            return 0.0
            
        self.model.eval()
        user_feat = self.user_features_df.loc[user_id].values.astype(np.float32)
        user_feat_t = torch.tensor(user_feat, dtype=torch.float32, device=self.device).unsqueeze(0)
        text = self.item_texts.get(item_id, "unknown")
        text_emb = self.text_encoder.encode(text, convert_to_tensor=True, device=self.device).unsqueeze(0)
        with torch.no_grad():
            score, _, _ = self.model(user_feat_t, text_emb)
        return score.item()

    def recommend(self, user_id: int, candidate_items: List[int], top_n: int = 10) -> List[int]:
        """Возвращает топ-N треков из списка кандидатов."""
        if self.model is None or not hasattr(self, 'item_embeddings') or len(self.item_embeddings) == 0:
            print(f"Невозможно получить рекомендации: model={self.model is not None}, embeddings={len(self.item_embeddings) if hasattr(self, 'item_embeddings') else 0}")
            return candidate_items[:top_n] if candidate_items else []
        
        if user_id not in self.user_features_df.index:
            print(f"Пользователь {user_id} не найден в user_features_df")
            return candidate_items[:top_n] if candidate_items else []

        self.model.eval()

        if candidate_items is None:
            candidate_items = self.item_ids_list

        user_feat = self.user_features_df.loc[user_id].values.astype(np.float32)
        user_feat_t = torch.tensor(user_feat, dtype=torch.float32, device=self.device).unsqueeze(0)

        with torch.no_grad():
            user_emb = self.model.user_tower(user_feat_t).cpu().numpy().flatten()

        scores = []
        for item_id in candidate_items:
            if item_id in self.item_emb_dict:
                item_emb = self.item_emb_dict[item_id]
                score = np.dot(user_emb, item_emb)
                scores.append((item_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [item_id for item_id, _ in scores[:top_n]]

    def save(self, path: str):
        """Сохраняет модель."""
        os.makedirs(path, exist_ok=True)
        if self.model is not None:
            torch.save(self.model.state_dict(), os.path.join(path, 'model_weights.pt'))
        
        config = {
            'embedding_dim': self.embedding_dim,
            'user_hidden': self.user_hidden,
            'item_hidden': self.item_hidden,
            'text_encoder_name': self.text_encoder_name,
            'batch_size': self.batch_size,
            'epochs': self.epochs,
            'lr': self.lr,
            'num_negatives': self.num_negatives,
            'user_input_dim': self.user_input_dim,
            'text_dim': self.text_dim,
            'user_normalizer': self.user_normalizer,
            'user_features_columns': list(self.user_features_df.columns) if self.user_features_df is not None else [],
            'user_features_index': self.user_features_df.index.tolist() if self.user_features_df is not None else [],
            'user_features_values': self.user_features_df.values if self.user_features_df is not None else [],
            'item_texts': self.item_texts,
            'item_ids_list': self.item_ids_list if hasattr(self, 'item_ids_list') else [],
            'item_embeddings': self.item_embeddings if hasattr(self, 'item_embeddings') else np.zeros((0, self.embedding_dim)),
        }
        with open(os.path.join(path, 'config.pkl'), 'wb') as f:
            pickle.dump(config, f)

    @classmethod
    def load(cls, path: str):
        """Загружает модель."""
        with open(os.path.join(path, 'config.pkl'), 'rb') as f:
            config = pickle.load(f)

        recommender = cls(
            embedding_dim=config['embedding_dim'],
            user_hidden=config['user_hidden'],
            item_hidden=config['item_hidden'],
            text_encoder_name=config['text_encoder_name'],
            batch_size=config['batch_size'],
            epochs=config['epochs'],
            lr=config['lr'],
            num_negatives=config['num_negatives']
        )
        recommender.text_encoder = SentenceTransformer(config['text_encoder_name'], device=recommender.device)
        recommender.user_input_dim = config['user_input_dim']
        recommender.text_dim = config['text_dim']
        recommender.user_normalizer = config['user_normalizer']
        
        if config.get('user_features_values') is not None and len(config['user_features_values']) > 0:
            user_features_df = pd.DataFrame(config['user_features_values'],
                                            index=config['user_features_index'],
                                            columns=config['user_features_columns'])
            recommender.user_features_df = user_features_df
        
        recommender.item_texts = config['item_texts']
        recommender.item_ids_list = config['item_ids_list']
        recommender.item_embeddings = config['item_embeddings']
        recommender.item_emb_dict = {iid: emb for iid, emb in zip(recommender.item_ids_list, recommender.item_embeddings)}

        if config.get('user_input_dim') is not None and config.get('text_dim') is not None:
            recommender.model = TwoTowerModel(
                user_input_dim=recommender.user_input_dim,
                text_dim=recommender.text_dim,
                user_hidden=recommender.user_hidden,
                item_hidden=recommender.item_hidden,
                embedding_dim=recommender.embedding_dim
            ).to(recommender.device)
            
            weights_path = os.path.join(path, 'model_weights.pt')
            if os.path.exists(weights_path):
                recommender.model.load_state_dict(torch.load(weights_path, map_location=recommender.device))
                recommender.model.eval()
        
        return recommender