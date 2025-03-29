import sqlite3
import os
import re
import json
import time
import subprocess

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_guid FROM Extension")
    return cursor.fetchall()

def collect_js_files(extension_path):
    js_files = []
    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):
                js_files.append(os.path.join(root, file))
    return js_files

def analyse_files(extension_dir):
    #start_time = time.time()
    trufflehog_path = "/home/thomas/go/bin/trufflehog" 

    try:
        print(f"Running TruffleHog in directory: {extension_dir}")

        result = subprocess.run(
        [
            trufflehog_path,
            "filesystem",
            extension_dir,
            "--include", r"\.js$",
            "--json"
        ],
        capture_output=True,
        text=True,
        check=True
        )
        findings = []

        for line in result.stdout.splitlines():
            findings.append(json.loads(line))
        
        #end_time = time.time()
        #elapsed_time = end_time - start_time
        #print(f"Execution time: {elapsed_time:.6f} seconds")

        return findings

    except subprocess.CalledProcessError as e:
        print("Error running TruffleHog:", e.stderr)
        return []

def analyse_extensions(extract_path, guids):
    findings = []
    for guid in guids:
        file_path = os.path.join(extract_path, guid[0])
        x = analyse_files(file_path)

        findings.append((guid, x))

    print("==============")
    print("Final results:")
    for x in findings:
        print(x)


def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]
    
    conn = init_db_connection(db_file)
    guids = get_extensions_to_analyse(conn)
    
    analyse_extensions(extract_path, guids)