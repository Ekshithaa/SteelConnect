import sqlite3
conn = sqlite3.connect("steelconnect.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(products)")
print(cursor.fetchall())
conn.close()