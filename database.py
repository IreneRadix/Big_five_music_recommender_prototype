import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Создает подключение к базе данных PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="music_db",
            user="postgres",  # Замените на вашего пользователя
            password="560730"  # Замените на ваш пароль
        )
        return conn
    except psycopg2.Error as e:
        print(f"Ошибка подключения к базе данных: {e}")
        raise e

def init_db():
    """Инициализация базы данных (создание таблиц, если их нет)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Создание таблицы пользователей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создание таблицы треков
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                artist VARCHAR(100) NOT NULL,
                genre VARCHAR(50),
                file_url TEXT,
                cover_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создание таблицы избранного
        cur.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, track_id)
            )
        """)
        
        conn.commit()
        print("База данных успешно инициализирована")
        
    except psycopg2.Error as e:
        print(f"Ошибка при создании таблиц: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()