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

        element = driver.find_element(By.ID, "tlmdata")
        
        json_str = element.get_attribute("data-tealium-data") 
        data = json.loads(json_str)
        
        genre = data.get('tag', 'N/A').split(',')[0]
        if 'russian' in genre:
            genre = data.get('tag', 'N/A').split(',')[1]
        return genre
    except BaseException as e:
        print(e)
