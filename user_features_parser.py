from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
from lastfm_parser import get_genre
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scroll_to_bottom(driver, delay=3):
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
    driver.get(user_liks['avatars'])
    
    wait = WebDriverWait(driver, 20)
    
    try:
        count_xpath = "//div[contains(@class, 'vkitBreadcrumb__indicator')]//h4"
        count_element = wait.until(EC.presence_of_element_located((By.XPATH, count_xpath)))
        total_photos = int(count_element.text)
        print(f"Всего фото в альбоме: {total_photos}")
    except:
        total_photos = None
        print("Не удалось получить количество фото")
    
    all_src_urls = set()
    all_post_urls = set()
    
    last_count = 0
    same_count_attempts = 0
    scroll_attempts = 0
    max_scroll_attempts = 30
    
    scroll_container = driver.find_element(By.CSS_SELECTOR, ".PhotosPageGrid__virtualRoot--8R5Be")
    
    while scroll_attempts < max_scroll_attempts:
        
        photos = driver.find_elements(By.CSS_SELECTOR, 
            ".PhotosPagePhotoGridVirtualItem__root--jeBPH")
        
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
        
        if total_photos and current_count >= total_photos:
            print("Все фото собраны!")
            break
        
        if current_count == last_count:
            same_count_attempts += 1
            if same_count_attempts >= 5:
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                same_count_attempts = 0
        else:
            same_count_attempts = 0
            last_count = current_count
        
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
        time.sleep(2)
        
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

def get_user_ids():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT DISTINCT user_id FROM favorites ORDER BY user_id
    """)
    return cur.fetchall()

def get_liker_urls_for_one(photo_url, album):
        liker_urls = []
        
        driver.get(album + r"?w=likes%2Fphoto" + extract_after_photo(photo_url))
        scroll_to_bottom(driver)
        likers = driver.find_elements(By.CLASS_NAME, "fans_fan_ph ")
        for liker in likers:
            liker_urls.append(liker.get_attribute('href'))
        return liker_urls

def get_friends(link, driver):
    """Ищет кнопку 'Показать еще' для загрузки дополнительных друзей"""
    print(f"Загружаем {link}")
    driver.get(link)
    
    time.sleep(3)
    
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
        
        elements = driver.find_elements(By.CSS_SELECTOR, "a.vkitLink__link--b0dQw")
        for elem in elements:
            href = elem.get_attribute('href')
            if href:
                friends.add(href)
        
        print(f"Найдено: {len(friends)}/{total_friends if total_friends else '?'}")
        
        if total_friends and len(friends) >= total_friends:
            break
        
        if len(friends) == last_count:
            
            try:
                show_more = driver.find_element(By.XPATH, "//button[contains(text(), 'Показать еще')]")
                show_more.click()
                time.sleep(2)
            except:
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                new_elements = driver.find_elements(By.CSS_SELECTOR, "a.vkitLink__link--b0dQw")
                if len(new_elements) == last_count or len(new_elements)> 3000:
                    break
        else:
            last_count = len(friends)
        
        time.sleep(1)
    
    print(f"Итого друзей: {len(friends)}")
    return list(friends), total_friends

def init_deepface():
    """Инициализация модели DeepFace (однократно)"""
    DeepFace.build_model("Facenet512")

init_deepface()
driver = get_vk_driver()

vk_user_ids = get_user_ids()
features = {'user_id': [],'pictures': [], 'friends': [], 'likes_pics_med': []} 

count = 0
vk_user_id = str(vk_user_ids[1][0])
for item in vk_user_ids:
    if count % 3==0:
        file_path = 'user_data.pkl'
        with open(file_path, 'wb') as file:
            pickle.dump(features, file)
    count+=1
    try:
        vk_user_id = str(item[0])
        if vk_user_id in  ['81497874', '99839399', '128579620', '352807988', '376995746', '393467750', '488823322', '491119963', '506242790', '515869754', '518142219', '521411927', '559593247', '560263909', '600431061', '627846415', '628658916', '730394404', '730654420', '737472328', '739428407', '739896331', '5898', '10054150', '12350095', '50331449', '51503353','1', '166220527', '166845152', '171754634', '180854663', '186806131', '194118736', '209865523', '226492618', '230388129', '241869361', '269487052', '279244851', '285581821', '297922641', '311022827', '319387122', '320332176','355846758', '143323595', '1084970499', '56426269', '1021422385', '561344419', '736750737', '766130229', '680995689', '378118909', '1021139334']:
            continue

        user_liks = {}
        user_liks['own_posts'] = "https://vk.com/wall" + vk_user_id + "?owner=1"
        user_liks['all_posts'] = "https://vk.com/wall" + vk_user_id
        user_liks['avatars'] = "https://vk.com/album" + vk_user_id + "_0"
        user_liks['with_others'] = "https://vk.com/tag" + vk_user_id
        user_liks['friends'] =  "https://vk.com/friends?id=" + vk_user_id + "&section=all"
        friends, n_friends = get_friends(user_liks['friends'], driver)

        driver.get('https://vk.com')
        time.sleep(1)
        driver.get(user_liks['avatars'])
        src_urls, post_urls = extract_image_urls(driver)
        photos =  get_imgs(src_urls)
        auto_portraits_number, portraits = process_imgs_parallel(photos)
        portrait_idxs = [photos.index(i) for i in portraits]
        portrait_urls = [post_urls[i] for i in portrait_idxs]
        friend_likes_per_portrait = []
        for url in portrait_urls:
            liker_urls = get_liker_urls_for_one(url, user_liks['avatars'])
            common_elements = set(liker_urls) & set(friends)
            friend_likes_per_portrait.append(len(common_elements))

        med_friend_likes_per_portrait = np.median(np.array(friend_likes_per_portrait))
        features['user_id'].append(vk_user_id)
        features['likes_pics_med'].append(med_friend_likes_per_portrait)
        features["friends"].append(n_friends)
        features['pictures'].append(auto_portraits_number)
    except Exception as e:
        print(vk_user_id, e)
    