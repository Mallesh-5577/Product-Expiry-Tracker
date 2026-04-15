import sqlite3
import os

try:
    import psycopg2
except ImportError:
    psycopg2 = None

DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "product_expiry.db")
LEGACY_DB_PATH = os.path.join(BASE_DIR, "medicine_expiry.db")

if os.path.exists(DEFAULT_DB_PATH):
    DB_PATH = DEFAULT_DB_PATH
elif os.path.exists(LEGACY_DB_PATH):
    DB_PATH = LEGACY_DB_PATH
else:
    DB_PATH = DEFAULT_DB_PATH

if DATABASE_URL:
    if psycopg2 is None:
        raise RuntimeError(
            "DATABASE_URL is set but psycopg2 is not installed. Install requirements first."
        )

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            batch TEXT NOT NULL,
            expiry DATE NOT NULL,
            barcode TEXT NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Database tables created successfully in PostgreSQL")
    raise SystemExit(0)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cur.execute("PRAGMA table_info(users)")
user_columns = [row[1] for row in cur.fetchall()]
if "phone" not in user_columns:
    cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")

cur.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        batch TEXT NOT NULL,
        expiry TEXT NOT NULL,
        barcode TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")

conn.commit()
conn.close()
print("Database created successfully in SQLite")
