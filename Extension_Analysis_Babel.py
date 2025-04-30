import json
import os
import sqlite3
import time
import subprocess
import sys
import multiprocessing
import threading

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
                full_path = os.path.join(root, file)
                if os.path.getsize(full_path) > 200:
                    js_files.append(full_path)
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
            return None
    else:
        return None

def analyse_extensions(extract_path, extension_id, extension_guid, rule_map, queue, ext_counter_queue, file_counter_queue):
    """
    Performs AST analysis on all JavaScript files in an extension, inserts results into queue.

    Parameters:
    extract_path (str): Path to extension.
    extension_id (int): Extension ID.
    extension_guid (str): Extension GUID.
    rule_map (dict): Mapping of pattern name to rule ID.
    queue (multiprocessing.Queue): Queue to send results to insert_data.
    ext_counter_queue (multiprocessing.Queue): Queue to track number of extensions analysed.
    file_counter_queue (multiprocessing.Queue): Queue to track success and failure for files.
    """

    extension_dir = os.path.join(extract_path, extension_guid)
    js_files = collect_js_files(extension_dir)
    findings = []
    success = False

    for js_file in js_files:
        # Retrieves analysed AST
        patterns = analyse_js_file(js_file)

        if patterns:
            success = True
            file_counter_queue.put("success")
            # Loops through patterns, processes information and inserts into database
            for pattern, count in patterns.items():
                rule_id = rule_map.get(pattern)
                if rule_id:
                    findings.append((extension_id, rule_id, js_file, count))
        else:
            file_counter_queue.put("fail")

    queue.put(findings)
    ext_counter_queue.put("success" if success else "fail")
    
                        
def insert_data(db_file, queue):
    """
    Creates an entry for a detected secret in the "ExtensionSecrets" table.

    Parameters:
    db_file (str): Path to the database file.
    queue (multiprocessing.Queue): Queue with findings to process.
    """

    conn = init_db_connection(db_file)
    cursor = conn.cursor()
    while True:
        findings = queue.get()
        if findings == "FINISHED":
            conn.close()
            return
        for (extension_id, rule_id, file_name, count) in findings:
            cursor.execute(
                "INSERT INTO ExtensionAnalysisJS (extension_id, rule_id, file_name, count) VALUES (?, ?, ?, ?)",
                (extension_id, rule_id, file_name, count)
            )
        conn.commit()

def status_updater(ext_counter_queue, file_counter_queue, num_extensions):
    """
    Updates console in real-time to tell the user how many extensions (successfully and unsuccesfully) have been analysed.

    Parameters:
    ext_counter_queue (multiprocessing.Queue): Queue to track number of extensions analysed.
    file_counter_queue (multiprocessing Queue): Queue to track success and failure for files
    num_extensions (int): Total number of extensions.
    """

    # Counts
    extension_count = 0
    file_success_count = 0
    file_fail_count = 0
    processed = 0

    # Prints three lines to be used in formatting later
    print("Extensions analysed:")
    print("Files analysed successfully:")
    print("Files analysed unsuccessfully:")

    while processed < num_extensions:
        if not ext_counter_queue.empty():
            status = ext_counter_queue.get()
            extension_count += 1
            processed += 1

        if not file_counter_queue.empty():
            status = file_counter_queue.get()
            if status == "success":
                file_success_count += 1
            else:
                file_fail_count += 1

        sys.stdout.write("\033[F\033[K" * 3)  # Move up and clear three lines
        sys.stdout.write(f"Extensions analysed:             {extension_count}\n")
        sys.stdout.write(f"Files analysed successfully:     {file_success_count}\n")
        sys.stdout.write(f"Files analysed unsuccessfully:   {file_fail_count}\n")
        sys.stdout.flush()
        time.sleep(0.02)

def main(config):
    """
    Main entry point for the Extension analysis pipeline.

    Parameters:
    config: Configuration settings (used for database and directories).
    """
    # Start time
    start_time = time.time()

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]

    # Retrieve extensions to analyse, call "analyse_extensions" to start the analysis
    conn = init_db_connection(db_file)
    init_analysis_rules(conn)
    extensions = get_extensions_to_analyse(conn)

    # Generates the rule map 
    cursor = conn.cursor()
    cursor.execute("SELECT rule_id, name FROM AnalysisRule")
    rule_map = {name: rule_id for rule_id, name in cursor.fetchall()}

    conn.close()

    manager = multiprocessing.Manager()

    queue = manager.Queue()
    ext_counter_queue = manager.Queue()
    file_counter_queue = manager.Queue()

    writer_process = multiprocessing.Process(target=insert_data, args=(db_file, queue))
    writer_process.start()

    status_thread = threading.Thread(target=status_updater, args=(ext_counter_queue, file_counter_queue, len(extensions)))
    status_thread.start()

    cpu_count = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=cpu_count - 1) 

    for extension in extensions:
        pool.apply_async(analyse_extensions, args=(extract_path, extension[0], extension[1], rule_map, queue, ext_counter_queue, file_counter_queue))

    pool.close()
    pool.join()

    queue.put("FINISHED")
    writer_process.join()
    status_thread.join()

    # Formats and outputs execution time
    end_time = time.time()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    print(f"Execution time: {hours:02d}hrs, {minutes:02d}mins, {seconds:02d}secs")