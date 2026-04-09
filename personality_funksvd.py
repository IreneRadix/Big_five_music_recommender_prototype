import numpy as np
import pandas as pd
import pickle
from typing import Optional, Dict, List, Tuple
from base_recommender import BaseRecommender

class PersonalityFunkSVD(BaseRecommender):
    """
    FunkSVD with user bias parameterized by psychological traits.

    Prediction:
        r_ui = μ + b_u + b_i + p_u^T q_i

    where user bias is modelled as:
        b_u = β0 + βE * E_u + βO * O_u + ε_u

    E_u : extraversion score of user u
    O_u : openness score of user u
    ε_u : individual residual, learned from data.

    Parameters
    ----------
    n_factors : int
        Dimensionality of latent vectors (p_u, q_i).
    lr : float
        Learning rate for SGD.
    reg : float
        L2 regularization strength (applied to all parameters except global mean).
    n_epochs : int
        Number of passes over the training data.
    random_state : int, optional
        Seed for reproducibility.
    """

    def __init__(
        self,
        n_factors: int = 20,
        lr: float = 0.005,
        reg: float = 0.02,
        n_epochs: int = 20,
        random_state: Optional[int] = None,
    ):
        self.n_factors = n_factors
        self.lr = lr
        self.reg = reg
        self.n_epochs = n_epochs
        self.random_state = random_state

        self.global_mean_: float = 0.0
        self.beta_0_: float = 0.0
        self.beta_E_: float = 0.0
        self.beta_O_: float = 0.0
        self.item_biases_: Dict[int, float] = {}
        self.user_residuals_: Dict[int, float] = {}   
        self.user_vectors_: Dict[int, np.ndarray] = {}  
        self.item_vectors_: Dict[int, np.ndarray] = {}  
        self.user_features_: Optional[pd.DataFrame] = None
        self._user_ids_: set = set()
        self._item_ids_: set = set()

    def _init_params(self, interactions: pd.DataFrame, user_features: pd.DataFrame):
        """Initialize all model parameters before training."""
        if self.random_state is not None:
            np.random.seed(self.random_state)

        if 'track_id' in interactions.columns:
            interactions = interactions.rename(columns={'track_id': 'item_id'})
        
        self.global_mean_ = interactions['rating'].mean()

        self.user_features_ = user_features.copy()
        
        if 'extraversion' not in self.user_features_.columns:
            raise ValueError("user_features must contain 'extraversion' column")
        if 'openness' not in self.user_features_.columns:
            raise ValueError("user_features must contain 'openness' column")

        self.beta_0_ = 0.0
        self.beta_E_ = 0.0
        self.beta_O_ = 0.0

        users = interactions['user_id'].unique()
        items = interactions['item_id'].unique()
        self._user_ids_ = set(users)
        self._item_ids_ = set(items)

        self.item_biases_ = {item: 0.0 for item in items}

        self.user_residuals_ = {}
        self.user_vectors_ = {}
        for u in users:
            self.user_residuals_[u] = 0.0
            self.user_vectors_[u] = np.random.normal(0, 0.1, self.n_factors)

        self.item_vectors_ = {}
        for i in items:
            self.item_vectors_[i] = np.random.normal(0, 0.1, self.n_factors)

    def _get_user_bias(self, u: int) -> float:
        """Compute b_u = β0 + βE*E_u + βO*O_u + ε_u."""
        
        e_u = self.user_residuals_.get(u, 0.0)
        if u in self.user_features_.index:
            row = self.user_features_.loc[u]
            E_u, O_u = row['extraversion'], row['openness']
        else:
            
            E_u, O_u = 0.0, 0.0
        return self.beta_0_ + self.beta_E_ * E_u + self.beta_O_ * O_u + e_u

    def fit(self, interactions: pd.DataFrame, user_features: pd.DataFrame, item_features: pd.DataFrame = None):
        """
        Train the model.

        Parameters
        ----------
        interactions : pd.DataFrame
            Must contain columns ['user_id', 'item_id', 'rating'].
        user_features : pd.DataFrame
            Index = user_id, columns = ['extraversion', 'openness'].
        item_features : pd.DataFrame, optional
            Ignored by this model (kept for interface compatibility).
        """
        
        if 'track_id' in interactions.columns:
            interactions = interactions.rename(columns={'track_id': 'item_id'})
        
        self._init_params(interactions, user_features)

        for epoch in range(self.n_epochs):
            
            shuffled = interactions.sample(frac=1, random_state=self.random_state + epoch if self.random_state else None)
            
            for _, row in shuffled.iterrows():
                u = row['user_id']
                i = row['item_id']
                r_ui = row['rating']

                b_u = self._get_user_bias(u)
                b_i = self.item_biases_[i]
                p_u = self.user_vectors_[u]
                q_i = self.item_vectors_[i]
                pred = self.global_mean_ + b_u + b_i + np.dot(p_u, q_i)

                err = r_ui - pred

                self.global_mean_ += self.lr * err

                if u in self.user_features_.index:
                    E_u = self.user_features_.loc[u, 'extraversion']
                    O_u = self.user_features_.loc[u, 'openness']
                else:
                    E_u, O_u = 0.0, 0.0

                self.beta_0_ += self.lr * (err - self.reg * self.beta_0_)
                self.beta_E_ += self.lr * (err * E_u - self.reg * self.beta_E_)
                self.beta_O_ += self.lr * (err * O_u - self.reg * self.beta_O_)

                if u in self.user_residuals_:
                    eps_u = self.user_residuals_[u]
                    grad_eps = err - self.reg * eps_u
                    self.user_residuals_[u] += self.lr * grad_eps

                b_i_old = self.item_biases_[i]
                grad_bi = err - self.reg * b_i_old
                self.item_biases_[i] += self.lr * grad_bi

                if u in self.user_vectors_:
                    p_u_old = self.user_vectors_[u]
                    grad_pu = err * q_i - self.reg * p_u_old
                    self.user_vectors_[u] += self.lr * grad_pu

                q_i_old = self.item_vectors_[i]
                grad_qi = err * p_u - self.reg * q_i_old
                self.item_vectors_[i] += self.lr * grad_qi

    def predict(self, user_id: int, item_id: int) -> float:
        """Predict rating for a single user-item pair."""
        
        if user_id in self.user_vectors_:
            p_u = self.user_vectors_[user_id]
        else:
            p_u = np.zeros(self.n_factors)  

        b_u = self._get_user_bias(user_id)

        if item_id in self.item_vectors_:
            q_i = self.item_vectors_[item_id]
            b_i = self.item_biases_.get(item_id, 0.0)
        else:
            
            q_i = np.zeros(self.n_factors)
            b_i = 0.0

        return self.global_mean_ + b_u + b_i + np.dot(p_u, q_i)

    def recommend(self, user_id: int, candidate_items: List[int], top_n: int = 10) -> List[int]:
        """Return top-N recommended item_ids for a user from a list of candidates."""
        if not candidate_items:
            return []
        
        predictions = [(item, self.predict(user_id, item)) for item in candidate_items]
        predictions.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in predictions[:top_n]]

    def save(self, path: str):
        """Save model to file."""
        with open(path, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str):
        """Load model from file."""
        with open(path, 'rb') as f:
            return pickle.load(f)