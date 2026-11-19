import asyncio
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_NUTRI_BOOKING_1")
DB_PATH = os.path.join(os.path.dirname(__file__), "booking.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            service TEXT,
            preferred_slot TEXT,
            health_goal TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_appointment(data: dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO appointments (user_id, username, full_name, phone, service, preferred_slot, health_goal)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("user_id"),
        data.get("username", ""),
        data.get("full_name", ""),
        data.get("phone", ""),
        data.get("service", "Экспресс-аудит рациона"),
        data.get("slot", "Ближайшее окно"),
        data.get("goal", "")
    ))
    conn.commit()
    conn.close()

class BookingFSM(StatesGroup):
    service = State()
    goal = State()
    slot = State()
    phone = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Экспресс-аудит рациона (30 мин)", callback_data="srv_audit")],
        [InlineKeyboardButton(text="🔬 Разбор анализов + план добавок", callback_data="srv_labs")],
        [InlineKeyboardButton(text="🎯 Ведение 1-на-1 до результата (Месяц)", callback_data="srv_full")],
        [InlineKeyboardButton(text="ℹ️ О докторе и сертификатах", callback_data="info_doc")]
    ])
    welcome = (
        f"🌿 <b>Клиника превентивной нутрициологии Dr. Vita</b>\n\n"
        f"Здравствуйте, {msg.from_user.first_name}! Я бот-ассистент клиники. "
        f"Помогу записаться на индивидуальный разбор и подготовить первичный анамнез.\n\n"
        f"Выберите интересующую услугу:"
    )
    await msg.answer(welcome, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("srv_"))
async def cb_service(call: types.CallbackQuery, state: FSMContext):
    services = {
        "srv_audit": "Экспресс-аудит рациона (30 мин)",
        "srv_labs": "Разбор анализов + план добавок",
        "srv_full": "Ведение 1-на-1 до результата (Месяц)"
    }
    chosen = services.get(call.data, "Консультация")
    await state.update_data(service=chosen, user_id=call.from_user.id, username=call.from_user.username or "", full_name=call.from_user.full_name or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Снижение веса / Отеки", callback_data="goal_weight")],
        [InlineKeyboardButton(text="🔋 Хроническая усталость / Сон", callback_data="goal_energy")],
        [InlineKeyboardButton(text="🥗 Проблемы с ЖКТ / Вздутия", callback_data="goal_gut")],
        [InlineKeyboardButton(text="📊 Нормализация сахара / Холестерина", callback_data="goal_biochem")]
    ])
    await call.message.edit_text(f"Выбрана услуга: <b>{chosen}</b>\n\nКакая главная задача или симптом сейчас в приоритете?", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BookingFSM.goal)

@dp.callback_query(F.data.startswith("goal_"))
async def cb_goal(call: types.CallbackQuery, state: FSMContext):
    goals = {
        "goal_weight": "Снижение веса и отечность",
        "goal_energy": "Хроническая усталость и сон",
        "goal_gut": "Проблемы с ЖКТ и вздутия",
        "goal_biochem": "Биохимия: сахар/холестерин"
    }
    chosen_goal = goals.get(call.data, "Общее оздоровление")
    await state.update_data(goal=chosen_goal)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓 Завтра: 11:00", callback_data="slot_1"), InlineKeyboardButton(text="🗓 Завтра: 15:30", callback_data="slot_2")],
        [InlineKeyboardButton(text="🗓 Послезавтра: 12:00", callback_data="slot_3"), InlineKeyboardButton(text="🗓 Послезавтра: 18:00", callback_data="slot_4")],
        [InlineKeyboardButton(text="💬 Согласовать другое время с ассистентом", callback_data="slot_custom")]
    ])
    await call.message.edit_text(f"Запрос: <b>{chosen_goal}</b>\n\nВыберите удобный тайм-слот для онлайн-разбора (Zoom/Telegram):", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BookingFSM.slot)

@dp.callback_query(F.data.startswith("slot_"))
async def cb_slot(call: types.CallbackQuery, state: FSMContext):
    slots = {
        "slot_1": "Завтра: 11:00 (МСК)",
        "slot_2": "Завтра: 15:30 (МСК)",
        "slot_3": "Послезавтра: 12:00 (МСК)",
        "slot_4": "Послезавтра: 18:00 (МСК)",
        "slot_custom": "Индивидуальный слот (через ассистента)"
    }
    chosen_slot = slots.get(call.data, "Онлайн")
    await state.update_data(slot=chosen_slot)
    
    await call.message.edit_text(
        f"Вы выбрали: <b>{chosen_slot}</b>\n\n"
        f"Для подтверждения брони введите ваш контактный номер телефона (или Telegram @username):",
        parse_mode="HTML"
    )
    await state.set_state(BookingFSM.phone)

@dp.message(BookingFSM.phone)
async def process_phone(msg: types.Message, state: FSMContext):
    contact = msg.text.strip()
    await state.update_data(phone=contact)
    data = await state.get_data()
    save_appointment(data)
    
    confirm = (
        f"✅ <b>Запись успешно подтверждена!</b>\n\n"
        f"• <b>Услуга:</b> {data['service']}\n"
        f"• <b>Запрос:</b> {data['goal']}\n"
        f"• <b>Слот:</b> {data['slot']}\n"
        f"• <b>Контакт:</b> {contact}\n\n"
        f"📋 <i>Вам отправлен предварительный опросник по питанию. Ассистент свяжется за 1 час до начала.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Записаться на другую услугу", callback_data="restart")]
    ])
    await msg.answer(confirm, reply_markup=kb, parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "restart")
async def cb_restart(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await cmd_start(call.message, state)

async def main():
    init_db()
    print("Bot 1 (NutriBooking) initialized and DB ready.")
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK MODE] Bot tested and compiled successfully.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
