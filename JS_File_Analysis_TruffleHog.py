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
    gitleaks_path = "gitleaks" 

    try:
        print(f"Running Gitleaks in directory: {extension_dir}")
        findings = []

        result = subprocess.run(
        [
            gitleaks_path,
            "detect",
            "--source", extension_dir,
            "--verbose",
            "--no-git",
            "--report-format", "json"
        ],
        capture_output=True,
        text=True,
        )
            
        print("----------------------------------------")
        print(f"Gitleaks raw output:\n{result.stdout}")

        if result.stdout:
            lines = result.stdout.splitlines()
            secret_info = {}
            
            for line in lines:
                if "Secret:" in line:
                    # Extract secret and clean it by removing ANSI escape codes
                    secret = line.split('Secret:')[1].strip()
                    secret = re.sub(r'\x1b\[[0-9;]*m', '', secret)  # Remove ANSI escape codes
                    secret_info['secret'] = secret
                    
                if 'File:' in line:
                    # Extract file
                    secret_info['file'] = line.split('File:')[1].strip()
                    
                if secret_info:  # If secret info has been populated, add it to findings
                    findings.append(secret_info)
                    secret_info = {}  # Reset for the next potential finding

        return findings

    except subprocess.CalledProcessError as e:
        print(f"Error running Gitleaks: {e}")
        print(f"Exit Status: {e.returncode}")
        print(f"Error Output:\n{e.stderr}")
        return []

def analyse_extensions(extract_path, guids):
    start_time = time.time()
    findings = []
    for guid in guids:
        file_path = os.path.join(extract_path, guid[0])
        x = analyse_files(file_path)

        findings.append((guid[0], x))

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Execution time: {elapsed_time:.6f} seconds")

    print("==============")
    print("Final results:")
    for x in findings:
        print(x)


def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]
    
    conn = init_db_connection(db_file)
    guids = get_extensions_to_analyse(conn)

    guids = guids[:20]
    
    #analyse_extensions(extract_path, guids)

    file_path = os.path.join(extract_path, "ofpnmcalabcbjgholdjcjblkibolbppb")
    x = analyse_files(file_path)
    print(x)