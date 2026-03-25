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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
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
    if len(elements) < 200:
         return
    
    conn = get_db_connection()
    cur = conn.cursor()

    genre_chrome_options = Options()
    genre_chrome_options.add_argument("--headless")  # Без GUI
    genre_chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    genre_chrome_options.page_load_strategy = 'eager'
    #genre_driver = webdriver.Chrome(options=genre_chrome_options)

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




def get_vk_driver():
        # Создаем папку для логов, если её нет
    log_dir = "C:\\temp\\selenium_logs"
    os.makedirs(log_dir, exist_ok=True)

    options = Options()

    # !!! ВАЖНО: Используем НОВУЮ папку, а не ваш реальный профиль
    # Создайте эту папку вручную или раскомментируйте строку ниже
    options.add_argument("--user-data-dir=C:\\selenium_profile")

    # Добавляем аргументы для стабильности
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Включаем подробное логирование
    service = Service()
    service_args = [
        "--verbose",
        f"--log-path={log_dir}\\chromedriver.log",
        "--append-log"
    ]
    service = Service(service_args=service_args)
    #service=service,

    driver = webdriver.Chrome(options=options)
    return driver

def has_favs(user_id, conn, cur):
        query = """
            SELECT user_id, track_id, added_at 
            FROM favorites 
            WHERE user_id = %s
            LIMIT 1
        """
        
        # Выполняем запрос с параметром
        cur.execute(query, (int(user_id),))
        
        # Получаем все найденные записи
        results = cur.fetchone()
        return results

def get_friends(link, driver):
    driver.get(link)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break    
        last_height = new_height
    elements = driver.find_elements(By.CSS_SELECTOR, 'a.vkuiAvatar__host.vkuiImageBase__host.vkuiClickable__host')
    friends = [elem.get_attribute('href') for elem in elements if elem.get_attribute('href')]
    return friends

def extract_user_id_from_vk_url(url):
    if not url or not isinstance(url, str):
        return None

    # 1. Прямое извлечение ID из /audios722465521 или /id123456
    match_direct = re.search(r'/(?:audios|id|club|public)(\d+)', url)
    if match_direct:
        return match_direct.group(1)
    return None

def process_user(user_id, links, driver):
    if not has_favs(user_id, conn, cur):
        process_music(links['music'], user_id)

    user_liks['own_posts'] = "https://vk.com/wall" + vk_user_id + "?owner=1"
    user_liks['all_posts'] = "https://vk.com/wall" + vk_user_id
    user_liks['avatars'] = "https://vk.com/album" + vk_user_id + "_0"
    user_liks['with_others'] = "https://vk.com/tag" + vk_user_id

    try:
        pass # попытка получения личностных черт
    except Exception:
        pass

    


if __name__ == "__main__":
    conn = get_db_connection()
    cur = conn.cursor()
    driver = get_vk_driver()
    driver.get("https://vk.com")
    time.sleep(60)
    starts = [
    "https://vk.com/id383126333"
]
    #start =  'https://vk.com/tem4iklox' #  https://vk.com/griissviiss https://vk.com/annapharaoh  https://vk.com/muradov86"https://vk.com/sitalaputa2006"  https://vk.com/abor2   https://vk.com/onidzuka27
    for start in starts: 
        visited = set()
        stack = [(start, 0)]  # (узел, глубина)
        max_depth = 6
        try:
            while stack:
                user, depth = stack.pop()
                
                if depth <= max_depth and not user in visited:
                    visited.add(user)
                    try:
                        time.sleep(1)
                        driver.get(user) 
                        user_liks = {}
                        # Ищем все ссылки на аудио
                        audio_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/audios')]")
                        user_liks['music'] = audio_links[1].get_attribute("href")
                        vk_user_id = extract_user_id_from_vk_url(user_liks['music']) 
                        user_liks['friends'] =  "https://vk.com/friends?id=" + vk_user_id + "&section=all"
                        print('get friends')
                        friends = get_friends(user_liks['friends'], driver)
                        print(friends)

                    except Exception as e:
                        print(e)
                        continue      
                    process_user(vk_user_id, user_liks, driver)          
                    # Добавляем соседей в стек с увеличенной глубиной
                    for neighbor in friends:
                        if neighbor not in visited:
                            stack.append((neighbor, depth + 1))

        

             


        #profiler = cProfile.Profile()
        #profiler.enable()
        #process_music(user_liks['music'], vk_user_id)
        #profiler.disable()
        #s = StringIO()
        #ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        #ps.print_stats(30)  # Покажет топ-30 самых медленных функций
        #print(s.getvalue())


        except BaseException as e:
            print(e)