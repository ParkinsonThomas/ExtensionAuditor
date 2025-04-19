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
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def collect_js_files(extension_path):
    js_files = []
    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):
                js_files.append(os.path.join(root, file))
    return js_files

def analyse_files(conn, extract_path, guid, extension_id):
    gitleaks_path = "gitleaks" 

    try:
        extension_dir = os.path.join(extract_path, guid)
        print(f"Running Gitleaks in directory: {extension_dir}")
        findings = []
        secret, rule_id, entropy, file_name, line_num = None, None, None, None, None

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

        if result.stdout:
            lines = result.stdout.splitlines()
            
            for line in lines:
                if "Secret:" in line:
                    secret = line.split('Secret:')[1].strip()
                    secret = re.sub(r'\x1b\[[0-9;]*m', '', secret)   
                elif 'RuleID:' in line:
                    rule_id = line.split("RuleID:")[1].strip()
                elif 'File:' in line:
                    file_name = line.split('File:')[1].strip()
                elif 'Entropy:' in line:
                    entropy = float(line.split('Entropy:')[1].strip())
                elif 'Line:' in line:
                    line_num = line.split('Line:')[1].strip()

                    
                if all(v is not None for v in [secret, rule_id, entropy, file_name, line_num]):
                    insert_data(conn, extension_id, secret, rule_id, entropy, file_name, line_num)
                    secret, rule_id, entropy, file_name, line_num = None, None, None, None, None

        return findings

    except subprocess.CalledProcessError as e:
        print(f"Error running Gitleaks: {e}")
        print(f"Exit Status: {e.returncode}")
        print(f"Error Output:\n{e.stderr}")
        return []
    
def insert_data(conn, extension_id, secret, rule_id, entropy, file_name, line_num):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Extension_KeyPwd_Faults (extension_id, file_name, line, rule_id, secret, entropy)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (extension_id, file_name, line_num, rule_id, secret, entropy)
    )
    conn.commit()

def analyse_extensions(conn, extract_path, extensions):
    start_time = time.time()
    findings = []
    for extension in extensions:
        analyse_files(conn, extract_path, extension[1], extension[0])

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Execution time: {elapsed_time:.6f} seconds")

def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]
    
    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)

    extensions = extensions[:20]

    analyse_extensions(conn, extract_path, extensions)

    #file_path = os.path.join(extract_path, "ofpnmcalabcbjgholdjcjblkibolbppb")
    #x = analyse_files(file_path)
    #print(x)