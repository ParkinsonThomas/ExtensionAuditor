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

def scrape_extension_data(extension_guid):
    url = f"{extension_webstore_url}{extension_guid}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        name = soup.find("meta", {"property": "og.title"})
        author = soup.find("meta", {"name": "author"})
        publish_date = soup.find("meta", {"itemprop": "datePublished"})
        last_updated = soup.find("meta", {"itemprop": "dateModified"})
        return {
            "name": name["content"] if name else "Unknown",
            "author": author["content"] if author else "Unknown",
            "publish_date": publish_date["content"] if publish_date else None,
            "last_updated": last_updated["content"] if last_updated else None
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
        manifest_data.get("publish_date") or "0000-00-00",
        manifest_data.get("last_updated") or "0000-00-00",
        downloaded_date,
        absolute_path
    )

    #print("DEBUG:")
    #for i in extension_values:
    #    print(extension_values[i])

    cursor.execute("""
        INSERT INTO Extension (extension_guid, name, version, manifest_json, author, homepage_url, is_active, publish_date, last_updated, downloaded_date, absolute_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        extension_values
    )
    conn.commit()

def main():
    conn = init_db_connection()
    extension_guid = "imbncilibdpngpkpbnhadjfcjoplkpfc"

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
    conn.close()

if __name__ == "__main__":
    main()
    