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
import shutil

# Создаем папку для логов, если её нет
log_dir = "C:\\temp\\selenium_logs"
os.makedirs(log_dir, exist_ok=True)

# Удаляем старую папку профиля, если она существует и создаем новую
profile_dir = "C:\\selenium_profile"
os.makedirs(profile_dir, exist_ok=True)

options = Options()

# Базовые опции
options.add_argument(f"--user-data-dir={profile_dir}")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# Убираем remote-debugging-port, так как он может конфликтовать
# options.add_argument("--remote-debugging-port=9222")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-extensions")
options.add_argument("--disable-plugins")
options.add_argument("--disable-images")
options.add_argument("--disable-javascript")  # Временно для теста

# Добавляем опции для избежания конфликтов
options.add_argument("--disable-logging")
options.add_argument("--log-level=3")  # Только фатальные ошибки
options.add_argument("--silent")

# Важно: отключаем автоматическое закрытие при ошибках
options.add_experimental_option("detach", False)

# Настройка сервиса
service = Service()
service.service_args = [
    "--verbose",
    f"--log-path={log_dir}\\chromedriver.log",
    "--append-log"
]

try:
    driver = webdriver.Chrome(service=service, options=options)
    print("ChromeDriver успешно запущен!")
    
    # Тестовая навигация
    driver.get("https://vk.com")
    print("Страница загружена")
    time.sleep(60)
    # Ваш остальной код здесь...
    
except Exception as e:
    print(f"Ошибка при запуске: {e}")
    
    # Альтернативный способ без профиля
    print("Пробуем запустить без профиля...")
    options_clean = Options()
    options_clean.add_argument("--no-sandbox")
    options_clean.add_argument("--disable-dev-shm-usage")
    options_clean.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=options_clean)
        print("ChromeDriver успешно запущен без профиля!")
    except Exception as e2:
        print(f"Ошибка при запуске без профиля: {e2}")
        exit(1)