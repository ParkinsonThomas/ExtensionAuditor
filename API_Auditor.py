import sqlite3
import os
import re
import json
import openai

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def find_api_usage(file_path):
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
    
    api_list = audit_api_links(api_usage)

    return api_list
    
def audit_api_links(api_usage):
    api_list = []
    openai.api_key = os.getenv("OPENAI_API_KEY")

    for link in api_usage:
        prompt = f"Is the following URL an API endpoint and not just a documentation or namespace link? Please answer with just 'Yes' or 'No'.\n\nURL: {link}"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0
            )
            answer = response["choices"][0]["message"]["content"].strip().lower()
            if answer.startswith("Yes"):
                api_list.append(link)
        except Exception as e:
            print(f"Error querying the API for link: {link}: {e}")

    return api_list    

def analyse_extension(extension_id, extension_path, conn):
    detected_apis = set()

    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):
                file_path = os.path.join(root, file)
                api_usage = find_api_usage(file_path)

                for api, path, line in api_usage:
                    if api not in detected_apis:
                        detected_apis.add(api)
                        api_id = get_api_entry(conn, api)
                        insert_extension_api(conn, extension_id, api_id, path, line)
                if len(detected_apis) == len(api_usage):
                    break

def get_api_entry(conn, api_name):
    cursor = conn.cursor()
    cursor.execute("SELECT api_id FROM API WHERE name = ?", (api_name, ))
    result = cursor.fetchone()

    author = "Google" if api_name.startswith(("chrome.", "browser.")) else "Third Party"

    if result:
        return result[0]

    else:
        cursor.execute("INSERT INTO API (name, author) VALUES (?, ?)", (api_name, author, ))
        conn.commit()
        return cursor.lastrowid
    
def insert_extension_api(conn, extension_id, api_id, file_path, line_number):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ExtensionAPIs (extension_id, api_id, file_path, line_number)
        VALUES (?, ?, ?, ?)
    """, (extension_id, api_id, file_path, line_number))
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