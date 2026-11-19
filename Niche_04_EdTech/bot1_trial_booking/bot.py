import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_TUTOR_BOOK")
DB_PATH = os.path.join(os.path.dirname(__file__), "tutor_leads.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trial_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            subject TEXT,
            target_grade TEXT,
            slot TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class TutorFSM(StatesGroup):
    subject = State()
    target = State()
    slot = State()
    phone = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💻 Информатика ЕГЭ (Python / Базы данных)", callback_data="sub_inf")],
        [InlineKeyboardButton(text="📐 Профильная Математика ЕГЭ (Параметры/Геометрия)", callback_data="sub_math")],
        [InlineKeyboardButton(text="🇬🇧 Английский язык (IELTS / Олимпиады)", callback_data="sub_eng")]
    ])
    text = (
        f"🎓 <b>Apex Academy // Запись на бесплатный вводный урок</b>

"
        f"Привет, {msg.from_user.first_name}! За 45 минут преподаватель оценит твой текущий уровень, "
        f"разберет 3 сложные темы и составит индивидуальную стратегию на 85+ баллов.

"
        f"Выбери предмет:"
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(TutorFSM.subject)

@dp.callback_query(F.data.startswith("sub_"))
async def cb_sub(call: types.CallbackQuery, state: FSMContext):
    subs = {"sub_inf": "Информатика ЕГЭ", "sub_math": "Профильная математика", "sub_eng": "Английский язык"}
    s = subs.get(call.data, "Предмет")
    await state.update_data(subject=s, user_id=call.from_user.id, username=call.from_user.username or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 80 - 90 баллов", callback_data="tg_80")],
        [InlineKeyboardButton(text="🔥 90 - 100 баллов (Бюджет ВШЭ / МФТИ)", callback_data="tg_90")],
        [InlineKeyboardButton(text="🛡 Уверенные 70+ баллов для поступления", callback_data="tg_70")]
    ])
    await call.message.edit_text(f"Предмет: <b>{s}</b>

Твоя целевая планка на экзамене:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(TutorFSM.target)

@dp.callback_query(F.data.startswith("tg_"))
async def cb_target(call: types.CallbackQuery, state: FSMContext):
    targets = {"tg_80": "80-90 баллов", "tg_90": "90-100 баллов", "tg_70": "70+ баллов"}
    t = targets.get(call.data, "Цель")
    await state.update_data(target=t)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓 Завтра в 17:00", callback_data="sl_1")],
        [InlineKeyboardButton(text="🗓 Завтра в 19:30", callback_data="sl_2")],
        [InlineKeyboardButton(text="🗓 Выходные в 13:00", callback_data="sl_3")]
    ])
    await call.message.edit_text(f"Цель: <b>{t}</b>

Выбери удобный слот для индивидуального созвона в Zoom/Discord:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(TutorFSM.slot)

@dp.callback_query(F.data.startswith("sl_"))
async def cb_slot(call: types.CallbackQuery, state: FSMContext):
    slots = {"sl_1": "Завтра в 17:00", "sl_2": "Завтра в 19:30", "sl_3": "Выходные в 13:00"}
    slot = slots.get(call.data, "Время")
    await state.update_data(slot=slot)
    
    await call.message.edit_text(f"Слот: <b>{slot}</b>

Введите номер телефона (или Telegram) для отправки ссылки на урок:", parse_mode="HTML")
    await state.set_state(TutorFSM.phone)

@dp.message(TutorFSM.phone)
async def proc_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip()
    data = await state.get_data()
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO trial_bookings (user_id, username, subject, target_grade, slot, phone) VALUES (?, ?, ?, ?, ?, ?)",
                (data["user_id"], data["username"], data["subject"], data["target"], data["slot"], phone))
    conn.commit()
    conn.close()
    
    await msg.answer(
        f"🚀 <b>Вводный урок успешно забронирован!</b>

"
        f"• Предмет: {data['subject']}
"
        f"• Время: {data['slot']}

"
        f"Ссылка на конференцию и рабочая тетрадь отправлены в этот чат.",
        parse_mode="HTML"
    )
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Tutor Booking Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
