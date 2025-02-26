import requests
from bs4 import BeautifulSoup
import re

def get_extension_guids(url, result_cap):
    response = requests.get(url)
    
    if response.status_code != 200:
        print("Failed to fetch page:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Find all div elements containing 'data-item-id'
    extension_divs = soup.find_all("div", attrs={"data-item-id": True})
    
    guids = [div["data-item-id"] for div in extension_divs]

    if not guids:
        print("No extensions found.")
    
    return guids

def save_to_file(guids):
    filename = "GUID_List.txt"

    with open(filename, "w") as file:
        for guid in guids:
            file.write(guid + "\n")
    print(f"Saved {len(guids)} extension GUIDs to {filename}")

def main():
    url_category = "https://chromewebstore.google.com/category/extensions"
    guids = get_extension_guids(url_category, 30)

    if guids:
        print(f"Extracted {len(guids)} GUIDs.")
        save_to_file(guids)
        return guids
    else:
        print("No GUIDs were found.")
        return []
