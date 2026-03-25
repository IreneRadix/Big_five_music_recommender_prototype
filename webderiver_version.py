from selenium import webdriver

driver = webdriver.Chrome()
# Получаем словарь со всеми capabilities текущей сессии
capabilities = driver.capabilities

# Ключ для версии драйвера может отличаться в разных версиях Selenium
# Чаще всего это 'chrome' -> 'chromedriverVersion' или прямой ключ 'driverVersion'
if 'chrome' in capabilities:
    chrome_info = capabilities['chrome']
    if 'chromedriverVersion' in chrome_info:
        print(f"Версия ChromeDriver: {chrome_info['chromedriverVersion']}")

# В более новых версиях Selenium (4.x) информация может быть здесь:
if 'driverVersion' in capabilities:
    print(f"Версия ChromeDriver: {capabilities['driverVersion']}")

driver.quit()