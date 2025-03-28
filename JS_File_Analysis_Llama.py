import sqlite3
import os
import re
import json
import time
from llama_cpp import Llama

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
                print("Here")
                js_files.append(os.path.join(root, file))
    return js_files

def scan_js_files(js_files, llm):
    start_time = time.time()
    for js_file in js_files:
        print(f"Querying Llama LLM for file: {js_file}")
        with open(js_file, "r", encoding="utf-8") as file:
            js_code = file.read()
    
        prompt = f"""Please analyse this JavaScript file for security issues e.g. hardcoded API keys, passwords or sensitive data. 
                Return only security issues, with the line number it occurs on. If no security issues present, simply return "No security issues".
                
                File: {js_code}
                """
        
        response = llm(prompt, max_tokens=1024)
        print(response["choices"][0]["text"])
        print("")
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Execution time: {elapsed_time:.6f} seconds")

def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]
    model_path = config["misc"]["model_path"]

    llm = Llama(model_path=model_path, n_ctx=2048)

    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)

    print("1")
    guid = "befflofjcniongenjmbkgkoljhgliihe"
    file_path = os.path.join(extract_path, guid)
    print("2")
    js_files = collect_js_files(file_path)
    print("3")
    print(js_files)
    print("4")
    scan_js_files(js_files, llm)