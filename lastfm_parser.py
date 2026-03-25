from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time


def get_genre(title, artist, driver):

    title = "+".join(title.split())
    artist = "+".join(artist.split())

    url = "https://www.last.fm/music/" + artist + "/_/" + title


    try:
        driver.get(url)

        # Получаем атрибут data-tealium-data
        element = driver.find_element(By.ID, "tlmdata")
        
        # Парсим JSON (убираем экранированные кавычки)
        json_str = element.get_attribute("data-tealium-data") 
        data = json.loads(json_str)
        
        #print("Извлеченные данные:")
        #print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Доступ к ключевым полям
        #print(f"\nАртист: {data.get('musicArtistName', 'N/A')}")
        #print(f"Альбом: {data.get('musicAlbumName', 'N/A')}")
        #print(f"Теги: {data.get('tag', 'N/A')}")
        genre = data.get('tag', 'N/A').split(',')[0]
        if 'russian' in genre:
            genre = data.get('tag', 'N/A').split(',')[1]
        return genre
    except BaseException as e:
        print(e)


        

