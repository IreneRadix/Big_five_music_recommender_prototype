from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from selenium.webdriver.common.by import By
import os
from database import get_db_connection
from lastfm_parser import get_genre
import time
import pickle
import time

# Настройка Chrome

options = Options()


# Антидетект опции
options.add_argument("--user-data-dir=C:\\selenium_profile")

# Добавляем аргументы для стабильности
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome(options = options)

def save_cookies(driver, filename="cookies.pkl"):
    with open(filename, "wb") as file:
        pickle.dump(driver.get_cookies(), file)


        
def load_cookies(driver, filename="cookies.pkl"):
    try:
        with open(filename, "rb") as file:
            cookies = pickle.load(file)
        return True
    except FileNotFoundError:
        print("Файл с cookies не найден")
        return False
    

def process_music(link, user_id):
    driver.get(link)

    # Находим все элементы с указанным классом
    elements = driver.find_elements(By.CSS_SELECTOR, ".audio_row__performer_title")
    
    conn = get_db_connection()
    cur = conn.cursor()
    #
    i=0    
    for element in elements:
       if i> 10:
           break
       title = element.find_element(By.CSS_SELECTOR, ".audio_row__title_inner").text
       authors = element.find_element(By.CSS_SELECTOR, ".audio_row__performers")
       authors = authors.find_element(By.CSS_SELECTOR, "a").text 
       print('a')
       genre = get_genre(title, authors)
       #i+=1
       print(title, authors, genre)
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
                    "INSERT INTO public.favorites(user_id, track_id) VALUES (%s, %s)",
                    (int(user_id), track_id)
            )
            track_id = cur.fetchone()[0]
            conn.commit() 
            print(title, authors, genre)
        except Exception as e:
                print(e)
                conn.rollback()
            
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


    time.sleep(60)
    save_cookies(driver)
    
    time.sleep(5)
    driver.get("https://vk.com/esselias") #https://vk.com/id31426
    

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
    user_liks['with_others'] = "https://vk.com/tag2366359" + vk_user_id

    process_music(user_liks['music'], vk_user_id)

    

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