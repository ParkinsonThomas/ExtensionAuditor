import sqlite3
import requests
import json
import os
import zipfile

db_file = "ExtensionDB.db"
extension_webstore_url = "https://chrome.google.com/webstore/detail/"

def init_db_connection():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    return conn

# def download_extension(extension_name)