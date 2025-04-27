import json
import os
import sqlite3
import time
import subprocess
from collections import defaultdict

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

# Populates AnalysisRule table with default rules, if they aren't already there
def init_analysis_rules(conn):
    rules = [
        {
            "name": "eval_usage",
            "severity": "High",
        },
        {
            "name": "new_function_usage",
            "severity": "High",
        },
        {
            "name": "dynamic_timer_string",
            "severity": "Medium",
        },
        {
            "name": "document_write",
            "severity": "High",
        },
        {
            "name": "innerhtml_assignment",
            "severity": "Medium",
        },
        {
            "name": "chrome_execute_script",
            "severity": "Critical",
        },
        {
            "name": "chrome_onmessage_listener",
            "severity": "Medium",
        },
        {
            "name": "storage_access",
            "severity": "Low",
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

# Retrieves all extensions from the database and returns a list of tuples (extension_id, extension_guid)
def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def collect_js_files(extension_path):
    """
    Collects all JavaScript files from the inputted extension directory.

    Parameters:
    extension_path (str): Path to the directory of an extracted extension.

    Returns:
    list[str]: List of file paths to all JavaScript files for an extension.
    """

    js_files = []
    for root, _, files in os.walk(extension_path):
        for file in files:
            if file.endswith(".js"):
                js_files.append(os.path.join(root, file))
    return js_files

def analyse_js_file(js_file_path):
    """
    Runs Analyse_Babel.js (Node.js script) to produce an AST and detect code patterns in a JS file.

    Parameters:
    js_file_path (str): Path to the JavaScript file.

    Returns:
    dict or None: Mapping of pattern name to occurrence count, returns None if error occurs.
    """

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
    """
    Orchestrates the analysis process.
    Inserts one record per pattern per file with the total count.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    extract_path (str): Directory for extracted extensions.
    extensions (list[tuple]): List of (extension_id, extension_guid) tuples.
    """

    start_time = time.time()
    cursor = conn.cursor()

    # Retrieves rule_id from AnalysisRule, to be used as FK when inserting into ExtensionAnalysisJS
    cursor.execute("SELECT rule_id, name FROM AnalysisRule")
    pattern_to_rule = {
        name: rule_id
        for rule_id, name in cursor.fetchall()
    }

    # Iterates through each extension
    for extension in extensions:
        extension_dir = os.path.join(extract_path, extension[1])
        if not os.path.isdir(extension_dir):
            continue
        print(f"Analysing extension: {extension_dir}...")
        
        # Collect JS files, then iterate through each one
        js_files = collect_js_files(extension_dir)
        for js_file in js_files:
            # Retrieves analysed AST
            patterns = analyse_js_file(js_file)

            if patterns:
                # Loops through patterns, processes information and inserts into database
                for pattern, count in patterns.items():
                    rule_id = pattern_to_rule.get(pattern)  
                    cursor.execute(
                        "INSERT INTO ExtensionAnalysisJS (extension_id, rule_id, file_name, count) VALUES (?, ?, ?, ?)",
                        (extension[0], rule_id, js_file, count)
                    )                
        conn.commit()

    # Calculates execution time
    elapsed_time = time.time() - start_time
    print(f"Completed in {elapsed_time:.2f} seconds")


def main(config):
    """
    Main entry point for the Extension analysis pipeline.

    Parameters:
    config: Configuration settings (used for database and directories).
    """

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]

    # Initialise database connection, populate AnalysisRules, retrieve extensions to analyse, call "analyse_extensions" to start the analysis
    conn = init_db_connection(db_file)
    init_analysis_rules(conn)
    extensions = get_extensions_to_analyse(conn)
    analyse_extensions(conn, extract_path, extensions)
    conn.close()