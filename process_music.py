from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from selenium.webdriver.common.by import By
import os
from database import get_db_connection
from lastfm_parser import get_genre
import time
import pickle
import time
from psycopg2.extras import execute_values

import cProfile
import pstats
from io import StringIO

def batch_insert(conn, cur, batch, user_id):     
            try:

                track_values = [(artist, title, genre) for artist, title, genre, _ in batch]
                execute_values(cur, """
                    INSERT INTO tracks (artist, title, genre) 
                    VALUES %s 
                    ON CONFLICT (artist, title) DO NOTHING
                """, track_values)
                
                # Получаем ID всех треков
                cur.execute("""
                    SELECT id FROM tracks 
                    WHERE (artist, title) IN %s
                """, (tuple((a, t) for a, t, _, _ in batch),))
                
                track_ids = [row[0] for row in cur.fetchall()]
                
                # Вставляем в favorites
                favorite_values = [(user_id, track_id) for track_id in track_ids]
                execute_values(cur, """
                    INSERT INTO favorites (user_id, track_id) 
                    VALUES %s 
                    ON CONFLICT DO NOTHING
                """, favorite_values)
                
                conn.commit()
                batch = []
                print(f"Успешно добавлено {len(track_ids)} треков")
            except Exception as e:
                    print(e)
            finally:
                    conn.commit()
                    batch = []
    


def process_music(link, user_id):
    driver.get(link)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break    
        last_height = new_height

    # Находим все элементы с указанным классом
    elements = driver.find_elements(By.CSS_SELECTOR, ".audio_row__performer_title")
    
    conn = get_db_connection()
    cur = conn.cursor()

    genre_chrome_options = Options()
    genre_chrome_options.add_argument("--headless")  # Без GUI
    genre_chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    genre_chrome_options.page_load_strategy = 'eager'
    genre_driver = webdriver.Chrome(options=genre_chrome_options)

    #
    i=0    
    batch = []

    for element in elements:
        
       title = element.find_element(By.CSS_SELECTOR, ".audio_row__title_inner").text
       authors = element.find_element(By.CSS_SELECTOR, ".audio_row__performers")
       authors = authors.find_element(By.CSS_SELECTOR, "a").text 
       #print('a')
       genre = "" #get_genre(title, authors, genre_driver)
       i+=1
       batch.append((authors, title[:50], genre, user_id))
       if i % 250 == 0:
            batch_insert(conn, cur, batch, user_id)
            batch = []
        


    batch_insert(conn, cur, batch, user_id)       
    cur.close()
    conn.close()



def extract_user_id_from_vk_url(url):
    if not url or not isinstance(url, str):
        return None

    # 1. Прямое извлечение ID из /audios722465521 или /id123456
    match_direct = re.search(r'/(?:audios|id|club|public)(\d+)', url)
    if match_direct:
        return match_direct.group(1)
    return None