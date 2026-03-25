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

driver = webdriver.Chrome(service=service, options=options)


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

try:
    # Сначала нужно открыть сайт (обязательно тот же домен)
    driver.get("https://vk.com")
   
    #
    time.sleep(1)
    driver.get("https://vk.com/offscreenviolence") # https://vk.com/lexavolod https://vk.com/id31426 https://vk.com/little.ricky https://vk.com/marauderofrock
    #https://vk.com/balbe5ich https://vk.com/fpspersecond https://vk.com/amakeeva83 https://vk.com/id269487052 https://vk.com/alexandrfucking.slaves
    # https://vk.com/the_capitan_brake https://vk.com/id171754634 https://vk.com/id171754634 https://vk.com/id269487052
    # https://vk.com/id269487052  https://vk.com/justonefeather https://vk.com/heathen99  https://vk.com/bel19 https://vk.com/m9578r
    #  https://vk.com/loltishotutzabil  https://vk.com/mmaloyy https://vk.com/obormotus https://vk.com/id230388129 https://vk.com/idi_na_xui69
    #  https://vk.com/barenad   https://vk.com/worik.java https://vk.com/tem4iklox https://vk.com/aleksandr_inco  https://vk.com/arina.sadovnikova
    # https://vk.com/anxiietysm  https://vk.com/aleksandr_inco https://vk.com/annapharaoh  https://vk.com/muradov86 
    #  https://vk.com/abor2  https://vk.com/onidzuka27
    buttons = driver.find_elements(By.CSS_SELECTOR, "a[class*='vkitButton']")

    user_liks = {}
    
    print("Найденные кнопки с классом vkitButton:")
    for btn in buttons:
        href = btn.get_attribute("href")
        text = btn.text
        if href:
            print(f"{text}: {href}")
    
    # Ищем все ссылки на аудио
    audio_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/audios')]")
    
    print("\nСсылки на аудио:")
    for link in audio_links:
        href = link.get_attribute("href")
        text = link.text
        print(f"{text}: {href}")

    user_liks['music'] = audio_links[1].get_attribute("href")
    vk_user_id = extract_user_id_from_vk_url(user_liks['music']) 
    user_liks['own_posts'] = "https://vk.com/wall" + vk_user_id + "?owner=1"
    user_liks['all_posts'] = "https://vk.com/wall" + vk_user_id
    user_liks['avatars'] = "https://vk.com/album" + vk_user_id + "_0"
    user_liks['with_others'] = "https://vk.com/tag" + vk_user_id

    profiler = cProfile.Profile()
    profiler.enable()
    process_music(user_liks['music'], vk_user_id)
    profiler.disable()
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(30)  # Покажет топ-30 самых медленных функций
    print(s.getvalue())

    

    try:
        # Используем CSS селектор с классами
        friends_link = driver.find_element(By.CSS_SELECTOR, 
            'a.vkitHeader__tappable--BX9pT.ProfileGroupHeader.vkuiInternalTappable')
        print(f"Друзья (по классам): {friends_link.get_attribute('href')}")
        user_liks['friends'] = friends_link.get_attribute("href")
    except NoSuchElementException:
        print("Ссылка на друзей по классам не найдена")
    
    print(user_liks)

except BaseException as e:
    print(e)