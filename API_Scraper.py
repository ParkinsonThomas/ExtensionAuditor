import requests
import sqlite3
import datetime
from bs4 import BeautifulSoup

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def update_api_entry(conn, api_url, status_code, content_length, is_active, doc_url):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE "API" SET "status_code" = ?, "content_length" = ?, "last_checked" = ?, "is_active" = ?, "documentation_url" = ?
        WHERE api_url = ?
    """, (status_code, content_length, datetime.datetime.now(), is_active, doc_url, api_url))
    conn.commit()

def scrape_url(conn, api_url):
    headers = {"User-Agent": "API_Scraper"}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        status_code = response.status_code
        content_length = len(response.content) if response.content else 0

        is_active = status_code == 200

        doc_url = extract_documentation_url(api_url)
        doc_url = doc_url if doc_url else ""

        update_api_entry(conn, api_url, status_code, content_length, is_active, doc_url)
        print(f"Scraped: {api_url} - Status: {status_code}")
    
    except requests.RequestException as e:
        print(f"Failed to scrape {api_url}: {e}")


def extract_documentation_url(api_url):
    search_url = f"https://www.google.com/search?q={api_url}+API+documentation"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            if "developer" in link["href"] or "docs" in link["href"]:
                return link["href"]

    except requests.RequestException:
        pass

    return None

def main(config):
    db_file = config["database"]["db"]

    conn = init_db_connection(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT api_url FROM API")
    stored_apis = cursor.fetchall()

    for (api_url, ) in stored_apis:
        scrape_url(conn, api_url)

    conn.close()