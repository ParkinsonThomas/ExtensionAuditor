import sqlite3
import os
import re
import json
import time
from llama_cpp import Llama

#from openai import OpenAI

#client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

llm = Llama(model_path="/home/thomas/UoA_Diss/llama.cpp/build/codellama-7b.Q4_K_M.gguf", n_ctx=2048)

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

#def split_file(js_file):
#    chunk_size = 100000
#    return [js_file[i:i+chunk_size] for i in range(0, len(js_file), chunk_size)]

#def analyse_js_files(js_files):
#    start_time = time.time()
#    
#    for js_file in js_files:
#        with open(js_file, "r", encoding="utf-8") as file:
#            content = file.read()
#
#        chunks = split_file(content)
#        print(f"Querying DeepSeek API: {js_file}")
#        for chunk in chunks:
#            prompt = f"""Please analyse this JavaScript file for security issues e.g. hardcoded API keys, passwords or sensitive data. 
#                Return only security issues, with the line number it occurs on. If no security issues present, simply return "No security issues".
#                
#                File: {chunk}
#                """
#            try:
#                response = client.chat.completions.create(
#                    model="deepseek-chat",
#                    messages=[{"role": "user", "content": prompt}],
#                    stream=False
#                )
#                raw_answer = response.choices[0].message.content.strip()
#                print(raw_answer)
#
#            except Exception as e:
#                print(f"Error querying DeepSeek API: {e}")
#        print("")
#    total_time = round(time.time() - start_time, 2)
#    print(f"Time taken: {total_time}")
#    return

def scan_js_files(js_files):
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

def main(config):
    db_file = config["database"]["db"]
    extract_path = config["storage"]["extract_path"]


    conn = init_db_connection(db_file)
    extensions = get_extensions_to_analyse(conn)

    guid = "befflofjcniongenjmbkgkoljhgliihe"
    file_path = os.path.join(extract_path, guid)
    js_files = collect_js_files(file_path)
    
    scan_js_files(js_files)