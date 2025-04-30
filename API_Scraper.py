import requests
import sqlite3
import datetime
import time
import sys
import multiprocessing
import threading
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

def insert_data(db_file, queue):
    """
    Updates entries in the API table with scraped information.

    Parameters:
    db_file (str): Path to the database file.
    queue (multiprocessing.Queue): Queue with findings to process.
    """

    conn = init_db_connection(db_file)
    while True:
        result = queue.get()
        if result == "FINISHED":
            conn.close()
            return
        if result:
            api_url, status_code, content_length, is_active, doc_url = result
            update_api_entry(conn, api_url, status_code, content_length, is_active, doc_url)

def scrape_url(api_url):
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

        return (api_url, status_code, content_length, is_active, doc_url)
    
    except requests.RequestException as e:
        return None


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

# Multiprocess worker function
def scrape_api(api_url, queue, counter_queue):
    result = scrape_url(api_url)
    if result:
        queue.put(result)
        counter_queue.put("success")
    else:
        counter_queue.put("fail")

# Updates the terminal with real time updates
def status_updater(counter_queue, num_apis):
    """
    Updates console in real-time to tell the user how many apis (successfully and unsuccesfully) have been scraped.

    Parameters:
    counter_queue (multiprocessing.Queue): Queue to track number of apis analysed.
    num_apis (int): Total number of apis.
    """

    # Counts
    success_count = 0
    fail_count = 0
    processed = 0
    
    # Prints two lines to be used in formatting later
    print("APIs scraped successfully:")
    print("APIs scraped unsuccessfully:")

    while processed < num_apis:
        status = counter_queue.get()
        if status == "success":
            success_count += 1
        else:
            fail_count += 1
        processed += 1

        sys.stdout.write("\033[F\033[K" * 2) # Move up and clear two lines
        sys.stdout.write(f"APIs scraped successfully:    {success_count}\n")
        sys.stdout.write(f"APIs scraped unsuccessfully:  {fail_count}\n")
        sys.stdout.flush()
        time.sleep(0.01)

def main(config):
    """
    Main entry point for the API scraping module.

    Parameters:
    config: Configuration settings (used for database).
    """

    # Start time
    start_time = time.time()

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]

    # Initialise database connection and retrieve APIs to be analysed
    conn = init_db_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT api_url FROM API")
    stored_apis = cursor.fetchall()
    conn.close()

    manager = multiprocessing.Manager()
    queue = manager.Queue()
    counter_queue = manager.Queue()

    writer_process = multiprocessing.Process(target=insert_data, args=(db_file, queue))
    writer_process.start()

    status_thread = threading.Thread(target=status_updater, args=(counter_queue, len(stored_apis)))
    status_thread.start()

    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
    for (api_url,) in stored_apis:
        pool.apply_async(scrape_api, args=(api_url, queue, counter_queue))

    pool.close()
    pool.join()

    queue.put("FINISHED")
    writer_process.join()
    status_thread.join()

    # Formats and outputs execution time
    end_time = time.time()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    print(f"Execution time: {hours:02d}hrs, {minutes:02d}mins, {seconds:02d}secs")