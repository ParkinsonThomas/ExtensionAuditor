import sqlite3
import os
import re
import sys
import time
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

# Retrieves all extensions from the database and returns a list of tuples (extension_id, extension_guid)
def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def find_api_usage(file_path, conn):
    """
    Scans a JavaScript file to detect possible API calls.

    Parameters:
    file_path (str): Path to the JavaScript file.
    conn (sqlite3.Connection): Database connection.

    Returns:
    list[tuple]: List of (API usage string, file path, line number) matches.
    """
    
    # Regex patterns
    api_patterns = [
        re.compile(r'\b(?:chrome|browser)\.[a-zA-Z0-9_\.]+'),   # Chrome or Browser APIs
        re.compile(r'\b(fetch|XMLHttpRequest)\b'),              # fetch() and XMLHttpRequests
        re.compile(r'https?://[a-zA-Z0-9./_-]+')                # All URLs                
    ]
    api_usage = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                for pattern in api_patterns:
                    matches = pattern.findall(line)
                    for match in matches:
                        api_usage.append((match, file_path, line_number))
    except Exception as e:
        #print(f"Error reading file {file_path}: {e}")
        return api_usage

    return api_usage

def audit_api_links(api_usage, conn):
    """
    Filters a list of potential API usages, verifying which are true API endpoints.
    Uses DeepSeek's API (LLM) to validate URLs and filters out false positives.

    Parameters:
    api_usage (list[tuple]): List of (API usage string, file path, line number).
    conn (sqlite3.Connection): Database connection.

    Returns:
    list[str]: List of valid API URLs.
    """

    api_list = []
    api_to_audit = set()
    for api_tuple in api_usage:
        api_url = api_tuple[0]
        if get_url_entry(conn, api_url) == False:
            if get_api_entry(conn, api_url) == None:
                api_to_audit.add(api_url)
            else:
                api_list.append(api_url)

    if len(api_to_audit) > 0:

        prompt = f"""Here is a list of URLs. Remove any that are not actual API endpoints 
        (e.g., documentation pages or namespace links). Return only the valid API URLs in a JSON array with no extra text.
        
        URLs: {list(api_to_audit)}

        Example response:
        ["https://api.example.com", "https://api.someother.com"]
        
        """
        
        try:
            # DeepSeek query
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )

            # Extract JSON response from DeepSeek
            raw_answer = response.choices[0].message.content.strip()
            answer = re.search(r"\[.*\]", raw_answer, re.DOTALL)

            try:
                valid_apis = json.loads(answer.group(0))    # Convert response to list
            except json.JSONDecodeError:
                #print("Error: DeepSeek response is not valid JSON.")
                valid_apis = []

            # Store results in database
            for link in api_to_audit:
                if link in valid_apis:
                    insert_api_entry(conn, link)    # Stores API URL in database
                    api_list.append(link)
                else:
                    insert_url_entry(conn, link)    # Stores URL to use for pre-filtering in the future

        except Exception as e:
            #print(f"Error querying DeepSeek API: {e}")
            return api_list
            
    return api_list

def analyse_extension(extension_id, extension_path, conn):
    """
    Conducts analysis for APIs on an extracted extension directory.

    Parameters:
    extension_id (int): Extension ID.
    extension_path (str): Path to the extracted extension folder.
    conn (sqlite3.Connection): Database connection.
    """

    # Uses set to only track one instance of the API URL
    inserted_apis = set()
    all_api_usage = []

    # Iterates through the directory
    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):    # Only analyses JavaScript files
                file_path = os.path.join(root, file)
                api_usage = find_api_usage(file_path, conn)
                all_api_usage.extend(api_usage)

    api_audit_list = audit_api_links(all_api_usage, conn)
    audited_api_usage = [entry for entry in all_api_usage if entry[0] in api_audit_list]

    for api, path, line in audited_api_usage:
        if api not in inserted_apis:
            api_id = get_api_entry(conn, api)
            if api_id == None:
                insert_api_entry(conn, api)
                api_id = get_api_entry(conn, api)
            
            insert_extension_api(conn, extension_id, api_id, path, line)
            inserted_apis.add(api)  # Adds API URL to set to ensure it isn't processed again

def get_api_entry(conn, api_url):
    """
    Looks up an API URL in the database.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    api_url (str): API URL to lookup.

    Returns:
    int or None: API ID if found, returns None if not.
    """

    cursor = conn.cursor()
    cursor.execute("SELECT api_id FROM API WHERE api_url = ?", (api_url, ))
    result = cursor.fetchone()

    if result:
        return result[0]
    else:
        return None

def insert_api_entry(conn, api_url):
    """
    Inserts a new API URL into the database.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    api_url (str): API URL to insert.
    """

    author = "Google" if api_url.startswith(("chrome.", "browser.")) else "Third Party"    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO API (api_url, author) VALUES (?, ?)", (api_url, author, ))
    conn.commit()

def get_url_entry(conn, url):
    """
    Checks if a URL exists in the URLs database table.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    url (str): URL to check.

    Returns:
    bool: True if exists, False if not.
    """

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM URLs WHERE name = ?", (url, ))
    result = cursor.fetchone()

    if result:
        return True
    else:
        return False
    
# Inserts URL into the URLs table
def insert_url_entry(conn, url):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO URLs (name) VALUES (?)", (url, ))
    conn.commit()
    
def insert_extension_api(conn, extension_id, api_id, path, line):
    """
    Creates an entry into the "ExtensionAPIs" linking table, recording which APIs are present in Extensions.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    extension_id (int): Extension ID.
    api_id (int): API ID.
    path (str): File path of where the API is used.
    line (int): Line number where the API was used.
    """

    # Check to make sure entry doesn't exist
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM ExtensionAPIs WHERE extension_id = ? AND api_id = ?
    """, (extension_id, api_id))
    
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO ExtensionAPIs (extension_id, api_id, file_path, line_number)
            VALUES (?, ?, ?, ?)
        """, (extension_id, api_id, path, line))
        conn.commit()

def main(config):
    """
    Main entry point for the API auditing pipeline.

    Parameters:
    config: Configuration settings (used for database and directories).
    """
    # Start time
    start_time = time.time()

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]

    # Initialise database connection and retrieve extensions to analyse
    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)

    # Counts
    success_count = 0
    fail_count = 0

    # Prints three lines for formatting later
    print("Extensions audited successfully:")
    print("Extensions audited unsuccessfully:")
    
    # Iterates through each extension and calls "analyse_extension"
    for extension_id, extension_guid in extensions:
        file_path = os.path.join(extract_path, extension_guid)
        if os.path.exists(file_path):
            analyse_extension(extension_id, file_path, conn)
            success_count += 1
        else:
            fail_count += 1
        
        sys.stdout.write("\033[F\033[K" * 2)  # Move up and clear three lines
        sys.stdout.write(f"Extensions audited successfully:     {success_count}\n")
        sys.stdout.write(f"Extensions audited unsuccessfully:   {fail_count}\n")
        sys.stdout.flush()
        time.sleep(0.05)

    # Formats and outputs execution time
    end_time = time.time()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    print(f"Execution time: {hours:02d}hrs, {minutes:02d}mins, {seconds:02d}secs")

    conn.close()