import json
import os
import sqlite3
import time
import subprocess
from collections import defaultdict

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def init_analysis_rules(conn):
    rules = [
        {
            "name": "eval_usage",
            "severity": "high",
        },
        {
            "name": "new_function_usage",
            "severity": "high",
        },
        {
            "name": "dynamic_timer_string",
            "severity": "medium",
        },
        {
            "name": "document_write",
            "severity": "high",
        },
        {
            "name": "innerhtml_assignment",
            "severity": "medium",
        },
        {
            "name": "chrome_execute_script",
            "severity": "critical",
        },
        {
            "name": "chrome_onmessage_listener",
            "severity": "medium",
        },
        {
            "name": "storage_access",
            "severity": "low",
        },
    ]
    cursor = conn.cursor()
    for rule in rules:
        cursor.execute(
            "SELECT 1 FROM AnalysisRule WHERE name = ?",
            (rule["name"],)
        )
        if cursor.fetchone() is None:
            cursor.execute(
                """
                INSERT INTO AnalysisRule (name, severity)
                VALUES (?, ?)
                """,
                (rule["name"], rule["severity"])
            )
    conn.commit()

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
    cursor = conn.cursor()

    cursor.execute("SELECT rule_id, name FROM AnalysisRule")
    pattern_to_rule = {
        name: rule_id
        for rule_id, name in cursor.fetchall()
    }

    for extension in extensions:
        extension_dir = os.path.join(extract_path, extension[1])
        if not os.path.isdir(extension_dir):
            continue

        print(f"Analysing extension: {extension_dir}...")
        js_files = collect_js_files(extension_dir)

        for js_file in js_files:
            patterns = analyse_js_file(js_file)

            if patterns:
                for pattern, count in patterns.items():
                    rule_id = pattern_to_rule.get(pattern)
                    
                    for i in range(count):
                        cursor.execute("INSERT INTO ExtensionAnalysisJS (extension_id, rule_id, file_name) VALUES (?, ?, ?)",
                                       (extension[0], rule_id, js_file))
                        
    conn.commit()
    elapsed_time = time.time() - start_time
    print(f"Completed in {elapsed_time:.2f} seconds")

def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]

    conn = init_db_connection(db_file)

    init_analysis_rules(conn)

    extensions = get_extensions_to_analyse(conn)
    extensions = extensions[:10]
    analyse_extensions(conn, extract_path, extensions)
    conn.close()