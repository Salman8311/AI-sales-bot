import sqlite3
import json
import os

DB_FILE = "leads.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
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

def save_lead(lead_data: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO leads (name, phone, city, electricity_bill, house_type, interested)
        VALUES (?, ?, ?, ?, ?, ?)
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

# Initialize the db when modulo loads
init_db()
