import sqlite3
import requests
import json
import os
import zipfile
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import time

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def download_extension(extension_guid, download_dir):
    """
    Downloads a Chrome Extension .crx file using its GUID.

    Parameters:
    extension_guid (str): Chrome Extension GUID.
    download_dir (str): Directory for downloaded extension .crx files.

    Returns:
    Path to the downloaded file if successful, None otherwise.
    """

    url = f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=91.0.4472.77&acceptformat=crx2,crx3&x=id%3D{extension_guid}%26uc"
    response = requests.get(url, stream=True)
    
    if response.status_code == 200:
        # Makes a directory for each extension in the downloads directory 
        os.makedirs(download_dir, exist_ok=True)
        file_path = os.path.join(download_dir, f"{extension_guid}.crx")
        with open(file_path, "wb") as f:
            f.write(response.content)
        return file_path
    return None

def extract_extension(file_path, extract_dir):
    """
    Extracts the contents of an extension .crx file into the extracted directory.

    Parameters:
    file_path (str): Path to the downloaded .crx file.
    extract_dir (str): Directory for extracted extensions.

    Returns:
    str: Path to the extracted extension folder.
    """

    os.makedirs(extract_dir, exist_ok=True)
    extract_path = os.path.join(extract_dir, os.path.basename(file_path).replace(".crx", ""))
    with zipfile.ZipFile(file_path, 'r') as zip_reference:
        zip_reference.extractall(extract_path)
    return extract_path

def parse_manifest(manifest_path):
    """
    Parses the manifest.json file from the extracted extension.

    Parameters:
    manifest_path (str): Path to the manifest.json file.

    Returns:
    dict: Parsed manifest as a dictionary.
    """

    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        manifest_data = json.load(f)
    return manifest_data

def extract_author(soup):
    """
    Extracts the extension author's name from the Chome Web Store HTML.

    Parameters:
    soup (BeautifulSoup): Parsed BeautifulSoup object of the Chrome Web Store extension page.

    Returns:
    str: Author name, "Unknown" if not found.
    """

    author_tag = soup.find("div", {"class": "Fm8Cnb"})
    if author_tag:
        author = author_tag.get_text(separator="\n").split("\n")[0].strip()
        return author
    return "Unknown"

def extract_last_updated(soup):
    """
    Extracts the last updated date of the extension from the Chrome Web Store HTML.

    Parameters:
    soup (BeautifulSoup): Parsed BeautifulSoup object of the extension page.

    Returns:
    str: Formatted date as 'YYYY-MM-DD', returns "0000-00-00" if not found or invalid.
    """

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
    """
    Scrapes metadata (name, author, last updated date) from the Chrome Web Store page.

    Parameters:
    extension_guid (str): Chrome Extension GUID.

    Returns:
    dict: Dictionary containing metadata about the extension.
    """

    extension_webstore_url = "https://chromewebstore.google.com/detail/"
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
    """
    Inserts an extension entry into the database.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    extension_guid (str): Chrome Extension GUID.
    manifest_data (dict): Parsed manifest and metadata.
    absolute_path (str): Path to the extracted extension folder.
    """

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

    cursor.execute("""
        INSERT INTO Extension (extension_guid, name, version, manifest_json, author, homepage_url, is_active, last_updated, downloaded_date, absolute_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        extension_values
    )
    conn.commit()

def extension_exists(conn, extension_guid):
    """
    Checks whether an extension exists in the database.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    extension_guid (str): Chrome Extension GUID.

    Returns:
    bool: True if extension exists, False otherwise.
    """

    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Extension WHERE extension_guid = ?", (extension_guid, ))
    return cursor.fetchone() is not None

def run_scraper(conn, extension_guid, download_dir, extract_dir):
    """
    Runs the complete scraping pipeline for a single extension,
    download, extract, parse metadata, and store it in the database.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    extension_guid (str): Extension GUID.
    download_dir (str): Directory for downloaded extension .crx files.
    extract_dir (str): Directory for extracted extensions.
    """

    # Check if extension exists, skips extension if it exists
    if extension_exists(conn, extension_guid):
        #print(f"Skipping {extension_guid}, already exists in database.")
        return ("skipped")

    # Error handling for download failing
    file_path = download_extension(extension_guid, download_dir)
    if not file_path:
        #print("Failed to download extension.")
        return ("failed")

    # Scrapes metadata by calling functions
    extract_path = extract_extension(file_path, extract_dir)
    manifest_data = parse_manifest(os.path.join(extract_path, "manifest.json"))
    scraped_data = scrape_extension_data(extension_guid)
    manifest_data.update(scraped_data)

    insert_extension_data(conn, extension_guid, manifest_data, extract_path)
    #print("Extension data inserted successfully.")
    return ("success")

def main(config):
    """
    Main entry point for the extension scraper.
    Reads GUIDs from file, then runs "run_scraper" which starts the operations.

    Parameters:
    config: Configuration settings (used for database, directories and guid list).
    """
    # Start time
    start_time = time.time()

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]
    download_dir = config["storage"]["download_path"]
    extract_dir = config["storage"]["extract_path"]
    guids_file = config["guid_list"]["name"]

    # Counts for output
    success_count = 0
    fail_count = 0
    skipped_count = 0

    # Processes GUIDs from txt file into a list (guids)
    with open(guids_file, "r") as file:
        guids = [line.strip() for line in file.readlines()]

    # Prints three lines for formatting later
    print("Extensions inserted successfully:")
    print("Extensions inserted unsuccessfully:")
    print("Extensions skipped (already in database):")

    conn = init_db_connection(db_file)
    for guid in guids:
        result = run_scraper(conn, guid, download_dir, extract_dir)
        if result == "success":
            success_count += 1
        if result == "skipped":
            skipped_count += 1
        if result == "failed":
            fail_count += 1

        sys.stdout.write("\033[F\033[K" * 3)  # Move up and clear three lines
        sys.stdout.write(f"Extensions inserted successfully:            {success_count}\n")
        sys.stdout.write(f"Extensions inserted unsuccessfully:          {fail_count}\n")
        sys.stdout.write(f"Extensions skipped (already in database):    {skipped_count}\n")
        sys.stdout.flush()
        time.sleep(0.01)

    # Formats and outputs execution time
    end_time = time.time()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    print(f"Execution time: {hours:02d}hrs, {minutes:02d}mins, {seconds:02d}secs")

    conn.close()