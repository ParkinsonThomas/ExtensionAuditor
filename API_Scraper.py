import requests
import sqlite3
import datetime
from bs4 import BeautifulSoup

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def update_api_entry(conn, api_url, status_code, content_length, is_active, doc_url):
    """
    Updates an API entry in the database with the new metadata scraped.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    api_url (str): URL of the API being updated.
    status_code (int): HTTP status code from the API request.
    content_length (int): Length of the API response content.
    is_active (bool): Whether the API responded successfully (status 200).
    doc_url (str): URL of the API's documentation, if found.
    """

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE "API" SET "status_code" = ?, "content_length" = ?, "last_checked" = ?, "is_active" = ?, "documentation_url" = ?
        WHERE api_url = ?
    """, (status_code, content_length, datetime.datetime.now(), is_active, doc_url, api_url))
    conn.commit()

def scrape_url(conn, api_url):
    """
    Attempts to access an API URL, checks its status, measures its response size,
    attempts to find related documentation. Calls the "update_api_entry" function
    to insert data found into the database.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    api_url (str): URL of the API to scrape.
    """

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
    """
    Performs a Google search to find a developer documentation page for a given API URL.

    Parameters:
    api_url (str): API URL to find documentation for.

    Returns:
    str or None: URL of documentation if found, None if not.
    """

    search_url = f"https://www.google.com/search?q={api_url}+API+documentation"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # Uses BeautifulSoup to parse HTML from Google search
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            if "developer" in link["href"] or "docs" in link["href"]:
                return link["href"]

    except requests.RequestException:
        pass

    return None

def main(config):
    """
    Main entry point for the API scraping module.

    Parameters:
    config: Configuration settings (used for database).
    """

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]

    # Initialise database connection and retrieve APIs to be analysed
    conn = init_db_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT api_url FROM API")
    stored_apis = cursor.fetchall()

    for (api_url, ) in stored_apis:
        scrape_url(conn, api_url)

    conn.close()