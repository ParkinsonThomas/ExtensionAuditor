import sqlite3

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

# Retrieves all extensions in database
def get_extensions(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

def get_apis(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT api_url FROM API")
    return cursor.fetchall()

def get_urls(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM URLs")
    return cursor.fetchall()

def get_extension_secrets(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM ExtensionSecrets")
    numEntries = cursor.fetchall()

    extensions = set()
    cursor.execute("SELECT extension_id FROM ExtensionSecrets")
    numExtensions = cursor.fetchall()
    
    for i in range(len(numExtensions)):
        extensions.add(numExtensions[i])

    return(numEntries, extensions)

def get_extension_dangerous_patterns(conn):
    count = 0
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM ExtensionAnalysisJS")
    count_array = cursor.fetchall()
    
    for i in range(len(count_array)):
        count += count_array[i][0]
    
    extensions = set()
    cursor.execute("SELECT extension_id FROM ExtensionAnalysisJS")
    numExtensions = cursor.fetchall()
    for i in range(len(numExtensions)):
        extensions.add(numExtensions[i])

    file_num = set()
    cursor.execute("SELECT file_name FROM ExtensionAnalysisJS")
    files = cursor.fetchall()
    for i in range(len(files)):
        file_num.add(files[i])
    
    return(count, extensions, file_num)


def databaseStats(conn):
    extensions = get_extensions(conn)
    apis = get_apis(conn)
    extensionSecrets = get_extension_secrets(conn)
    dangerousPatterns = get_extension_dangerous_patterns(conn)

    percentage_secrets = round((len(extensionSecrets[1])/len(extensions))*100, 2)
    percentage_patterns = round((len(dangerousPatterns[1])/len(extensions))*100, 2)

    print(
    f"""
    Database Statistics...

    Basic Stats
    Extensions: {len(extensions)}
    APIs: {len(apis)}

    Extension Secrets
    Found {len(extensionSecrets[0])} secrets in {len(extensionSecrets[1])} extensions
    {percentage_secrets}% of extensions

    Dangerous Patterns
    Found {dangerousPatterns[0]} dangerous patterns in {len(dangerousPatterns[2])} files, in {len(dangerousPatterns[1])} extensions.
    {percentage_patterns}% of extensions"""
    )


def main(config):
    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]
    download_dir = config["storage"]["download_path"]
    extract_dir = config["storage"]["extract_path"]

    conn = init_db_connection(db_file)
    databaseStats(conn)
    conn.close()