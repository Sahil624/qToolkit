import sqlite3

def setup():
    # Connect to or create the database
    conn = sqlite3.connect('example.db')

    # Create a cursor
    cursor = conn.cursor()

    # Create a tablex
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS replay (
            id INTEGER PRIMARY KEY,
            nodeTraversal TEXT,
            ksuid CHAR(100) NOT NULL
        )
    ''')
    return conn

def insert(nodeTraversal, ksu_id):
    # Insert values into the table
    conn = setup()
    cursor = conn.cursor()
    # rows = fetchallRows()
    rows = select(ksu_id)
    if(len(rows) > 0):
        query = 'Update replay set nodeTraversal =?  where ksuid = ?'
        cursor.execute(query, (nodeTraversal, ksu_id))
    else:
        cursor.execute('INSERT INTO replay (nodeTraversal, ksuid) VALUES (?, ?)', (nodeTraversal, ksu_id))
    conn.commit()

    # Close the connection
    conn.close()


def select(ksu_id):
    conn = setup()
    cursor = conn.cursor()
    query = 'SELECT nodeTraversal FROM replay where ksuid =?'
    cursor.execute(query, [ksu_id])
    rows = cursor.fetchall()

    # Close the connection
    conn.close()
    return rows

def fetchallRows():
    conn = setup()
    cursor = conn.cursor()
    query = 'SELECT ksuid, nodeTraversal FROM replay'
    cursor.execute(query)
    rows = cursor.fetchall()
    print(rows)
    # Close the connection
    conn.close()
    return rows