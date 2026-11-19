import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "barber_booking.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            client_name TEXT,
            phone TEXT,
            barber TEXT,
            service TEXT,
            slot TEXT,
            status TEXT DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_booking(data: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings (user_id, username, client_name, phone, barber, service, slot)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("user_id"),
        data.get("username", ""),
        data.get("client_name", ""),
        data.get("phone", ""),
        data.get("barber", "Топ-барбер"),
        data.get("service", "Мужская стрижка"),
        data.get("slot", "Сегодня")
    ))
    conn.commit()
    conn.close()
