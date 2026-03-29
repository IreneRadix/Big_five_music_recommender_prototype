import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from database import get_db_connection
from tqdm import tqdm  # для отображения прогресса

def compare_users_psychometric(target_user_id, df, metric='euclidean'):
    """
    Сравнение пользователей по психометрическим характеристикам
    """
    df_indexed = df.set_index('user_id')
    
    if target_user_id not in df_indexed.index:
        return pd.DataFrame()  # возвращаем пустой DataFrame, если пользователь не найден
    
    target = df_indexed.loc[target_user_id]
    others = df_indexed[df_indexed.index != target_user_id]
    
    results = []
    
    for user_id, user_data in others.iterrows():
        if metric == 'cosine':
            # Косинусное сходство
            similarity = np.dot(target, user_data) / (np.linalg.norm(target) * np.linalg.norm(user_data))
            
        elif metric == 'euclidean':
            # Евклидово расстояние (чем меньше, тем ближе)
            similarity = -np.linalg.norm(target - user_data)  # отрицательное для ранжирования
            
        elif metric == 'manhattan':
            # Манхэттенское расстояние
            similarity = -np.sum(np.abs(target - user_data))
            
        elif metric == 'pearson':
            # Корреляция Пирсона
            similarity = np.corrcoef(target, user_data)[0, 1]
            
        elif metric == 'dot':
            # Скалярное произведение
            similarity = np.dot(target, user_data)
            
        results.append({
            'user_id': user_id,
            'similarity': similarity,
            'extraversion_diff': target['extraversion'] - user_data['extraversion'],
            'openness_diff': target['openness'] - user_data['openness']
        })
    
    result_df = pd.DataFrame(results)
    
    if metric in ['euclidean', 'manhattan']:
        # Для расстояний сортируем по возрастанию (меньше расстояние = ближе)
        result_df = result_df.sort_values('similarity', ascending=False)
    else:
        # Для сходства сортируем по убыванию
        result_df = result_df.sort_values('similarity', ascending=False)
    
    return result_df


def get_popular_tracks_among_users(user_ids, favorites_df, top_n=20):
    """
    Получение самых популярных треков среди списка пользователей
    
    Parameters:
    -----------
    user_ids : list
        Список ID пользователей
    favorites_df : DataFrame
        DataFrame с избранными треками пользователей
    top_n : int
        Количество самых популярных треков для возврата
    
    Returns:
    --------
    set : набор ID самых популярных треков
    """
    if len(user_ids) == 0:
        return set()
    
    # Фильтруем треки только для указанных пользователей
    filtered_tracks = favorites_df[favorites_df['user_id'].isin(user_ids)]
    
    # Подсчитываем количество пользователей для каждого трека
    track_popularity = filtered_tracks.groupby('track_id')['user_id'].nunique().reset_index()
    track_popularity.columns = ['track_id', 'user_count']
    
    # Сортируем по убыванию популярности и берем топ-N
    top_tracks = track_popularity.sort_values('user_count', ascending=False).head(top_n)
    
    return set(top_tracks['track_id'].tolist())


def count_user_tracks_in_popular_set(user_id, popular_tracks_set, favorites_df):
    """
    Подсчет количества треков пользователя, которые входят в набор популярных треков
    
    Parameters:
    -----------
    user_id : int
        ID пользователя
    popular_tracks_set : set
        Набор популярных треков
    favorites_df : DataFrame
        DataFrame с избранными треками пользователей
    
    Returns:
    --------
    int : количество треков пользователя, входящих в популярный набор
    """
    # Получаем треки пользователя
    user_tracks = set(favorites_df[favorites_df['user_id'] == user_id]['track_id'])
    
    # Подсчитываем пересечение
    common_tracks = user_tracks & popular_tracks_set
    
    return len(common_tracks)


# Подключение к базе данных
print("Загрузка данных из базы...")
conn = get_db_connection()
query = "SELECT user_id, extraversion, openness FROM user_features"
df_features = pd.read_sql(query, conn)

query_favorites = "SELECT user_id, track_id FROM favorites"
df_favorites = pd.read_sql(query_favorites, conn)

# Закрытие соединения
conn.close()

print(f"Загружено {len(df_features)} пользователей с психометрическими данными")
print(f"Загружено {len(df_favorites)} записей избранных треков")

# Получаем список всех пользователей, у которых есть психометрические данные
all_users = df_features['user_id'].unique()
print(f"Всего пользователей для анализа: {len(all_users)}")

# Словарь для хранения результатов
results = []

# Проходим по каждому пользователю
print("\nНачинаем анализ для каждого пользователя...")
for target_user in tqdm(all_users, desc="Обработка пользователей"):
    # Находим пользователей с similarity = 0 для текущего целевого пользователя
    similar_users_df = compare_users_psychometric(target_user, df_features)
    
    if similar_users_df.empty:
        # Если пользователь не найден или нет других пользователей
        results.append({
            'user_id': target_user,
            'similarity_zero_count': 0,
            'tracks_in_top20': 0,
            'top20_tracks_count': 0
        })
        continue
    
    # Получаем пользователей с similarity = 0
    zero_similarity_users = similar_users_df[similar_users_df['similarity'] < 5]['user_id'].tolist()
    
    if len(zero_similarity_users) == 0:
        # Нет пользователей с similarity = 0
        results.append({
            'user_id': target_user,
            'similarity_zero_count': 0,
            'tracks_in_top20': 0,
            'top20_tracks_count': 0
        })
        continue
    
    # Строим топ-20 самых популярных треков среди пользователей с similarity = 0
    popular_tracks_set = get_popular_tracks_among_users(
        user_ids=zero_similarity_users,
        favorites_df=df_favorites,
        top_n=20
    )
    
    # Считаем, сколько из этих треков есть у текущего целевого пользователя
    tracks_count = count_user_tracks_in_popular_set(
        user_id=target_user,
        popular_tracks_set=popular_tracks_set,
        favorites_df=df_favorites
    )
    
    # Сохраняем результаты
    results.append({
        'user_id': target_user,
        'similarity_zero_count': len(zero_similarity_users),
        'tracks_in_top20': tracks_count,
        'top20_tracks_count': len(popular_tracks_set)
    })

# Создаем DataFrame с результатами
results_df = pd.DataFrame(results)

# Выводим итоговую статистику
print("\n" + "="*80)
print("ИТОГОВЫЙ АНАЛИЗ")
print("="*80)

print(f"\nВсего обработано пользователей: {len(results_df)}")
print(f"Пользователей с хотя бы одним similarity=0: {(results_df['similarity_zero_count'] > 0).sum()}")
print(f"Пользователей без similarity=0: {(results_df['similarity_zero_count'] == 0).sum()}")

# Фильтруем только тех пользователей, у которых есть similarity=0
users_with_similarity_zero = results_df[results_df['similarity_zero_count'] > 0]

if len(users_with_similarity_zero) > 0:
    print(f"\nСтатистика по количеству пользователей с similarity=0:")
    print(f"  Среднее: {users_with_similarity_zero['similarity_zero_count'].mean():.2f}")
    print(f"  Медиана: {users_with_similarity_zero['similarity_zero_count'].median():.2f}")
    print(f"  Минимум: {users_with_similarity_zero['similarity_zero_count'].min()}")
    print(f"  Максимум: {users_with_similarity_zero['similarity_zero_count'].max()}")
    
    print(f"\nСтатистика по количеству треков из топ-20, которые есть у пользователя:")
    print(f"  Среднее: {users_with_similarity_zero['tracks_in_top20'].mean():.2f}")
    print(f"  Медиана: {users_with_similarity_zero['tracks_in_top20'].median():.2f}")
    print(f"  Минимум: {users_with_similarity_zero['tracks_in_top20'].min()}")
    print(f"  Максимум: {users_with_similarity_zero['tracks_in_top20'].max()}")
    print(f"  Стандартное отклонение: {users_with_similarity_zero['tracks_in_top20'].std():.2f}")
    
    # Выводим распределение
    print(f"\nРаспределение количества треков из топ-20:")
    distribution = users_with_similarity_zero['tracks_in_top20'].value_counts().sort_index()
    for count, num_users in distribution.items():
        percentage = (num_users / len(users_with_similarity_zero)) * 100
        print(f"  {count:2d} треков: {num_users:5d} пользователей ({percentage:5.2f}%)")
    
    # Топ-10 пользователей с наибольшим количеством треков из топ-20
    print(f"\nТоп-10 пользователей с наибольшим количеством треков из топ-20:")
    print("-" * 60)
    top_users = users_with_similarity_zero.nlargest(10, 'tracks_in_top20')
    for idx, row in top_users.iterrows():
        print(f"  User ID: {row['user_id']:12d} | Треков в топ-20: {row['tracks_in_top20']:2d} | Всего similarity=0: {row['similarity_zero_count']:4d}")
    
    # Топ-10 пользователей с наименьшим количеством треков из топ-20
    print(f"\nТоп-10 пользователей с наименьшим количеством треков из топ-20:")
    print("-" * 60)
    bottom_users = users_with_similarity_zero.nsmallest(10, 'tracks_in_top20')
    for idx, row in bottom_users.iterrows():
        print(f"  User ID: {row['user_id']:12d} | Треков в топ-20: {row['tracks_in_top20']:2d} | Всего similarity=0: {row['similarity_zero_count']:4d}")
    
    # Дополнительная статистика: сколько пользователей имеют 0 треков из топ-20
    zero_tracks_users = users_with_similarity_zero[users_with_similarity_zero['tracks_in_top20'] == 0]
    print(f"\nПользователей с 0 треков из топ-20: {len(zero_tracks_users)} ({len(zero_tracks_users)/len(users_with_similarity_zero)*100:.2f}%)")
    
    # Анализ корреляции между количеством similarity=0 и количеством треков
    if len(users_with_similarity_zero) > 1:
        correlation = users_with_similarity_zero['similarity_zero_count'].corr(users_with_similarity_zero['tracks_in_top20'])
        print(f"\nКорреляция между количеством similarity=0 и количеством треков из топ-20: {correlation:.3f}")
    
else:
    print("\nНет пользователей с similarity=0 ни для одного пользователя")

# Сохраняем результаты в CSV файл
output_file = 'user_tracks_in_popular_analysis.csv'
results_df.to_csv(output_file, index=False)
print(f"\nРезультаты сохранены в файл: {output_file}")

# Выводим дополнительную информацию для проверки
print("\n" + "="*80)
print("ПРИМЕР РАСЧЕТА ДЛЯ ПЕРВЫХ 5 ПОЛЬЗОВАТЕЛЕЙ")
print("="*80)
for idx, row in results_df.head(5).iterrows():
    print(f"\nПользователь {row['user_id']}:")
    print(f"  Количество пользователей с similarity=0: {row['similarity_zero_count']}")
    print(f"  Количество треков из топ-20: {row['tracks_in_top20']}")