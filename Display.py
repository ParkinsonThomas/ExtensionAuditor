import sqlite3

# Initialises and returns database connection
def init_db_connection(db_file):
    return sqlite3.connect(db_file)

# Retrieves all extensions in database
def get_extensions(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT extension_id, extension_guid FROM Extension")
    return cursor.fetchall()

# Retrieves all apis in database
def get_apis(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT api_url FROM API")
    return cursor.fetchall()

# Retrieves information on extension secrets from the database
def get_extension_secrets(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM ExtensionSecrets")
    numEntries = cursor.fetchall()

    extensions = set()  # Set used to get the number of extensions
    cursor.execute("SELECT extension_id FROM ExtensionSecrets")
    numExtensions = cursor.fetchall()
    
    for i in range(len(numExtensions)):
        extensions.add(numExtensions[i])

    return(numEntries, extensions)

def get_extension_dangerous_patterns(conn):
    """
    Collects information on dangerous patterns found in JavaScript files of Chrome Extensions.

    Parameters:
    conn (sqlite3.Connection): Database connection.

    Returns:
    tuple: (number of secret entries, set of extension_ids, set of files).
    """
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

def get_detailed_dangerous_patterns(conn, total_extensions):
    """
    Collects information based on the severity of the pattern.
    Processes information and calls "print_detailed_dangerous_pattern" to display.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    total_extensions (int): Total number of extensions in the database.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT rule_id, name, severity FROM AnalysisRule")
    analysis_rules = cursor.fetchall()

    low_rules = []
    med_rules = []
    high_rules = []
    crit_rules = []

    for rule in analysis_rules:
        if rule[2] == "Low":
            low_rules.append(rule)
        if rule[2] == "Medium":
            med_rules.append(rule)
        if rule[2] == "High":
            high_rules.append(rule)
        if rule[2] == "Critical":
            crit_rules.append(rule)

    print_detailed_dangerous_patterns(conn, low_rules, total_extensions)
    print_detailed_dangerous_patterns(conn, med_rules, total_extensions)
    print_detailed_dangerous_patterns(conn, high_rules, total_extensions)
    print_detailed_dangerous_patterns(conn, crit_rules, total_extensions)

def print_detailed_dangerous_patterns(conn, rules, total_extensions):
    """
    Prints stats for each dangerous pattern severity group.

    Parameters
    conn (sqlite3.Connection): Database connection.
    rules (list[tuple]): List of analysis rules.
    total_extensions (int): Total number of extensions.
    """

    print(
    f"""
    {rules[0][2]} Severity Patterns"""
    )
    total_count = [0, 0, 0]     # [count, extensions, files]

    cursor = conn.cursor()
    for rule in rules:

        count = 0
        cursor = conn.cursor()
        cursor.execute("SELECT count FROM ExtensionAnalysisJS WHERE rule_id = ?", (rule[0],))
        count_array = cursor.fetchall()
        
        for i in range(len(count_array)):
            count += count_array[i][0]
        total_count[0] += count

        extensions = set()
        cursor.execute("SELECT extension_id FROM ExtensionAnalysisJS WHERE rule_id = ?", (rule[0],))
        numExtensions = cursor.fetchall()
        for i in range(len(numExtensions)):
            extensions.add(numExtensions[i])
        total_count[1] += len(extensions)

        file_num = set()
        cursor.execute("SELECT file_name FROM ExtensionAnalysisJS WHERE rule_id = ?", (rule[0],))
        files = cursor.fetchall()
        for i in range(len(files)):
            file_num.add(files[i])
        total_count[2] += len(file_num)

        percentage = round((len(extensions)/total_extensions)*100, 2)

        print(f"""
    {rule[1]}
    Found {count} matches in {len(file_num)} files, in {len(extensions)} extensions.
    {percentage}% of extensions."""
        )

def database_stats(conn):
    """
    Prints overall database stats.

    Parameters:
    conn (sqlite3.Connection): Database connection.
    """

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

    get_detailed_dangerous_patterns(conn, len(extensions))

def main(config):
    """
    Main function to initialise database connection and display stats.

    Parameters:
    config: Configuration settings (used for database).
    """

    # Retrieve necessary information from the configuration file
    db_file = config["database"]["db"]

    # Initialise database connection
    conn = init_db_connection(db_file)
    database_stats(conn)
    conn.close()