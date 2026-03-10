import jwt
import bcrypt
from flask import Blueprint, request, jsonify, current_app, redirect, url_for
from database import get_db_connection
from datetime import datetime, timedelta
from functools import wraps
from psycopg2.extras import RealDictCursor

auth_bp = Blueprint('auth', __name__)

# Декоратор для проверки JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Получаем токен из заголовка
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Ожидаем формат "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid token format"}), 401
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            # Декодируем токен
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token is invalid"}), 401
            
        return f(current_user_id, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # Проверка наличия всех полей
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Хешируем пароль
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (username, email, hashed.decode('utf-8'))
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "User created", "user_id": user_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Username or email already exists"}), 400
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        # Генерируем JWT
        token = jwt.encode(
            {
                'user_id': user['id'],
                'username': user['username'],
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return jsonify({"token": token, "user_id": user['id'], "username": user['username']})
    else:
        return jsonify({"error": "Invalid credentials"}), 401