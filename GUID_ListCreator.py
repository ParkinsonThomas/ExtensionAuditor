import requests
from bs4 import BeautifulSoup
import re
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import selenium.common.exceptions as selenium_exceptions

import time

def get_extension_guids(url, result_cap):
    #response = requests.get(url)
    
    #if response.status_code != 200:
    #    print("Failed to fetch page:", response.status_code)
    #    return []

    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode (remove this if you want to see the browser)
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(3)  # Allow page to load

    wait = WebDriverWait(driver, 3)

    start_time = time.time()
    max_time = 90

    # Scroll & click "Load More" repeatedly
    while time.time() - start_time < max_time:
        try:
            # Find the "See More" button
            load_more_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.mUIrbf-vQzf8d:nth-child(5)")))
            
            # Click the button to load more extensions
            driver.execute_script("arguments[0].click();", load_more_button)
            time.sleep(2)  # Wait for more extensions to load
        except selenium_exceptions.TimeoutException:
            break

    # Get final loaded HTML
    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, "html.parser")

    extension_divs = soup.find_all("div", attrs={"data-item-id": True})
    
    guids = [div["data-item-id"] for div in extension_divs]

    if not guids:
        print("No extensions found.")
    
    return guids

def save_to_file(guids, url):
    filename = "GUID_List.txt"

    mode = "a" if os.path.exists(filename) else "w"

    with open(filename, mode) as file:
        for guid in guids:
            file.write(guid + "\n")
    print(f"Saved {len(guids)} extension GUIDs to {filename} from {url}")

def main(config):
    scraper_config = config.get("scraper", {})
    url_categories = [
    #    "https://chromewebstore.google.com/category/extensions",
        "https://chromewebstore.google.com/category/extensions/productivity/communication",
        "https://chromewebstore.google.com/category/extensions/productivity/developer",
        "https://chromewebstore.google.com/category/extensions/productivity/education",
        "https://chromewebstore.google.com/category/extensions/productivity/tools",
        "https://chromewebstore.google.com/category/extensions/productivity/workflow",
        "https://chromewebstore.google.com/category/extensions/lifestyle/art",
        "https://chromewebstore.google.com/category/extensions/lifestyle/entertainment",
        "https://chromewebstore.google.com/category/extensions/lifestyle/games",
        "https://chromewebstore.google.com/category/extensions/lifestyle/household",
        "https://chromewebstore.google.com/category/extensions/lifestyle/fun",
        "https://chromewebstore.google.com/category/extensions/lifestyle/news",
        "https://chromewebstore.google.com/category/extensions/lifestyle/shopping",
        "https://chromewebstore.google.com/category/extensions/lifestyle/social",
        "https://chromewebstore.google.com/category/extensions/lifestyle/travel",
        "https://chromewebstore.google.com/category/extensions/lifestyle/well_being",
        "https://chromewebstore.google.com/category/extensions/make_chrome_yours/accessibility",
        "https://chromewebstore.google.com/category/extensions/make_chrome_yours/functionality",
        "https://chromewebstore.google.com/category/extensions/make_chrome_yours/privacy"
    ]
    max_guids = scraper_config.get("max_guids", 200)

    for url in url_categories:
        guids = get_extension_guids(url, max_guids)

        if guids:
            save_to_file(guids, url)
        else:
            print(f"No GUIDs were found on {url_categories[0]}.")
