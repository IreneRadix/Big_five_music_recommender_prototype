import torch
import pandas as pd
import numpy as np
from two_tower_nn import TwoTowerRecommender
from database import get_db_connection
import warnings
warnings.filterwarnings('ignore')

def load_data_from_db():
    """Загружает данные из базы данных для обучения"""
    conn = get_db_connection()
    
    try:
        
        listening_history = pd.read_sql("""
            SELECT 
                lh.user_id,
                lh.track_id,
                COUNT(*) as rating
            FROM listening_history lh
            GROUP BY lh.user_id, lh.track_id
        """, conn)
        
        print(f"Загружено {len(listening_history)} записей прослушиваний")
        if len(listening_history) > 0:
            print(f"Уникальных пользователей: {listening_history['user_id'].nunique()}")
            print(f"Уникальных треков: {listening_history['track_id'].nunique()}")
        
        favorites = pd.read_sql("""
            SELECT 
                user_id,
                track_id,
                2 as rating
            FROM favorites
        """, conn)
        
        print(f"Загружено {len(favorites)} записей избранного")
        
        if len(favorites) > 0:
            interactions = pd.concat([listening_history, favorites], ignore_index=True)
            interactions = interactions.groupby(['user_id', 'track_id'])['rating'].max().reset_index()
        else:
            interactions = listening_history
        
        if len(interactions) == 0:
            print("Нет данных о взаимодействиях!")
            return None, None, None
        
        print(f"Всего взаимодействий: {len(interactions)}")
        
        user_features = pd.read_sql("""
            SELECT 
                u.id as user_id,
                uf.gender,
                uf.age,
                uf.extraversion,
                uf.openness
            FROM users u
            JOIN user_features uf ON u.id = uf.user_id
        """, conn)
        
        if len(user_features) > 0:
            user_features.set_index('user_id', inplace=True)
            print(f"Загружено {len(user_features)} пользователей с признаками")
            print("Признаки пользователей:", user_features.columns.tolist())
            print(user_features.head())
        else:
            print("Внимание: Нет данных о пользователях!")
            return None, None, None
        
        track_features = pd.read_sql("""
            SELECT 
                id as track_id,
                title,
                artist,
                genre
            FROM tracks
        """, conn)
        
        if len(track_features) > 0:
            track_features.set_index('track_id', inplace=True)
            print(f"Загружено {len(track_features)} треков")
            print(track_features.head())
        else:
            print("Внимание: Нет данных о треках!")
            return None, None, None
        
        max_rating = interactions['rating'].max()
        if max_rating > 1:
            interactions['rating'] = interactions['rating'] / max_rating
        
        return interactions, user_features, track_features
        
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None
    finally:
        conn.close()

def prepare_train_test_split(interactions, test_size=0.2):
    """Разделяет данные на обучающую и тестовую выборки"""
    if interactions is None or len(interactions) == 0:
        return None, None
    
    train_list = []
    test_list = []
    
    for user_id in interactions['user_id'].unique():
        user_data = interactions[interactions['user_id'] == user_id].copy()
        
        if len(user_data) >= 2:
            user_data = user_data.sort_values('rating', ascending=False)
            test_size_user = max(1, int(len(user_data) * test_size))
            test_data = user_data.head(test_size_user)
            train_data = user_data.iloc[test_size_user:]
            
            if len(train_data) > 0:
                train_list.append(train_data)
            if len(test_data) > 0:
                test_list.append(test_data)
        else:
            train_list.append(user_data)
    
    train_df = pd.concat(train_list, ignore_index=True) if train_list else pd.DataFrame()
    test_df = pd.concat(test_list, ignore_index=True) if test_list else pd.DataFrame()
    
    print(f"\nОбучающая выборка: {len(train_df)} взаимодействий")
    print(f"Тестовая выборка: {len(test_df)} взаимодействий")
    
    return train_df, test_df

def debug_model_state(recommender, user_id, track_features):
    """Отладочная функция для проверки состояния модели"""
    print("\n" + "=" * 60)
    print("Отладка модели")
    print("=" * 60)
    
    print(f"Модель обучена: {recommender.model is not None}")
    if recommender.model is not None:
        print(f"Модель в режиме eval: {not recommender.model.training}")
    
    print(f"Есть item_embeddings: {hasattr(recommender, 'item_embeddings')}")
    if hasattr(recommender, 'item_embeddings'):
        print(f"Размер item_embeddings: {recommender.item_embeddings.shape if recommender.item_embeddings is not None else 'None'}")
    
    print(f"Есть item_ids_list: {hasattr(recommender, 'item_ids_list')}")
    if hasattr(recommender, 'item_ids_list'):
        print(f"Количество item_ids: {len(recommender.item_ids_list)}")
        if len(recommender.item_ids_list) > 0:
            print(f"Примеры item_ids: {recommender.item_ids_list[:5]}")
    
    print(f"Есть user_features_df: {recommender.user_features_df is not None}")
    if recommender.user_features_df is not None:
        print(f"Пользователи в модели: {len(recommender.user_features_df)}")
        print(f"Пользователь {user_id} в модели: {user_id in recommender.user_features_df.index}")
    
    print(f"Есть item_emb_dict: {hasattr(recommender, 'item_emb_dict')}")
    if hasattr(recommender, 'item_emb_dict'):
        print(f"Размер item_emb_dict: {len(recommender.item_emb_dict)}")

def main():
    """Основная функция для обучения модели"""
    print("=" * 60)
    print("Обучение модели TwoTowerRecommender")
    print("=" * 60)
    
    print("\nЗагрузка данных из базы данных...")
    interactions, user_features, track_features = load_data_from_db()
    
    if interactions is None or len(interactions) == 0:
        print("\nНет данных для обучения!")
        return
    
    print("\nРазделение данных на обучающую и тестовую выборки...")
    train_df, test_df = prepare_train_test_split(interactions, test_size=0.2)
    
    if train_df is None or len(train_df) == 0:
        print("Недостаточно данных для обучения!")
        return
    
    print("\nСоздание и обучение модели...")
    recommender = TwoTowerRecommender(
        embedding_dim=64,
        user_hidden=[128, 64],
        item_hidden=[128, 64],
        text_encoder_name='distiluse-base-multilingual-cased-v2',
        batch_size=256,
        epochs=10,
        lr=0.001,
        num_negatives=5
    )
    
    try:
        
        recommender.fit(train_df, user_features, track_features)
        
        print("\nСохранение модели...")
        recommender.save('two_tower_model')
        print("Модель сохранена в директорию 'two_tower_model'")
        
        sample_user = train_df['user_id'].iloc[0]
        debug_model_state(recommender, sample_user, track_features)
        
        print("\n" + "=" * 60)
        print("Пример рекомендаций")
        print("=" * 60)
        
        sample_users = train_df['user_id'].unique()[:3]
        for user_id in sample_users:
            print(f"\nПользователь {user_id}:")
            
            if user_id not in recommender.user_features_df.index:
                print(f"  Пользователь {user_id} не найден в user_features_df модели!")
                continue
            
            recommendations = recommender.recommend(user_id, None, top_n=5)
            print(f"  Рекомендованные треки (ID): {recommendations}")
            
            if not recommendations:
                print("  ВНИМАНИЕ: Рекомендации пустые!")
                print("  Возможные причины:")
                print("    1. Нет эмбеддингов треков")
                print("    2. Проблема с вычислением скоринга")
                print("    3. Все треки отфильтровались")
                
                try:
                    
                    user_feat = recommender.user_features_df.loc[user_id].values.astype(np.float32)
                    user_feat_t = torch.tensor(user_feat, dtype=torch.float32, device=recommender.device).unsqueeze(0)
                    
                    with torch.no_grad():
                        user_emb = recommender.model.user_tower(user_feat_t).cpu().numpy().flatten()
                    
                    print(f"  Эмбеддинг пользователя получен, размерность: {len(user_emb)}")
                    print(f"  Количество треков для скоринга: {len(recommender.item_ids_list)}")
                    
                    if len(recommender.item_ids_list) > 0:
                        scores = []
                        for i, item_id in enumerate(recommender.item_ids_list[:5]):
                            if item_id in recommender.item_emb_dict:
                                item_emb = recommender.item_emb_dict[item_id]
                                score = np.dot(user_emb, item_emb)
                                scores.append((item_id, score))
                                print(f"    Трек {item_id}: score = {score:.4f}")
                        
                        if scores:
                            scores.sort(key=lambda x: x[1], reverse=True)
                            print(f"  Топ скоры: {scores[:3]}")
                        else:
                            print("  Нет эмбеддингов для треков в item_emb_dict")
                except Exception as e:
                    print(f"  Ошибка при отладке: {e}")
            else:
                
                for track_id in recommendations[:3]:
                    if track_id in track_features.index:
                        track = track_features.loc[track_id]
                        print(f"  - {track['artist']} - {track['title']}")
        
        print("\n" + "=" * 60)
        print("Обучение завершено!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Ошибка при обучении модели: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()