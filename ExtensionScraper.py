import sqlite3
import requests
import json
import os
import zipfile
from bs4 import BeautifulSoup
from datetime import datetime

db_file = "ExtensionDB.db"
extension_webstore_url = "https://chromewebstore.google.com/detail/"

def init_db_connection():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    return conn

def download_extension(extension_guid, save_path="Extensions_Downloaded"):
    url = f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=91.0.4472.77&acceptformat=crx2,crx3&x=id%3D{extension_guid}%26uc"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, f"{extension_guid}.crx")
        with open(file_path, "wb") as f:
            f.write(response.content)
        return file_path
    return None

def extract_extension(file_path, extract_to="Extensions_Extracted"):
    os.makedirs(extract_to, exist_ok=True)
    extract_path = os.path.join(extract_to, os.path.basename(file_path).replace(".crx", ""))
    with zipfile.ZipFile(file_path, 'r') as zip_reference:
        zip_reference.extractall(extract_path)
    return extract_path

def parse_manifest(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    return manifest_data

def extract_author(soup):
    author_tag = soup.find("div", {"class": "Fm8Cnb"})
    if author_tag:
        author = author_tag.get_text(separator="\n").split("\n")[0].strip()
        return author
    return "Unknown"

def extract_last_updated(soup):
    last_updated_li = soup.find("li", {"class": "ZbWJPd uBIrad"})
    if last_updated_li:
        divs = last_updated_li.find_all("div")
        if len(divs) > 1:
            raw_date = divs[1].text.strip()

            try:
                formatted_date = datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y-%m-%d")
                return formatted_date
            except ValueError:
                return "0000-00-00"
        
    return "0000-00-00"

def scrape_extension_data(extension_guid):
    url = f"{extension_webstore_url}{extension_guid}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        name_tag = soup.find("h1", {"class": "Pa2dE"})
        name = name_tag.text.strip() if name_tag else "Unknown"

        author = extract_author(soup)
        last_updated = extract_last_updated(soup)

        return {
            "name": name,
            "author": author,
            "last_updated": last_updated
        }
    return {}

def insert_extension_data(conn, extension_guid, manifest_data, absolute_path):
    cursor = conn.cursor()
    downloaded_date = datetime.today().strftime('%Y-%m-%d')
    
    extension_values = (
        extension_guid,
        manifest_data.get("name", "Unknown"),
        manifest_data.get("version", "0.0"),
        json.dumps(manifest_data),
        manifest_data.get("author", "Unknown"),
        manifest_data.get("homepage_url", "Unknown"),
        True,
        manifest_data.get("last_updated") or "0000-00-00",
        downloaded_date,
        absolute_path
    )

    #print("DEBUG:")
    #for i in extension_values:
    #    print(extension_values[i])

    cursor.execute("""
        INSERT INTO Extension (extension_guid, name, version, manifest_json, author, homepage_url, is_active, last_updated, downloaded_date, absolute_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        extension_values
    )
    conn.commit()

def run_scraper(conn, extension_guid):
    file_path = download_extension(extension_guid)
    if not file_path:
        print("Failed to download extension.")
        return

    extract_path = extract_extension(file_path)
    manifest_data = parse_manifest(os.path.join(extract_path, "manifest.json"))
    scraped_data = scrape_extension_data(extension_guid)
    manifest_data.update(scraped_data)

    insert_extension_data(conn, extension_guid, manifest_data, extract_path)
    print("Extension data inserted successfully.")
    return

def main():
    conn = init_db_connection()
    extension_guid = "imbncilibdpngpkpbnhadjfcjoplkpfc"
    run_scraper(conn, extension_guid)

    extension_guid2 = "eimadpbcbfnmbkopoojfekhnkhdbieeh"
    run_scraper(conn, extension_guid2)

    conn.close()

if __name__ == "__main__":
    main()
    