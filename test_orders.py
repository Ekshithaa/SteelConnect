# test_orders.py
import sqlite3
conn = sqlite3.connect("steelconnect.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM orders")
print(cursor.fetchall())
conn.close()