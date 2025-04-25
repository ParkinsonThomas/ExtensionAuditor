import json
import os
import sqlite3
import time
import subprocess
from collections import defaultdict

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
        ['node', 'Analyse_Babel.js', js_file_path],
        capture_output=True, text=True
    )

    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print(result.stdout)
            return None
    else:
        if result.stderr.strip():
            print(result.stderr.strip())
        return None

def analyse_extensions(conn, extract_path, extensions):
    start_time = time.time()
    total_dangerous_patterns = defaultdict(int)
    dangerous_files = []
    files_analysed = 0

    for extension in extensions:
        extension_dir = os.path.join(extract_path, extension[1])
        if not os.path.isdir(extension_dir):
            continue

        print(f"Analysing extension: {extension_dir}...")
        js_files = collect_js_files(extension_dir)

        for js_file in js_files:
            files_analysed += 1
            patterns = analyse_js_file(js_file)

            if patterns:
                for pattern, count in patterns.items():
                    total_dangerous_patterns[pattern] += count
                dangerous_files.append(js_file)

    print("===============================")
    print(f"Total files analysed: {files_analysed}")
    print(f"Files with dangerous patterns: {len(dangerous_files)}")
    print("===============================")

    if total_dangerous_patterns:
        print("Summary of dangerous patterns:")
        for pattern, count in sorted(total_dangerous_patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {pattern}: {count}")
    else:
        print("No dangerous patterns detected!")

    elapsed_time = time.time() - start_time
    print(f"Completed in {elapsed_time:.2f} seconds")

def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]

    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)
    analyse_extensions(conn, extract_path, extensions)