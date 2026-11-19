import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "kbju_leads.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kbju_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            gender TEXT,
            age INTEGER,
            weight REAL,
            height REAL,
            activity TEXT,
            goal TEXT,
            calories INTEGER,
            protein INTEGER,
            fats INTEGER,
            carbs INTEGER,
            symptoms TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_profile(data: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO kbju_profiles (user_id, username, gender, age, weight, height, activity, goal, calories, protein, fats, carbs, symptoms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("user_id"),
        data.get("username", ""),
        data.get("gender"),
        data.get("age"),
        data.get("weight"),
        data.get("height"),
        data.get("activity"),
        data.get("goal"),
        data.get("calories"),
        data.get("protein"),
        data.get("fats"),
        data.get("carbs"),
        data.get("symptoms", "")
    ))
    conn.commit()
    conn.close()
