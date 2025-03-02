import sqlite3
import os
import re
import json

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def find_api_usage(file_path, api_keywords):
    api_usage = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                for api in api_keywords:
                    if api in line:
                        api_usage.append((api, file_path, line_number))
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return api_usage    
    
def analyse_extension(extension_id, extension_path, conn, api_keywords):
    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):
                file_path = os.path.join(root, file)
                api_usage = find_api_usage(file_path, api_keywords)

                for api, path, line in api_usage:
                    api_id = get_api_entry(conn, api)
                    insert_extension_api(conn, extension_id, api_id, path, line)

def get_api_entry(conn, api_name):
    cursor = conn.cursor()
    cursor.execute("SELECT api_id FROM API WHERE name = ?", (api_name, ))
    result = cursor.fetchone()

    if result:
        return result[0]

    else:
        cursor.execute("INSERT INTO API (name) VALUES (?)", (api_name, ))
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
    api_keywords = ["chrome", "browser", "fetch(", "XMLHttpRequest"]

    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]

    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)

    for extension_id, extension_guid in extensions:
        file_path = os.path.join(extract_path, extension_guid)
        if os.path.exists(file_path):
            print(f"Analysing {file_path}...")
            analyse_extension(extension_id, file_path, conn, api_keywords)
        else:
            print(f"ERROR! Directory {file_path} not found.")
    conn.close()