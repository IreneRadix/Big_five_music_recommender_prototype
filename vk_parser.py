from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from single_user_traits_predictor import get_user_traits
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import logging
from typing import List, Tuple, Dict, Any, Optional
import multiprocessing as mp
from deepface import DeepFace
import os
import pandas as pd
from pathlib import Path
from collections import defaultdict
import numpy as np
from sklearn.cluster import DBSCAN
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tqdm import tqdm
import pickle
from selenium.webdriver.common.by import By
import os
from database import get_db_connection
import re
from collections import defaultdict
import time
import io
import time
from PIL import Image
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values
import requests
import cProfile
import pstats
from io import StringIO
from flask import jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scroll_to_bottom(driver, delay=3):
    """Прокрутка страницы до конца"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def extract_image_urls(driver, timeout=60):
    """
    Извлекает ВСЕ фото с учетом виртуального скроллинга
    """
    wait = WebDriverWait(driver, 20)
    
    # Получаем общее количество фото
    try:
        count_xpath = "//div[contains(@class, 'vkitBreadcrumb__indicator')]//h4"
        count_element = wait.until(EC.presence_of_element_located((By.XPATH, count_xpath)))
        total_photos = int(count_element.text)
        print(f"Всего фото в альбоме: {total_photos}")
    except:
        total_photos = None
        print("Не удалось получить количество фото")
    
    # Собираем URL фото в set для уникальности
    all_src_urls = set()
    all_post_urls = set()
    
    last_count = 0
    same_count_attempts = 0
    scroll_attempts = 0
    max_scroll_attempts = 30
    
    # Получаем контейнер для прокрутки
    try:
        scroll_container = driver.find_element(By.CSS_SELECTOR, ".PhotosPageGrid__virtualRoot--8R5Be")
    except:
        scroll_container = None
    
    while scroll_attempts < max_scroll_attempts:
        # Получаем текущие видимые фото
        photos = driver.find_elements(By.CSS_SELECTOR, 
            ".PhotosPagePhotoGridVirtualItem__root--jeBPH")
        
        # Добавляем URL всех видимых фото
        for photo in photos:
            try:
                img = photo.find_element(By.CSS_SELECTOR, 
                    ".PhotosPagePhotoGridVirtualItem__img--r0XHW")
                src = img.get_attribute("src")
                post_url = photo.get_attribute("href")
                
                if src:
                    all_src_urls.add(src)
                if post_url:
                    all_post_urls.add(post_url)
            except:
                continue
        
        current_count = len(all_src_urls)
        print(f"Собрано уникальных фото: {current_count}/{total_photos if total_photos else '?'}")
        
        # Проверяем, собрали ли все
        if total_photos and current_count >= total_photos:
            print("Все фото собраны!")
            break
        
        # Проверяем, не застряли ли мы
        if current_count == last_count:
            same_count_attempts += 1
            if same_count_attempts >= 5:
                # Пробуем прокрутить в разные стороны
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                same_count_attempts = 0
        else:
            same_count_attempts = 0
            last_count = current_count
        
        # Прокручиваем контейнер
        if scroll_container:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
        time.sleep(2)
        
        # Дополнительная прокрутка всей страницы
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        scroll_attempts += 1
    
    print(f"Итого собрано фото: {len(all_src_urls)}")
    return list(all_src_urls)[:150], list(all_post_urls)[:150]


def get_imgs(urls):
    photos = []
    for url in urls:
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                photos.append(response.content)
        except Exception as e:
            print(f"Failed {url}: {e}")
    return photos


def extract_after_photo(url):
    """Извлекает ID фото из URL"""
    if "photo" in url:
        photo_index = url.find("photo")
        return url[photo_index + len("photo"):]
    else:
        return None


def process_single_photo(photo: bytes) -> Optional[List[Dict]]:
    try:
        img = Image.open(io.BytesIO(photo))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        max_size = 800
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.LANCZOS)
        
        embeddings = DeepFace.represent(
            img_path=np.array(img),
            model_name="Facenet512",
            detector_backend="retinaface",
            enforce_detection=False,
            align=True
        )
        
        result = []
        for emb in embeddings:
            result.append({
                'photo': photo,
                'embedding': emb['embedding']
            })
        
        return result if result else None
        
    except Exception:
        return None


def process_batch(photos_batch: List[bytes]) -> List[Dict]:
    results = []
    for photo in photos_batch:
        result = process_single_photo(photo)
        if result:
            results.extend(result)
    return results


def process_imgs_parallel(photos: List[bytes], eps: float = 0.5, 
                         min_samples: int = 2, use_process_pool: bool = False,
                         batch_size: int = 20, show_progress: bool = True,
                         max_workers: Optional[int] = None) -> Tuple[int, List[bytes]]:
    
    if not photos:
        return 0, []
    
    if max_workers is None:
        max_workers = mp.cpu_count()
    
    if use_process_pool and len(photos) > 50:
        executor_class = ProcessPoolExecutor
        all_embeddings = []
        
        with executor_class(max_workers=max_workers) as executor:
            futures = []
            
            for i in range(0, len(photos), batch_size):
                batch = photos[i:i+batch_size]
                future = executor.submit(process_batch, batch)
                futures.append(future)
            
            if show_progress:
                pbar = tqdm(total=len(futures), desc="Processing batches")
            
            for future in futures:
                try:
                    batch_results = future.result(timeout=60)
                    if batch_results:
                        all_embeddings.extend(batch_results)
                except Exception:
                    pass
                finally:
                    if show_progress:
                        pbar.update(1)
            
            if show_progress:
                pbar.close()
    
    else:
        executor_class = ThreadPoolExecutor
        all_embeddings = []
        
        with executor_class(max_workers=max_workers) as executor:
            future_to_photo = {
                executor.submit(process_single_photo, photo): photo 
                for photo in photos
            }
            
            if show_progress:
                pbar = tqdm(total=len(future_to_photo), desc="Processing photos")
            
            for future in as_completed(future_to_photo):
                try:
                    result = future.result(timeout=30)
                    if result:
                        all_embeddings.extend(result)
                except Exception:
                    pass
                finally:
                    if show_progress:
                        pbar.update(1)
            
            if show_progress:
                pbar.close()
    
    all_embeddings = [emb for emb in all_embeddings if emb is not None]
    
    if len(all_embeddings) == 0:
        return 0, []
    
    embeddings_matrix = np.array([item['embedding'] for item in all_embeddings])
    
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine', n_jobs=-1)
    labels = clustering.fit_predict(embeddings_matrix)
    
    clusters = defaultdict(list)
    for idx, label in enumerate(labels):
        if label != -1:
            clusters[label].append(all_embeddings[idx]['photo'])
    
    if clusters:
        max_len = max(len(photos) for photos in clusters.values())
        max_cluster = max(clusters.values(), key=len)
    else:
        max_len = 0
        max_cluster = []
    
    return max_len, max_cluster


def get_vk_driver():
    """Создает и возвращает настроенный WebDriver для VK"""
    log_dir = "C:\\temp\\selenium_logs"
    os.makedirs(log_dir, exist_ok=True)

    options = Options()
    options.add_argument("--user-data-dir=C:\\selenium_profile")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    service = Service()
    service_args = [
        "--verbose",
        f"--log-path={log_dir}\\chromedriver.log",
        "--append-log"
    ]
    service = Service(service_args=service_args)

    driver = webdriver.Chrome(options=options)
    return driver


def get_liker_urls_for_one(driver, photo_url, user_profile_url):
    """Получает список URL лайкнувших пользователей"""
    liker_urls = []
    
    # Извлекаем ID фото из URL
    photo_id = extract_after_photo(photo_url)
    if not photo_id:
        print(f"Не удалось извлечь ID фото из URL: {photo_url}")
        return liker_urls
    
    # Формируем URL БЕЗ двойного кодирования
    # Используем незакодированный формат
    likes_url = f"{user_profile_url}?w=likes/photo{photo_id}"
    
    print(f"Открываем URL лайков: {likes_url}")
    driver.get(likes_url)
    
    # Драйвер сам правильно закодирует URL
    time.sleep(3)
    
    try:
        # Ждем загрузки
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "fans_fan_ph")))
        
        # Прокручиваем для загрузки всех лайков
        scroll_to_bottom(driver)
        time.sleep(2)
        
        # Собираем лайкеров
        likers = driver.find_elements(By.CLASS_NAME, "fans_fan_ph")
        for liker in likers:
            href = liker.get_attribute('href')
            if href:
                liker_urls.append(href)
                
        print(f"Найдено лайков: {len(liker_urls)}")
        
    except TimeoutException:
        print(f"Таймаут при загрузке лайков для {photo_url}")
    except Exception as e:
        print(f"Ошибка при получении лайков: {e}")
    
    return liker_urls


def get_friends(driver, link):
    """Ищет кнопку 'Показать еще' для загрузки дополнительных друзей"""
    print(f"Загружаем {link}")
    driver.get(link)
    
    time.sleep(3)
    
    # Получаем количество
    try:
        active_tab = driver.find_element(By.CSS_SELECTOR, ".vkuiTabsItem__selected")
        counter = active_tab.find_element(By.CSS_SELECTOR, ".vkuiTabsItem__status")
        total_friends = int(counter.text)
        print(f"Друзей должно быть: {total_friends}")
    except:
        total_friends = None
    
    friends = set()
    last_count = 0
    
    while True:
        # Получаем текущие ссылки
        elements = driver.find_elements(By.CSS_SELECTOR, "a.vkitLink__link--b0dQw")
        for elem in elements:
            href = elem.get_attribute('href')
            if href:
                friends.add(href)
        
        print(f"Найдено: {len(friends)}/{total_friends if total_friends else '?'}")
        
        if total_friends and len(friends) >= total_friends:
            break
        
        if len(friends) == last_count:
            # Пробуем найти кнопку "Показать еще"
            try:
                show_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Показать еще')]")
                show_more.click()
                time.sleep(2)
            except:
                # Если кнопки нет, пробуем скролл
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Проверяем, изменилось ли количество
                new_elements = driver.find_elements(By.CSS_SELECTOR, "a.vkitLink__link--b0dQw")
                if len(new_elements) == last_count or len(new_elements) > 3000:
                    break
        else:
            last_count = len(friends)
        
        time.sleep(1)
    
    print(f"Итого друзей: {len(friends)}")
    return list(friends), total_friends


def init_deepface():
    """Инициализация модели DeepFace (однократно)"""
    DeepFace.build_model("Facenet512")


def extract_user_id_from_vk_url(url):
    if not url or not isinstance(url, str):
        return None

    # 1. Прямое извлечение ID из /audios722465521 или /id123456
    match_direct = re.search(r'/(?:audios|id|club|public)(\d+)', url)
    if match_direct:
        return match_direct.group(1)
    return None


def parse_vk_data(vk_url: str, driver: webdriver.Chrome = None, 
                  should_close_driver: bool = True) -> Dict[str, Any]:
    """
    Парсит данные пользователя VK и возвращает результат в формате JSON.
    
    Args:
        vk_url: URL профиля VK
        driver: опционально переданный WebDriver (если None, создается новый)
        should_close_driver: закрывать ли driver после завершения
    
    Returns:
        Dict с данными пользователя
    """
    # Инициализируем DeepFace
    init_deepface()
    
    # Создаем driver, если не передан
    own_driver = False
    if driver is None:
        driver = get_vk_driver()
        own_driver = True
    
    try:
        features = {
            'user_id': None,
            'pictures': 0,
            'friends': 0,
            'likes_pics_med': 0,
            'vk_url': vk_url
        }
        
        # Переходим на главную страницу VK
        driver.get('https://vk.com')
        time.sleep(1)
        driver.get(vk_url)
        # Получаем ссылки на музыку
        audio_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/audios')]")
        if len(audio_links) < 2:
            raise Exception("Не удалось найти аудио ссылки. Возможно, пользователь не авторизован.")
        
        user_liks = {}
        user_liks['music'] = audio_links[1].get_attribute("href")
        vk_user_id = extract_user_id_from_vk_url(user_liks['music'])
        
        if not vk_user_id:
            raise Exception("Не удалось извлечь ID пользователя VK")
        
        user_liks['own_posts'] = f"https://vk.com/wall{vk_user_id}?owner=1"
        user_liks['all_posts'] = f"https://vk.com/wall{vk_user_id}"
        user_liks['avatars'] = f"https://vk.com/album{vk_user_id}_0"
        user_liks['with_others'] = f"https://vk.com/tag{vk_user_id}"
        user_liks['friends'] = f"https://vk.com/friends?id={vk_user_id}&section=all"
        
        # Получаем друзей
        friends, n_friends = get_friends(driver, user_liks['friends'])
        
        # Получаем фото
        driver.get(user_liks['avatars'])
        src_urls, post_urls = extract_image_urls(driver)
        photos = get_imgs(src_urls)
        
        # Обрабатываем фото
        auto_portraits_number, portraits = process_imgs_parallel(photos)
        
        # Находим URL портретов
        portrait_idxs = []
        for portrait in portraits:
            try:
                portrait_idxs.append(photos.index(portrait))
            except ValueError:
                continue
        
        portrait_urls = [post_urls[i] for i in portrait_idxs if i < len(post_urls)]
        
        # Получаем лайки на портретах
        friend_likes_per_portrait = []
        friend_likes_per_portrait = []
        for url in portrait_urls:
            # Передаем vk_url (URL профиля) вместо user_liks['avatars'] (URL альбома)
            liker_urls = get_liker_urls_for_one(driver, url, vk_url)
            common_elements = set(liker_urls) & set(friends)
            friend_likes_per_portrait.append(len(common_elements))
        
        # Вычисляем медиану
        med_friend_likes_per_portrait = 0
        if friend_likes_per_portrait:
            med_friend_likes_per_portrait = np.median(np.array(friend_likes_per_portrait))
        
        # Заполняем результат
        features['user_id'] = vk_user_id
        features['likes_pics_med'] = float(med_friend_likes_per_portrait)
        features['friends'] = n_friends if n_friends else 0
        features['pictures'] = auto_portraits_number
        
        return features
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге VK: {e}")
        raise
    finally:
        # Закрываем driver, если он был создан в этой функции
        if own_driver and should_close_driver:
            driver.quit()


# Функция для вызова через API Flask
def parse_vk_data_api(vk_url: str, consent: bool = True) -> Dict[str, Any]:
    """
    API-совместимая обертка для parse_vk_data.
    
    Args:
        vk_url: URL профиля VK
        consent: согласие на обработку данных
    
    Returns:
        Dict с данными пользователя
    """
    if not consent:
        raise ValueError("Необходимо согласие на обработку данных")
    
    if not vk_url or not isinstance(vk_url, str):
        raise ValueError("Неверный URL VK")
    
    # Создаем driver и парсим
    driver = get_vk_driver()
    try:
        result = parse_vk_data(vk_url, driver=driver, should_close_driver=False)
        get_user_traits({'user_id': [result['user_id']], 'pictures': [result['pictures']], 'friends': [result['friends']], 'likes_pics_med': [result['likes_pics_med']]})
        return result
    finally:
        driver.quit()


#parse_vk_data_api('https://vk.com/marauderofrock')