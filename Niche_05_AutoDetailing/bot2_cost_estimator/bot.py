import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_CAR_ESTIMATOR")
DB_PATH = os.path.join(os.path.dirname(__file__), "estimator_leads.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cost_estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            car_class TEXT,
            service_choice TEXT,
            estimated_price INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class CalcFSM(StatesGroup):
    car_class = State()
    service = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Седан / Купе (C/E класс)", callback_data="c_sedan")],
        [InlineKeyboardButton(text="🚙 Кроссовер (RAV4, Macan, X3)", callback_data="c_crossover")],
        [InlineKeyboardButton(text="🚐 Большой внедорожник (Range Rover, LC300)", callback_data="c_suv")]
    ])
    text = (
        f"⚡ <b>ИИ-Калькулятор стоимости детейлинга и защиты ЛКП</b>

"
        f"Рассчитайте точную смету за 30 секунд без визита в сервис.

"
        f"Выберите класс вашего автомобиля:"
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(CalcFSM.car_class)

@dp.callback_query(F.data.startswith("c_"))
async def cb_car(call: types.CallbackQuery, state: FSMContext):
    classes = {"c_sedan": ("Седан / Купе", 1.0), "c_crossover": ("Кроссовер", 1.2), "c_suv": ("Внедорожник", 1.4)}
    c_name, c_mult = classes.get(call.data, ("Седан", 1.0))
    await state.update_data(car_class=c_name, mult=c_mult, user_id=call.from_user.id, username=call.from_user.username or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Абразивная полировка + 2 слоя керамики", callback_data="svc_ceramic")],
        [InlineKeyboardButton(text="2. Оклейка полиуретаном зон риска (капот, фары, бампер)", callback_data="svc_front")],
        [InlineKeyboardButton(text="3. Полная оклейка всего кузова в глянец/мат", callback_data="svc_fullwrap")]
    ])
    await call.message.edit_text(f"Класс: <b>{c_name}</b>

Выберите желаемую услугу для расчета:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(CalcFSM.service)

@dp.callback_query(F.data.startswith("svc_"))
async def cb_svc(call: types.CallbackQuery, state: FSMContext):
    base_prices = {
        "svc_ceramic": ("Полировка + Керамика 9H", 35000),
        "svc_front": ("Бронирование зон риска", 65000),
        "svc_fullwrap": ("Полная оклейка полиуретаном", 185000)
    }
    svc_name, base_cost = base_prices.get(call.data, ("Полировка", 35000))
    data = await state.get_data()
    total_cost = round(base_cost * data["mult"])
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO cost_estimates (user_id, username, car_class, service_choice, estimated_price) VALUES (?, ?, ?, ?, ?)",
                (data["user_id"], data["username"], data["car_class"], svc_name, total_cost))
    conn.commit()
    conn.close()
    
    res = (
        f"📋 <b>ПРЕДВАРИТЕЛЬНАЯ СМЕТА ДЕТЕЙЛИНГА:</b>

"
        f"• <b>Класс авто:</b> {data['car_class']}
"
        f"• <b>Комплекс:</b> {svc_name}

"
        f"💰 <b>РАСЧЕТНАЯ СТОИМОСТЬ:</b> <code>{total_cost:,.0f} ₽</code>
"
        f"⏱ <i>Срок выполнения: 2-3 дня. Гарантия на работы: 3 года.</i>

"
        f"🎁 <b>Бонус:</b> Антидождь на лобовое стекло и гидрофоб бесплатно при бронировании сегодня."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏎 Зафиксировать смету и получить бонус", url="https://t.me/idrisov_prod")]
    ])
    await call.message.edit_text(res, reply_markup=kb, parse_mode="HTML")
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Car Estimator Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
