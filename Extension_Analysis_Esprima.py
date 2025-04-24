import json
import os
import re
import sqlite3
import time
import subprocess

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def collect_js_files(extension_path):
    js_files = []
    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):
                js_files.append(os.path.join(root, file))
    return js_files

def analyse_js_file(js_file_path):
    result = subprocess.run(
        ['node', 'Analyse_Esprima.js', js_file_path],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        # Parse the JSON result from Node.js output
        dangerous_patterns = json.loads(result.stdout)
        return dangerous_patterns
    else:
        return None
    

def analyse_extensions(conn, extract_path, extensions):
    start_time = time.time()
    dangerous_count = 0
    files_analysed = 0
    for extension in extensions:
        extension_dir = os.path.join(extract_path, extension[1])
        print(f"Analysing extension {extension_dir}...")
        js_files = collect_js_files(extension_dir)
        for js_file in js_files:
            files_analysed += 1
            dangerous_patterns = analyse_js_file(js_file)

            if dangerous_patterns:
                for pattern, count in dangerous_patterns.items():
                    dangerous_count += 1

    print("===============================")
    print(f"Files analysed: {files_analysed}")
    print(f"Dangerous patterns found: {dangerous_count}")
    print("===============================")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Execution time: {elapsed_time:.6f} seconds")

def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]
    
    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)

    extensions

    analyse_extensions(conn, extract_path, extensions)