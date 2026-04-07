import os
import sqlite3

# ---------- driver selection ----------
# If DATABASE_URL is set (Render Postgres), use psycopg2.
# Otherwise fall back to local SQLite for development.
DATABASE_URL = os.environ.get("DATABASE_URL")

def _get_pg_conn():
    """Return a psycopg2 connection using DATABASE_URL."""
    import psycopg2
    # Render gives postgres:// but psycopg2 needs postgresql://
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)

def _get_sqlite_conn():
    """Return an sqlite3 connection for local dev."""
    return sqlite3.connect("leads.db")

def get_connection():
    """Return the appropriate DB connection."""
    if DATABASE_URL:
        return _get_pg_conn()
    return _get_sqlite_conn()

# ---------- schema ----------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    if DATABASE_URL:
        # PostgreSQL syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                name TEXT,
                phone TEXT,
                city TEXT,
                electricity_bill TEXT,
                house_type TEXT,
                interested TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                city TEXT,
                electricity_bill TEXT,
                house_type TEXT,
                interested TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    conn.commit()
    conn.close()

# ---------- operations ----------
def save_lead(lead_data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    placeholder = "%s" if DATABASE_URL else "?"

    cursor.execute(f'''
        INSERT INTO leads (name, phone, city, electricity_bill, house_type, interested)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    ''', (
        lead_data.get("Name", ""),
        lead_data.get("Phone", ""),
        lead_data.get("City", ""),
        lead_data.get("Electricity bill", ""),
        lead_data.get("House type", ""),
        str(lead_data.get("Interested", ""))
    ))
    conn.commit()
    conn.close()

# Initialize the db when module loads
init_db()
