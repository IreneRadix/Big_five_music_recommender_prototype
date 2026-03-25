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

# Создаем папку для логов, если её нет
log_dir = "C:\\temp\\selenium_logs"
os.makedirs(log_dir, exist_ok=True)

options = Options()

# Используем НОВУЮ папку
options.add_argument("--user-data-dir=C:\\selenium_profile")

# Добавляем аргументы для стабильности
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

# Включаем подробное логирование - ИСПРАВЛЕНО: создаем Service один раз с аргументами
service = Service(
    service_args=[
        "--verbose",
        f"--log-path={log_dir}\\chromedriver.log",
        "--append-log"
    ]
)

driver = webdriver.Chrome(service=service, options=options)


def process_music(link, user_id):
    driver.get(link)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.25)
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

    i = 0    
    for element in elements:
        title = element.find_element(By.CSS_SELECTOR, ".audio_row__title_inner").text
        authors = element.find_element(By.CSS_SELECTOR, ".audio_row__performers")
        authors = authors.find_element(By.CSS_SELECTOR, "a").text 
        print('a')
        genre = get_genre(title, authors, genre_driver)
        i += 1
        track_id = ''
        try:
            cur.execute(
                "INSERT INTO public.tracks(title, artist, genre) VALUES (%s, %s, %s) RETURNING id",
                (title, authors, genre)
            )
            track_id = cur.fetchone()[0]
            conn.commit() 
            print(title, authors, genre)
        except Exception as e:
            conn.rollback()
            print(e)
        if track_id:
            try:
                cur.execute(
                    "INSERT INTO public.favorites(user_id, track_id) VALUES (%s, %s) returning user_id",
                    (int(user_id), track_id)
                )
                # ИСПРАВЛЕНО: здесь должен быть user_id, а не track_id
                user_id_result = cur.fetchone()[0]
                conn.commit() 
                print(f"Добавлено в избранное: {title}, {authors}, {genre}")
            except Exception as e:
                print(e)
                conn.rollback()
            
    cur.close()
    conn.close()
    genre_driver.quit()  # Закрываем genre_driver


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
   
    time.sleep(3)
    driver.get("https://vk.com/esselias")  # https://vk.com/id31426

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

    if len(audio_links) > 1:
        user_liks['music'] = audio_links[1].get_attribute("href")
        vk_user_id = extract_user_id_from_vk_url(user_liks['music']) 
        user_liks['own_posts'] = "https://vk.com/wall" + vk_user_id + "?owner=1"
        user_liks['all_posts'] = "https://vk.com/wall" + vk_user_id
        user_liks['avatars'] = "https://vk.com/album" + vk_user_id + "_0"
        user_liks['with_others'] = "https://vk.com/tag2366359" + vk_user_id

        process_music(user_liks['music'], vk_user_id)
    else:
        print("Не найдено достаточно ссылок на аудио")

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
finally:
    # Закрываем драйвер в конце
    driver.quit()