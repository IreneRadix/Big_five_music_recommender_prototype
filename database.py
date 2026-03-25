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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_features (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                
                -- Демографические данные
                gender VARCHAR(6),              -- пол (male, female)
                age INTEGER,  -- возраст (ограничение от 13 до 120)
                location VARCHAR(100),            -- местоположение (город/страна)
                
                -- Big Five личностные характеристики (шкала от 1 до 10)
                -- Экстраверсия (общительность, энергичность)
                extraversion INTEGER,
                
                -- Добросовестность/Организованность (самодисциплина, организованность)
                conscientiousness  INTEGER,
                
                -- Доброжелательность/Дружелюбие (доверие, альтруизм)
                agreeableness  INTEGER,
                
                -- Нейротизм (эмоциональная нестабильность, тревожность)
                neuroticism  INTEGER,
                
                -- Открытость новому опыту (любопытство, креативность)
                openness  INTEGER,
                
                
                -- Проверка, что хотя бы одно поле заполнено (необязательно)
                CONSTRAINT has_data CHECK (
                    gender IS NOT NULL OR 
                    age IS NOT NULL OR 
                    extraversion IS NOT NULL OR 
                    conscientiousness IS NOT NULL OR 
                    agreeableness IS NOT NULL OR 
                    neuroticism IS NOT NULL OR 
                    openness IS NOT NULL
                )
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