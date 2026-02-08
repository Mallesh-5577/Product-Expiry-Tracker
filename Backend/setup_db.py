import sqlite3

conn = sqlite3.connect("medicine_expiry.db")
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        batch TEXT NOT NULL,
        expiry TEXT NOT NULL,
        barcode TEXT NOT NULL,
        quantity INTEGER NOT NULL
    )
""")

conn.commit()
conn.close()
print("✓ Database created successfully!")
