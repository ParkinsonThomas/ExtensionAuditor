import sqlite3

def init_db_connection(db_file):
    return sqlite3.connect(db_file)

def wipe_db(conn):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Extension")
    cursor.execute("DELETE FROM API")
    cursor.execute("DELETE FROM ExtensionAPIs")
    cursor.execute("DELETE FROM URLs")

    conn.commit()

def main():
    conn = init_db_connection("ExtensionDB.db")
    wipe_db(conn)
    conn.close()

if __name__ == "__main__":
    main()