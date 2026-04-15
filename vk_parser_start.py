from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from selenium.webdriver.common.by import By
import os
from database import get_db_connection
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from psycopg2.extras import execute_values

from vk_parser import (
    get_vk_driver,
    get_friends,
    extract_user_id_from_vk_url,
    parse_vk_data,
    scroll_to_bottom,
    extract_image_urls,
    get_imgs,
    process_imgs_parallel,
    get_liker_urls_for_one
)
from single_user_traits_predictor import get_user_traits

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
        
        cur.execute("""
            SELECT id FROM tracks 
            WHERE (artist, title) IN %s
        """, (tuple((a, t) for a, t, _, _ in batch),))
        
        track_ids = [row[0] for row in cur.fetchall()]
        
        favorite_values = [(user_id, track_id) for track_id in track_ids]
        execute_values(cur, """
            INSERT INTO favorites (user_id, track_id) 
            VALUES %s 
            ON CONFLICT DO NOTHING
        """, favorite_values)
        
        conn.commit()
        print(f"Успешно добавлено {len(track_ids)} треков")
    except Exception as e:
        print(e)
        conn.rollback()
    finally:
        batch.clear()

def process_music(link, user_id, driver):
    """Обрабатывает музыку пользователя"""
    driver.get(link)
    scroll_to_bottom(driver, delay=1)
    
    elements = driver.find_elements(By.CSS_SELECTOR, ".audio_row__performer_title")
    if len(elements) < 200:
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    i = 0    
    batch = []
    
    for element in elements:
        title = element.find_element(By.CSS_SELECTOR, ".audio_row__title_inner").text
        authors = element.find_element(By.CSS_SELECTOR, ".audio_row__performers")
        authors = authors.find_element(By.CSS_SELECTOR, "a").text 
        
        i += 1
        batch.append((authors, title[:50], "", user_id))  # genre пока пустой
        
        if i % 250 == 0:
            batch_insert(conn, cur, batch, user_id)
            batch = []
    
    if batch:
        batch_insert(conn, cur, batch, user_id)
    
    cur.close()
    conn.close()

def has_favs(user_id, conn, cur):
    """Проверяет, есть ли у пользователя избранные треки"""
    query = """
        SELECT user_id, track_id, added_at 
        FROM favorites 
        WHERE user_id = %s
        LIMIT 1
    """
    cur.execute(query, (int(user_id),))
    return cur.fetchone() is not None

def process_user(user_id, links, driver):
    """Обрабатывает данные пользователя"""
    # Проверяем, есть ли уже музыка пользователя в БД
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if not has_favs(user_id, conn, cur):
            if 'music' in links and links['music']:
                process_music(links['music'], user_id, driver)
    finally:
        cur.close()
        conn.close()
    
    # Получаем дополнительные данные через parse_vk_data (если нужно)
    try:
        user_data = parse_vk_data(links.get('profile_url', f"https://vk.com/id{user_id}"), 
                                  driver=driver, 
                                  should_close_driver=False)
        
        # Сохраняем данные в БД (если есть таблица для user_features)
        # Здесь можно добавить сохранение user_data в БД
        print(f"User {user_id}: {user_data}")
        
    except Exception as e:
        print(f"Ошибка при получении данных пользователя {user_id}: {e}")

def get_user_links(driver, user_url):
    """Получает все ссылки пользователя"""
    driver.get(user_url)
    time.sleep(2)
    
    user_links = {}
    
    try:
        # Ищем ссылки на аудио
        audio_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/audios')]")
        if len(audio_links) >= 2:
            user_links['music'] = audio_links[1].get_attribute("href")
            vk_user_id = extract_user_id_from_vk_url(user_links['music'])
        else:
            vk_user_id = extract_user_id_from_vk_url(user_url)
            user_links['music'] = f"https://vk.com/audios{vk_user_id}"
        
        user_links['profile_url'] = user_url
        user_links['friends'] = f"https://vk.com/friends?id={vk_user_id}&section=all"
        user_links['own_posts'] = f"https://vk.com/wall{vk_user_id}?owner=1"
        user_links['all_posts'] = f"https://vk.com/wall{vk_user_id}"
        user_links['avatars'] = f"https://vk.com/album{vk_user_id}_0"
        user_links['with_others'] = f"https://vk.com/tag{vk_user_id}"
        
        return user_links, vk_user_id
        
    except Exception as e:
        print(f"Ошибка при получении ссылок пользователя: {e}")
        return None, None

def crawl_users(start_urls, max_depth=6, max_users=None):
    """
    Обходит пользователей VK в глубину
    
    Args:
        start_urls: список начальных URL
        max_depth: максимальная глубина обхода
        max_users: максимальное количество пользователей для обработки
    """
    conn = get_db_connection()
    cur = conn.cursor()
    driver = get_vk_driver()
    
    try:
        
        driver.get("https://vk.com")
        print("Пожалуйста, войдите в VK в открывшемся окне браузера...")
        time.sleep(60)  
        
        visited = set()
        processed_users = set()
        stack = []
        
        for start_url in start_urls:
            stack.append((start_url, 0))
        
        while stack and (max_users is None or len(processed_users) < max_users):
            user_url, depth = stack.pop()
            
            if user_url in visited or depth > max_depth:
                continue
                
            visited.add(user_url)
            
            try:
                time.sleep(1)  
                
                user_links, vk_user_id = get_user_links(driver, user_url)
                
                if not vk_user_id:
                    print(f"Не удалось получить ID для {user_url}")
                    continue
                
                if vk_user_id in processed_users:
                    continue
                
                processed_users.add(vk_user_id)
                print(f"\nОбработка пользователя {vk_user_id} (глубина {depth})")
                
                if user_links and 'friends' in user_links:
                    friends, total_friends = get_friends(driver, user_links['friends'])
                    print(f"Найдено друзей: {len(friends)}/{total_friends if total_friends else '?'}")
                else:
                    friends = []
                
                process_user(vk_user_id, user_links, driver)
                
                for friend_url in friends:
                    if friend_url not in visited:
                        stack.append((friend_url, depth + 1))
                        
            except Exception as e:
                print(f"Ошибка при обработке {user_url}: {e}")
                continue
                
    finally:
        cur.close()
        conn.close()
        driver.quit()
    
    print(f"\nОбработано пользователей: {len(processed_users)}")
    return processed_users

if __name__ == "__main__":
    
    starts = [
        "https://vk.com/id383126333"
    ]
    
    crawl_users(starts, max_depth=7, max_users=None)
    