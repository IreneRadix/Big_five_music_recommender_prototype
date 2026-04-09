import numpy as np
import pandas as pd
from database import get_db_connection
import pickle

def predict_extraversion(row):
    
    row_df = pd.DataFrame([row.values], columns=row.index)
    return round(extraversion_model.predict(row_df)[0])

def predict_openness(row):
    
    features = ['friends', 'pictures']
    row_df = pd.DataFrame([row[features].values], columns=features)
    return round(openness_model.predict(row_df)[0])

df = pd.read_csv('user_features_df', index_col=0) 
df.fillna(0, inplace=True)

with open(r"ml_models/extraversion_model_3featurea.pkl", 'rb') as file:  
    extraversion_model = pickle.load(file)

with open(r"ml_models/openness_model_2features.pkl", 'rb') as file:  
    openness_model = pickle.load(file)

conn = get_db_connection()
cur = conn.cursor() 

for index, row in df.iterrows():
    
    if 'user_id' in df.columns:
        user_id = row['user_id']
        row_features = row.drop('user_id')
    else:
        user_id = index
        row_features = row
    
    try:
        e_pred = predict_extraversion(row_features)
        o_pred = predict_openness(row_features)
        print(f"Index: {user_id}, E: {e_pred:.4f}, O: {o_pred:.4f}")
        try:
            cur.execute(
                "INSERT INTO user_features (user_id, extraversion, openness) VALUES (%s, %s, %s) ",
                (int(user_id), int(e_pred), int(o_pred))
            )
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(e)
    except Exception as e:
        print(f"Ошибка при обработке {user_id}: {e}")