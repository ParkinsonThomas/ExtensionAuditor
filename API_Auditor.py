import sqlite3
import os
import re
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def find_api_usage(file_path, conn):
    api_usage = []

    api_patterns = [
        re.compile(r'\b(?:chrome|browser)\.[a-zA-Z0-9_\.]+'),  # Chrome APIs
        re.compile(r'\b(fetch|XMLHttpRequest)\b'),
        re.compile(r'https?://[a-zA-Z0-9./_-]+')
    ]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                for pattern in api_patterns:
                    matches = pattern.findall(line)
                    for match in matches:
                        api_usage.append((match, file_path, line_number))
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")

    return api_usage

def audit_api_links(api_usage, conn):
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
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )

            # Extract JSON response from DeepSeek
            raw_answer = response.choices[0].message.content.strip()
            answer = re.search(r"\[.*\]", raw_answer, re.DOTALL)

            try:
                valid_apis = json.loads(answer.group(0))  # Convert response to list
            except json.JSONDecodeError:
                print("Error: DeepSeek response is not valid JSON.")
                valid_apis = []

            # Store results in DB
            for link in api_to_audit:
                if link in valid_apis:
                    insert_api_entry(conn, link)
                    api_list.append(link)
                else:
                    insert_url_entry(conn, link)  # Mark as non-API

        except Exception as e:
            print(f"Error querying DeepSeek API: {e}")

    return api_list

def analyse_extension(extension_id, extension_path, conn):
    inserted_apis = set()
    all_api_usage = []

    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):
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
            inserted_apis.add(api)

def get_api_entry(conn, api_url):
    cursor = conn.cursor()
    cursor.execute("SELECT api_id FROM API WHERE api_url = ?", (api_url, ))
    result = cursor.fetchone()

    if result:
        return result[0]
    else:
        return None

def insert_api_entry(conn, api_url):
    author = "Google" if api_url.startswith(("chrome.", "browser.")) else "Third Party"    
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO API (api_url, author) VALUES (?, ?)", (api_url, author, ))
    conn.commit()

def get_url_entry(conn, url):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM URLs WHERE name = ?", (url, ))
    result = cursor.fetchone()

    if result:
        return True
    else:
        return False
    
def insert_url_entry(conn, url):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO URLs (name) VALUES (?)", (url, ))
    conn.commit()
    
def insert_extension_api(conn, extension_id, api_id, path, line):
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
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]

    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)

    for extension_id, extension_guid in extensions:
        file_path = os.path.join(extract_path, extension_guid)
        if os.path.exists(file_path):
            print(f"Analysing {file_path}...")
            analyse_extension(extension_id, file_path, conn)
        else:
            print(f"ERROR! Directory {file_path} not found.")
    conn.close()