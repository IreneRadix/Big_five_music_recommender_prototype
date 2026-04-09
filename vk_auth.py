import requests
from flask import Blueprint, request, redirect, jsonify, current_app, url_for
from flask import session
from database import get_db_connection
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
import sys

from vk_parser import parse_vk_data  

vk_bp = Blueprint('vk_auth', __name__)

VK_CLIENT_ID = 'your_client_id'
VK_CLIENT_SECRET = 'your_client_secret'
VK_REDIRECT_URI = 'http://localhost:5000/api/vk/callback'  

@vk_bp.route('/vk/login')
def vk_login():
    
    vk_auth_url = (
        f"https://oauth.vk.com/authorize?"
        f"client_id={VK_CLIENT_ID}&"
        f"redirect_uri={VK_REDIRECT_URI}&"
        f"response_type=code&"
        f"v=5.131&"
        f"scope=email"  
    )
    return redirect(vk_auth_url)

@vk_bp.route('/vk/callback')
def vk_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No code provided"}), 400

    token_url = "https://oauth.vk.com/access_token"
    params = {
        'client_id': VK_CLIENT_ID,
        'client_secret': VK_CLIENT_SECRET,
        'redirect_uri': VK_REDIRECT_URI,
        'code': code
    }
    response = requests.get(token_url, params=params)
    data = response.json()
    if 'access_token' not in data:
        return jsonify({"error": "Failed to get access token", "details": data}), 400

    access_token = data['access_token']
    user_vk_id = data['user_id']
    email = data.get('email', '')  

    user_info_url = "https://api.vk.com/method/users.get"
    params = {
        'user_ids': user_vk_id,
        'fields': 'sex,bdate,city,country,interests,music,activities',
        'access_token': access_token,
        'v': '5.131'
    }
    user_response = requests.get(user_info_url, params=params)
    user_data = user_response.json()
    if 'response' not in user_data:
        return jsonify({"error": "Failed to get user data", "details": user_data}), 400

    user_info = user_data['response'][0]

    try:
        parsed_data = parse_vk_data(user_info)  
    except Exception as e:
        
        print(f"Parser error: {e}")
        parsed_data = {}

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, username FROM users WHERE vk_id = %s", (user_vk_id,))
    existing = cur.fetchone()
    if existing:
        user_id = existing[0]
        
        cur.execute("UPDATE users SET email = %s WHERE id = %s", (email, user_id))
        conn.commit()
    else:
        
        username = user_info.get('first_name', 'user') + '_' + str(user_vk_id)
        
        import secrets
        random_password = secrets.token_urlsafe(16)
        hashed = bcrypt.hashpw(random_password.encode('utf-8'), bcrypt.gensalt())
        cur.execute(
            "INSERT INTO users (username, email, password_hash, vk_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (username, email, hashed.decode('utf-8'), user_vk_id)
        )
        user_id = cur.fetchone()[0]
        conn.commit()

    if parsed_data:
        
        cur.execute("""
            INSERT INTO user_personality (user_id, extraversion, conscientiousness, agreeableness, neuroticism, openness)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                extraversion = EXCLUDED.extraversion,
                conscientiousness = EXCLUDED.conscientiousness,
                agreeableness = EXCLUDED.agreeableness,
                neuroticism = EXCLUDED.neuroticism,
                openness = EXCLUDED.openness,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id,
            parsed_data.get('extraversion'),
            parsed_data.get('conscientiousness'),
            parsed_data.get('agreeableness'),
            parsed_data.get('neuroticism'),
            parsed_data.get('openness')
        ))
        conn.commit()

    cur.close()
    conn.close()

    token = jwt.encode(
        {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

    return redirect(f'http://localhost:5000/vk_callback.html?token={token}&user_id={user_id}')