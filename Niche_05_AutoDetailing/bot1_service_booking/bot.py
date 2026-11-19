import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_DETAIL_BOOK")
DB_PATH = os.path.join(os.path.dirname(__file__), "detail_leads.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detailing_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            car_brand TEXT,
            package TEXT,
            date_slot TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class DetailFSM(StatesGroup):
    car = State()
    package = State()
    slot = State()
    phone = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    text = (
        f"🏎 <b>Obsidian Detailing Studio // Бронирование боксов</b>

"
        f"Привет, {msg.from_user.first_name}! Автоматический расчет стоимости и бронирование слота на полировку, керамику и оклейку авто.

"
        f"Напишите марку и модель вашего автомобиля (например: BMW X5 или Porsche Macan):"
    )
    await msg.answer(text, parse_mode="HTML")
    await state.set_state(DetailFSM.car)

@dp.message(DetailFSM.car)
async def proc_car(msg: types.Message, state: FSMContext):
    car = msg.text.strip()
    await state.update_data(car_brand=car, user_id=msg.from_user.id, username=msg.from_user.username or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Полная полировка кузова + 2 слоя керамики", callback_data="pkg_ceramic")],
        [InlineKeyboardButton(text="🛡 Оклейка антигравийной пленкой (Зоны риска)", callback_data="pkg_wrap")],
        [InlineKeyboardButton(text="✨ Детейлинг-химчистка салона с озонацией", callback_data="pkg_dry")]
    ])
    await msg.answer(f"Автомобиль: <b>{car}</b>

Выберите желаемый комплекс работ:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(DetailFSM.package)

@dp.callback_query(F.data.startswith("pkg_"))
async def cb_pkg(call: types.CallbackQuery, state: FSMContext):
    pkgs = {
        "pkg_ceramic": "Полировка + 2 слоя керамики",
        "pkg_wrap": "Оклейка бронепленкой (Зоны риска)",
        "pkg_dry": "Комплексная химчистка салона"
    }
    p = pkgs.get(call.data, "Детейлинг")
    await state.update_data(package=p)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓 Пятница: 10:00 (Бокс 1)", callback_data="sl_fri")],
        [InlineKeyboardButton(text="🗓 Суббота: 11:30 (Бокс 2)", callback_data="sl_sat")],
        [InlineKeyboardButton(text="🗓 Понедельник: 09:00", callback_data="sl_mon")]
    ])
    await call.message.edit_text(f"Комплекс: <b>{p}</b>

Выберите дату заезда в детейлинг-бокс:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(DetailFSM.slot)

@dp.callback_query(F.data.startswith("sl_"))
async def cb_slot(call: types.CallbackQuery, state: FSMContext):
    slots = {"sl_fri": "Пятница: 10:00", "sl_sat": "Суббота: 11:30", "sl_mon": "Понедельник: 09:00"}
    s = slots.get(call.data, "Слот")
    await state.update_data(slot=s)
    
    await call.message.edit_text(f"Слот: <b>{s}</b>

Введите номер телефона мастера-приемщика для подтверждения брони:", parse_mode="HTML")
    await state.set_state(DetailFSM.phone)

@dp.message(DetailFSM.phone)
async def proc_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip()
    data = await state.get_data()
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO detailing_bookings (user_id, username, car_brand, package, date_slot, phone) VALUES (?, ?, ?, ?, ?, ?)",
                (data["user_id"], data["username"], data["car_brand"], data["package"], data["slot"], phone))
    conn.commit()
    conn.close()
    
    await msg.answer(
        f"✅ <b>ДЕТЕЙЛИНГ-БОКС УСПЕШНО ЗАБРОНИРОВАН!</b>

"
        f"• Авто: {data['car_brand']}
"
        f"• Услуга: {data['package']}
"
        f"• Дата заезда: {data['slot']}

"
        f"Мастер-приемщик свяжется для подтверждения. Мойка кузова перед осмотром — в подарок.",
        parse_mode="HTML"
    )
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Detailing Booking Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
