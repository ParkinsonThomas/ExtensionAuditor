import requests
from bs4 import BeautifulSoup
import re
import os

def get_extension_guids(url, result_cap):
    response = requests.get(url)
    
    if response.status_code != 200:
        print("Failed to fetch page:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    extension_divs = soup.find_all("div", attrs={"data-item-id": True})
    
    guids = [div["data-item-id"] for div in extension_divs]

    if not guids:
        print("No extensions found.")
    
    return guids

def save_to_file(guids):
    filename = "GUID_List.txt"

    mode = "a" if os.path.exists(filename) else "w"

    with open(filename, mode) as file:
        for guid in guids:
            file.write(guid + "\n")
    print(f"Saved {len(guids)} extension GUIDs to {filename}")

def main(config):
    scraper_config = config.get("scraper", {})
    url_categories = [
        "https://chromewebstore.google.com/category/extensions",
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
    max_guids = scraper_config.get("max_guids", 30)

    #for url in url_categories:
    guids = get_extension_guids(url_categories[0], max_guids)

    if guids:
        save_to_file(guids)
    else:
        print(f"No GUIDs were found on {url_categories[0]}.")
