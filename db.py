import sqlite3

conn = sqlite3.connect('customers.db')

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

cursor.execute("""
INSERT OR IGNORE INTO customers (id, name, email, status)
VALUES
(1, 'Fares', 'fares@example.com', 'active'),
(2, 'Ali', 'ali@example.com', 'inactive')
""")


conn.commit()
conn.close()