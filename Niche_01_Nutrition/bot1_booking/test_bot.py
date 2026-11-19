import sqlite3
import os
from bot import init_db, save_appointment

def test_booking():
    init_db()
    test_data = {
        "user_id": 999111,
        "username": "test_patient",
        "full_name": "Анна Смирнова",
        "phone": "+79991112233",
        "service": "Экспресс-аудит рациона (30 мин)",
        "slot": "Завтра: 11:00 (МСК)",
        "goal": "Снижение веса и отечность"
    }
    save_appointment(test_data)
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "booking.db"))
    cur = conn.cursor()
    cur.execute("SELECT full_name, service, slot FROM appointments WHERE user_id = 999111")
    row = cur.fetchone()
    conn.close()
    assert row[0] == "Анна Смирнова"
    print("Bot 1 (NutriBooking) Unit Test PASSED!")

if __name__ == "__main__":
    test_booking()
