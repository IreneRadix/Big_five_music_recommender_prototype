import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import random
from tqdm import tqdm
import warnings
import pickle
import os
warnings.filterwarnings('ignore')

from personality_funksvd import PersonalityFunkSVD
from two_tower_nn import TwoTowerRecommender
from fm_model import FactorizationMachine
from database import get_db_connection

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 12

class ModelPrecisionTester:
    """Класс для тестирования точности моделей с разным количеством избранных треков"""
    
    def __init__(self, models_path: str = '.'):
        """
        models_path: путь к директории с сохраненными моделями
        """
        self.models_path = models_path
        self.models = {}
        self.user_data = None  
        self.all_tracks = None  
        
    def load_models(self):
        """Загрузка обученных моделей"""
        print("\n=== ЗАГРУЗКА МОДЕЛЕЙ ===")
        
        funksvd_path = f'{self.models_path}/personality_funksvd.pkl'
        if os.path.exists(funksvd_path):
            try:
                with open(funksvd_path, 'rb') as f:
                    self.models['personality_funksvd'] = pickle.load(f)
                print("✓ PersonalityFunkSVD загружена")
            except Exception as e:
                print(f"✗ Ошибка загрузки PersonalityFunkSVD: {e}")
        else:
            print(f"✗ Файл {funksvd_path} не найден")
            
        two_tower_path = f'{self.models_path}/two_tower_model'
        if os.path.exists(two_tower_path):
            try:
                self.models['two_tower'] = TwoTowerRecommender.load(two_tower_path)
                print("✓ TwoTowerNN загружена")
            except Exception as e:
                print(f"✗ Ошибка загрузки TwoTowerNN: {e}")
        else:
            print(f"✗ Директория {two_tower_path} не найдена")
            
        fm_path = f'{self.models_path}/fm_model.pkl'
        if os.path.exists(fm_path):
            try:
                with open(fm_path, 'rb') as f:
                    self.models['fm'] = pickle.load(f)
                print("✓ FM модель загружена")
            except Exception as e:
                print(f"✗ Ошибка загрузки FM: {e}")
        else:
            print(f"✗ Файл {fm_path} не найден")
        
        print(f"\nЗагружено моделей: {len(self.models)}/{3}")
        return len(self.models) > 0
    
    def load_user_data(self):
        """Загрузка данных пользователей и их взаимодействий"""
        print("\n=== ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ ===")
        
        conn = get_db_connection()
        
        try:
            
            query = """
                SELECT 
                    u.id as user_id,
                    COALESCE(f.track_id, lh.track_id) as track_id,
                    CASE 
                        WHEN f.track_id IS NOT NULL THEN 'favorite'
                        ELSE 'listen'
                    END as interaction_type
                FROM users u
                LEFT JOIN favorites f ON u.id = f.user_id
                LEFT JOIN listening_history lh ON u.id = lh.user_id
                WHERE f.track_id IS NOT NULL OR lh.track_id IS NOT NULL
            """
            
            all_interactions = pd.read_sql(query, conn)
            
            if len(all_interactions) == 0:
                print("❌ Нет данных о взаимодействиях!")
                return False
            
            user_tracks = defaultdict(set)
            for _, row in all_interactions.iterrows():
                if pd.notna(row['track_id']):
                    user_tracks[row['user_id']].add(int(row['track_id']))
            
            tracks_df = pd.read_sql("SELECT id as track_id FROM tracks", conn)
            self.all_tracks = tracks_df['track_id'].tolist()
            
            user_features_query = """
                SELECT DISTINCT u.id as user_id
                FROM users u
                JOIN user_features uf ON u.id = uf.user_id
            """
            users_with_features = pd.read_sql(user_features_query, conn)
            users_with_features_set = set(users_with_features['user_id'].tolist())
            
            self.user_data = {}
            users_filtered = 0
            users_no_features = 0
            users_insufficient_tracks = 0
            
            for user_id, tracks in user_tracks.items():
                
                if user_id not in users_with_features_set:
                    users_no_features += 1
                    continue
                
                if len(tracks) < 5:  
                    users_insufficient_tracks += 1
                    continue
                
                user_in_models = True
                for model_name, model in self.models.items():
                    if model_name == 'two_tower':
                        if not hasattr(model, 'user_features_df') or \
                           model.user_features_df is None or \
                           user_id not in model.user_features_df.index:
                            user_in_models = False
                            break
                    elif model_name == 'personality_funksvd':
                        if not hasattr(model, 'user_vectors_') or \
                           user_id not in model.user_vectors_:
                            user_in_models = False
                            break
                    elif model_name == 'fm':
                        if not hasattr(model, 'user_id_map') or \
                           user_id not in model.user_id_map:
                            user_in_models = False
                            break
                
                if user_in_models:
                    self.user_data[user_id] = list(tracks)
                else:
                    users_filtered += 1
            
            print(f"\nСтатистика по пользователям:")
            print(f"  - Всего пользователей с треками: {len(user_tracks)}")
            print(f"  - Без признаков: {users_no_features}")
            print(f"  - Мало треков (<5): {users_insufficient_tracks}")
            print(f"  - Отсутствуют в моделях: {users_filtered}")
            print(f"  ✅ Готовы к тестированию: {len(self.user_data)}")
            
            if len(self.user_data) == 0:
                print("\n⚠️ ВНИМАНИЕ: Нет пользователей для тестирования!")
                print("Проверьте:")
                print("1. В базе есть данные в таблицах users, user_features, favorites/listening_history")
                print("2. Пользователи имеют заполненные психологические признаки (extraversion, openness)")
                print("3. Модели обучены с этими же пользователями")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки данных: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()
    
    def get_candidate_items(self, user_id: int, train_tracks: List[int], 
                           num_candidates: int = 1000) -> List[int]:
        """
        Получение кандидатов для рекомендаций.
        Исключаем треки, которые уже есть в тренировочных данных.
        """
        
        train_set = set(train_tracks)
        candidates = [t for t in self.all_tracks if t not in train_set]
        
        if len(candidates) > num_candidates:
            candidates = random.sample(candidates, num_candidates)
        
        return candidates
    
    def calculate_precision_at_k(self, recommendations: List[int], 
                                ground_truth: List[int], k: int = 20) -> float:
        """
        Вычисление Precision@k
        """
        if not recommendations or not ground_truth:
            return 0.0
        
        recommended_k = set(recommendations[:k])
        relevant = recommended_k & set(ground_truth)
        return len(relevant) / k
    
    def test_user_for_size(self, user_id: int, all_user_tracks: List[int], 
                          train_size: int) -> Dict[str, float]:
        """
        Тестирование одного пользователя для определенного количества тренировочных треков
        """
        results = {}
        
        if len(all_user_tracks) <= train_size:
            return {name: 0.0 for name in self.models.keys()}
        
        train_tracks = random.sample(all_user_tracks, train_size)
        
        test_tracks = [t for t in all_user_tracks if t not in train_tracks]
        
        if len(test_tracks) == 0:
            return {name: 0.0 for name in self.models.keys()}
        
        candidates = self.get_candidate_items(user_id, train_tracks)
        
        for model_name, model in self.models.items():
            try:
                if model_name == 'two_tower':
                    recommendations = model.recommend(user_id, candidates, top_n=20)
                elif model_name == 'personality_funksvd':
                    recommendations = model.recommend(user_id, candidates, top_n=20)
                elif model_name == 'fm':
                    recommendations = model.recommend(user_id, candidates, top_n=20)
                else:
                    continue
                
                precision = self.calculate_precision_at_k(
                    recommendations, test_tracks, k=20
                )
                results[model_name] = precision
                
            except Exception as e:
                print(f"  Ошибка для модели {model_name} (user={user_id}): {e}")
                results[model_name] = 0.0
        
        return results
    
    def run_test(self, min_train_size: int = 1, max_train_size: int = 40, 
                 step: int = 2, test_users_limit: int = None,
                 num_tests_per_size: int = 3):
        """
        Запуск тестирования для всех пользователей с разным количеством тренировочных треков
        
        Parameters:
        -----------
        min_train_size: минимальное количество треков для обучения
        max_train_size: максимальное количество треков для обучения
        step: шаг увеличения количества треков
        test_users_limit: ограничение на количество тестовых пользователей
        num_tests_per_size: количество тестов для каждого размера (для усреднения)
        """
        print("\n=== ЗАПУСК ТЕСТИРОВАНИЯ ===")
        print(f"Пользователей: {len(self.user_data)}")
        print(f"Диапазон треков: {min_train_size}-{max_train_size}, шаг {step}")
        print(f"Тестов на размер: {num_tests_per_size}")
        
        if len(self.user_data) == 0:
            print("❌ Нет пользователей для тестирования!")
            return None, None
        
        train_sizes = list(range(min_train_size, max_train_size + 1, step))
        results = {
            'personality_funksvd': [],
            'two_tower': [],
            'fm': []
        }
        
        users_list = list(self.user_data.keys())
        if test_users_limit:
            users_list = users_list[:test_users_limit]
            print(f"Ограничение на {test_users_limit} пользователей")
        
        for train_size in tqdm(train_sizes, desc="Тестирование размеров выборки"):
            all_precisions = defaultdict(list)
            
            for test_iter in range(num_tests_per_size):
                print(f"\n  Размер={train_size}, итерация {test_iter+1}/{num_tests_per_size}")
                
                for user_id in tqdm(users_list, desc=f"  Пользователи", leave=False):
                    user_tracks = self.user_data[user_id]
                    
                    if len(user_tracks) < train_size + 1:
                        continue
                    
                    user_results = self.test_user_for_size(
                        user_id, user_tracks, train_size
                    )
                    
                    for model_name, precision in user_results.items():
                        if precision > 0:  
                            all_precisions[model_name].append(precision)
            
            avg_precisions = {}
            for model_name in results.keys():
                if all_precisions[model_name]:
                    avg = np.mean(all_precisions[model_name])
                    std = np.std(all_precisions[model_name])
                    avg_precisions[model_name] = avg
                    results[model_name].append(avg)
                    print(f"  {model_name}: {avg:.4f} (±{std:.4f})")
                else:
                    avg_precisions[model_name] = 0
                    results[model_name].append(0)
                    print(f"  {model_name}: Нет данных")
        
        return train_sizes, results
    
    def plot_results(self, train_sizes: List[int], results: Dict[str, List[float]], 
                    save_path: str = 'models_comparison.png'):
        """
        Построение графика сравнения моделей
        """
        if not train_sizes or not any(results.values()):
            print("❌ Нет данных для построения графика!")
            return
        
        plt.figure(figsize=(12, 7))
        
        colors = {
            'personality_funksvd': '#2E86AB',
            'two_tower': '#A23B72',
            'fm': '#F18F01'
        }
        
        labels = {
            'personality_funksvd': 'Personality FunkSVD',
            'two_tower': 'Two-Tower Neural Network',
            'fm': 'Factorization Machine'
        }
        
        for model_name, precisions in results.items():
            if precisions and any(p > 0 for p in precisions):
                plt.plot(train_sizes, precisions, 
                        marker='o', linewidth=2, markersize=6,
                        color=colors.get(model_name, 'gray'), 
                        label=labels.get(model_name, model_name))
        
        plt.xlabel('Количество треков в обучении', fontsize=14)
        plt.ylabel('Precision@20', fontsize=14)
        plt.title('Сравнение моделей рекомендаций\nв зависимости от объема данных', 
                 fontsize=16, fontweight='bold')
        plt.legend(loc='best', fontsize=12)
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.ylim(0, 0.5)  
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
        print(f"\n✅ График сохранен в {save_path}")
    
    def save_results(self, train_sizes: List[int], results: Dict[str, List[float]], 
                    save_path: str = 'test_results.csv'):
        """
        Сохранение результатов в CSV файл
        """
        if not train_sizes:
            return
            
        df = pd.DataFrame({
            'train_size': train_sizes,
            'personality_funksvd_precision': results.get('personality_funksvd', []),
            'two_tower_precision': results.get('two_tower', []),
            'fm_precision': results.get('fm', [])
        })
        df.to_csv(save_path, index=False)
        print(f"✅ Результаты сохранены в {save_path}")
        
        print("\n=== СТАТИСТИКА РЕЗУЛЬТАТОВ ===")
        for model_name, precisions in results.items():
            if precisions and any(p > 0 for p in precisions):
                print(f"\n{model_name}:")
                print(f"  Средняя precision: {np.mean(precisions):.4f}")
                print(f"  Максимальная precision: {max(precisions):.4f}")
                if len(precisions) > 19:
                    print(f"  Precision при 20 треках: {precisions[19]:.4f}")

def main():
    """Основная функция для запуска тестирования"""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ МОДЕЛЕЙ РЕКОМЕНДАЦИЙ")
    print("=" * 70)
    
    tester = ModelPrecisionTester(models_path='.')
    
    if not tester.load_models():
        print("\n❌ Не удалось загрузить модели!")
        print("\nСначала запустите save_trained_models.py для обучения моделей:")
        print("  python save_trained_models.py")
        return
    
    if not tester.load_user_data():
        print("\n❌ Не удалось загрузить данные пользователей!")
        return
    
    train_sizes, results = tester.run_test(
        min_train_size=2,
        max_train_size=40,
        step=2,  
        test_users_limit=20,  
        num_tests_per_size=2  
    )
    
    if train_sizes and any(results.values()):
        
        tester.save_results(train_sizes, results)
        
        tester.plot_results(train_sizes, results)
    else:
        print("\n❌ Тестирование не дало результатов!")
    
    print("\n=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")

if __name__ == "__main__":
    main()