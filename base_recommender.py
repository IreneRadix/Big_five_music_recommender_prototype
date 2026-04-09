from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict, Any

class BaseRecommender(ABC):
    """Абстрактный интерфейс для всех рекомендательных моделей."""

    @abstractmethod
    def fit(self, interactions: pd.DataFrame, user_features: pd.DataFrame, item_features: pd.DataFrame):
        """
        Обучить модель.
        interactions: колонки ['user_id', 'item_id', 'rating'] (rating = 1 для лайка)
        user_features: индекс = user_id, колонки с признаками
        item_features: индекс = item_id, колонки с признаками
        """
        pass

    @abstractmethod
    def predict(self, user_id: int, item_id: int) -> float:
        """Предсказать рейтинг (score) для пары пользователь-трек."""
        pass

    @abstractmethod
    def recommend(self, user_id: int, candidate_items: List[int], top_n: int = 10) -> List[int]:
        """Вернуть топ-N item_id из списка кандидатов."""
        pass

    @abstractmethod
    def save(self, path: str):
        """Сохранить модель в файл."""
        pass

    @classmethod
    @abstractmethod
    def load(cls, path: str):
        """Загрузить модель из файла."""
        pass