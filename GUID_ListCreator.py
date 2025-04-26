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

def get_extension_guids(url):
    """
    Scrapes the Chrome Web Store category page and extracts extension GUIDs.

    Parameters:
    url (str): URL of the Chrome Web Store category page.

    Returns:
    list[str]: List of extension GUIDs found, or an empty list if none found or if a failure occurs.
    """

    try:
        # Configures Selenium options
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--no-sandbox")
        
        # Starts Chrome browser
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(3)   # Allows time for page to load

        wait = WebDriverWait(driver, 3)

        start_time = time.time()
        max_time = 90   # Limits scrolling to a max of 90 seconds

        # Scrolls and clicks "Load More" repeatedly
        while time.time() - start_time < max_time:
            try:
                # Find the "Load More" button
                load_more_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.mUIrbf-vQzf8d:nth-child(5)")))
                
                # Click the button to load more extensions
                driver.execute_script("arguments[0].click();", load_more_button)
                time.sleep(2)  # Wait for more extensions to load
            except selenium_exceptions.TimeoutException:
                break

        # Retrieve HTML of the fully loaded page
        page_source = driver.page_source
        driver.quit()

        # Load BeautifulSoup to perform scraping of HTML
        soup = BeautifulSoup(page_source, "html.parser")

        # Scrapes guids from "data-item-id" div.
        extension_divs = soup.find_all("div", attrs={"data-item-id": True})

        # Processes guids into list
        guids = [div["data-item-id"] for div in extension_divs]

        if not guids:
            print("No extensions found.")
        
        return guids
    
    except Exception as e:
        print(f"Error fetching extension GUIDs: {e}")
        return []

# Saves GUIDs to txt file
def save_to_file(guids, url):
    """
    Saves a list of extension GUIDs to a txt file.

    Parameters:
    guids (list[str]): List of extension GUIDs to save.
    url (str): Chrome Web Store URL of the GUIDs.
    """

    filename = "GUID_List.txt"

    # If file exists GUIDs are appended, if not, file created and written to 
    mode = "a" if os.path.exists(filename) else "w"

    with open(filename, mode) as file:
        for guid in guids:
            file.write(guid + "\n")
    print(f"Saved {len(guids)} extension GUIDs to {filename} from {url}")

# Main function (loads config)
def main(config):
    """
    Iterates over selected Chrome Web Store categories and calls appropriate functions
    to generate list of extension GUIDs.

    Parameters:
    config: Configuration settings (unused here but standard for modularity).
    """

    # Categories for Chrome Web Store
    url_categories = [
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

    # Loop through each url and perform scraping and saving to file.
    for url in url_categories:
        guids = get_extension_guids(url)

        if guids:
            save_to_file(guids, url)
        else:
            print(f"No GUIDs were found on {url_categories[0]}.")
