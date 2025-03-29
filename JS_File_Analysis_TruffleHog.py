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

def analyse_files(js_files):
    #start_time = time.time()
    trufflehog_path = "/home/thomas/go/bin/trufflehog" 

    try:
        all_findings = [] 
        for js_file in js_files:
            print(f"Running TruffleHog for file: {js_file}")

            result = subprocess.run(
                [trufflehog_path, "filesystem", js_file, "--json"],
                capture_output=True,
                text=True,
                check=True
            )
            findings = []

            for line in result.stdout.splitlines():
                findings.append(json.loads(line))
            
            all_findings.append(findings)

        #end_time = time.time()
        #elapsed_time = end_time - start_time
        #print(f"Execution time: {elapsed_time:.6f} seconds")
        #print("")

        #for i in range(0, len(js_files)):
        #    print(f"File: {js_files[i]}\nFindings: {all_findings[i]}")    
        #print("")

        return all_findings

    except subprocess.CalledProcessError as e:
        print("Error running TruffleHog:", e.stderr)
        return []

def analyse_extensions(extract_path, guids):
    findings = []
    for guid in guids:
        file_path = os.path.join(extract_path, guid[0])
        js_files = collect_js_files(file_path)
        x = analyse_files(js_files)

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