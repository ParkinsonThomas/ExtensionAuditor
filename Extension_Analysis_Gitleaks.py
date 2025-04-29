import sqlite3
import os
import re
import json
import time
import sys
import subprocess

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

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

def analyse_files(conn, extract_path, guid, extension_id, entropy_filter):
    """
    Runs Gitleaks on an extracted Chrome extension and parses results.
    Inserts secrets with entropy above a certain threshold into the database.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    extract_path (str): Directory for extracted extension.
    guid (str): Chrome Extension GUID.
    extension_id (int): Extension ID.
    entropy_filter (float): Minimum entropy threshold for filtering findings.
    """

    gitleaks_path = "gitleaks" 
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
        )

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
                        insert_data(conn, extension_id, secret, rule_id, entropy, file_name, line_num)
                    
                    # Reset variables to None
                    secret, rule_id, entropy, file_name, line_num = None, None, None, None, None
        return True

    except subprocess.CalledProcessError as e:
        return False
    
def insert_data(conn, extension_id, secret, rule_id, entropy, file_name, line_num):
    """
    Creates an entry for a detected secret in the "ExtensionSecrets" table.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    extension_id (int): Extension ID.
    secret (str): The detected secret.
    rule_id (str): Gitleaks rule that was triggered.
    entropy (float): Entropy value of the detected secret.
    file_name (str): File where the secret was found.
    line_num (int): Line number where the secret was found.
    """

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ExtensionSecrets (extension_id, file_name, line, rule_id, secret, entropy)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (extension_id, file_name, line_num, rule_id, secret, entropy)
    )
    conn.commit()

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

    # Counts
    success_count = 0
    fail_count = 0

    # Prints two lines for formatting later
    print("Extensions analysed successfully:")
    print("Extensions analysed unsuccessfully:")

    # Iterates through extensions
    for extension in extensions:
        result = analyse_files(conn, extract_path, extension[1], extension[0], entropy_filter)
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        sys.stdout.write("\033[F\033[K" * 2)  # Move up and clear two lines
        sys.stdout.write(f"Extensions analysed successfully:    {success_count}\n")
        sys.stdout.write(f"Extensions analysed unsuccessfully:  {fail_count}\n")
        sys.stdout.flush()
        time.sleep(0.01)

    # Formats and outputs execution time
    end_time = time.time()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    print(f"Execution time: {hours:02d}hrs, {minutes:02d}mins, {seconds:02d}secs")

    conn.close()