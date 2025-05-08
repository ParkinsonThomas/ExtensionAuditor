import sqlite3
import os
import re
import json
import time
import sys
import subprocess
import multiprocessing
import threading

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

# Retrieves all extensions from the database and returns a list of tuples (extension_id, extension_guid)
def get_extensions_to_analyse(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def analyse_files(queue, extract_path, guid, extension_id, entropy_filter, counter_queue):
    """
    Runs Gitleaks on an extracted Chrome extension and parses results.
    Inserts secrets with entropy above a certain threshold into the database.

    Parameters:
    queue (multiprocessing.Queue): Queue to store findings.
    extract_path (str): Directory for extracted extension.
    guid (str): Chrome Extension GUID.
    extension_id (int): Extension ID.
    entropy_filter (float): Minimum entropy threshold for filtering findings.
    counter_queue (multiprocessing.Queue): Queue to store success/failure status.
    """

    gitleaks_path = "gitleaks"
    success = False

    try:
        extension_dir = os.path.join(extract_path, guid)

        # Initialises variables to None, not typical in Python however it is used for logic checks later on
        secret, rule_id, entropy, file_name, line_num = None, None, None, None, None

        # Runs Gitleaks
        result = subprocess.run(
        [
            gitleaks_path,
            "detect",
            "--source", extension_dir,
            "--verbose",                # Prevents output to console
            "--no-git",                 # specifies that its not a Git repo (Gitleaks is traditionally used for scanning Git repos)
            "--report-format", "json"   # Ensures response is in JSON, for parsing later
        ],
        capture_output=True,
        text=True,
        timeout=180
        )

        # Used to store results, then added to the queue
        findings = []

        if result.stdout:
            # Parses output
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

                # Once all variables have been assigned data, insert_data is called
                if all(var is not None for var in [secret, rule_id, entropy, file_name, line_num]):
                    if entropy > entropy_filter:
                        findings.append((extension_id, file_name, line_num, rule_id, secret, entropy))
                    
                    # Reset variables to None
                    secret, rule_id, entropy, file_name, line_num = None, None, None, None, None
        success = True
        queue.put(findings)
        
    except subprocess.TimeoutExpired:
        queue.put([])     # No findings - ensures status_updater remains correct in cases of error
        success = False

    except subprocess.CalledProcessError:
        success = False
        queue.put([])
    
    finally:
        counter_queue.put("success" if success else "fail")
    
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
        for (extension_id, file_name, line_num, rule_id, secret, entropy) in findings:
            cursor.execute("""
                INSERT INTO ExtensionSecrets (extension_id, file_name, line, rule_id, secret, entropy)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (extension_id, file_name, line_num, rule_id, secret, entropy)
            )
        conn.commit()
    

def status_updater(counter_queue, num_extensions):
    """
    Updates console in real-time to tell the user how many extensions (successfully and unsuccesfully) have been analysed.

    Parameters:
    counter_queue (multiprocessing.Queue): Queue with success/failure statuses.
    num_extensions (int): Total number of extensions.
    """

    # Counts
    success_count = 0
    fail_count = 0
    processed = 0

    # Prints two lines to be used in formatting later
    print("Extensions analysed successfully:")
    print("Extensions analysed unsuccessfully:")

    while processed < num_extensions:
        status = counter_queue.get()
        if status == "success":
            success_count += 1
        else:
            fail_count += 1
        processed += 1

        sys.stdout.write("\033[F\033[K" * 2)  # Move up two lines and clear
        sys.stdout.write(f"Extensions analysed successfully:    {success_count}\n")
        sys.stdout.write(f"Extensions analysed unsuccessfully:  {fail_count}\n")
        sys.stdout.flush()

def main(config):
    """
    Main entry point for the Extension Secrets analysis pipeline.

    Parameters:
    config: Configuration settings (used for database and directories).
    """
    # Start time
    start_time = time.time()

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]
    
    # If entropy filtering enabled, retrieve minimum entropy, if not then set minimum entropy to 0
    entropy_enabled = config["entropy_filtering"]["enabled"]
    if entropy_enabled == True:
        entropy_filter = config["entropy_filtering"]["entropy_filter"]
    else:
        entropy_filter = 0

    # Initialise database connection and retrieve extensions to analyse
    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)
    conn.close()

    manager = multiprocessing.Manager()

    queue = manager.Queue()
    counter_queue = manager.Queue()

    writer_process = multiprocessing.Process(target=insert_data, args=(db_file, queue))
    writer_process.start()

    status_thread = threading.Thread(target=status_updater, args=(counter_queue, len(extensions)))
    status_thread.start()


    cpu_count = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=cpu_count - 1) 

    for extension in extensions:
        pool.apply_async(analyse_files, args=(queue, extract_path, extension[1], extension[0], entropy_filter, counter_queue))

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

    conn.close()