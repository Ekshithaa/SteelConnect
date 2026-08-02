import sqlite3
conn = sqlite3.connect("steelconnect.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM products")
rows = cursor.fetchall()
print(rows)
conn.close()