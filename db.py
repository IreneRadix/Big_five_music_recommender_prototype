from database import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
print(int('54543'))