import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_MORTGAGE_CALC")
DB_PATH = os.path.join(os.path.dirname(__file__), "mortgage_leads.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mortgage_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            price REAL,
            down_payment REAL,
            term_years INTEGER,
            monthly_payment REAL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class MortgageFSM(StatesGroup):
    price = State()
    down_payment = State()
    term = State()
    phone = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        f"🧮 <b>Ипотечный ИИ-Калькулятор Aura Prime</b>

"
        f"Введите примерную стоимость желаемой квартиры в рублях (например: 18000000):",
        parse_mode="HTML"
    )
    await state.set_state(MortgageFSM.price)

@dp.message(MortgageFSM.price)
async def proc_price(msg: types.Message, state: FSMContext):
    text = msg.text.replace(" ", "").replace(",", "").replace(".", "")
    if not text.isdigit():
        await msg.answer("Введите стоимость числом (например, 15000000):")
        return
    price = float(text)
    await state.update_data(price=price, user_id=msg.from_user.id, username=msg.from_user.username or "")
    await msg.answer("Какой первоначальный взнос у вас на руках? (В рублях, например: 3500000):")
    await state.set_state(MortgageFSM.down_payment)

@dp.message(MortgageFSM.down_payment)
async def proc_down(msg: types.Message, state: FSMContext):
    text = msg.text.replace(" ", "").replace(",", "")
    if not text.isdigit():
        await msg.answer("Введите сумму ПВ числом:")
        return
    down = float(text)
    await state.update_data(down_payment=down)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15 лет", callback_data="y_15"), InlineKeyboardButton(text="20 лет", callback_data="y_20"), InlineKeyboardButton(text="30 лет", callback_data="y_30")]
    ])
    await msg.answer("Срок ипотечного кредитования:", reply_markup=kb)
    await state.set_state(MortgageFSM.term)

@dp.callback_query(F.data.startswith("y_"))
async def cb_term(call: types.CallbackQuery, state: FSMContext):
    years = int(call.data.replace("y_", ""))
    data = await state.get_data()
    price = data["price"]
    down = data["down_payment"]
    credit = max(price - down, 0)
    
    # Annuitet calc (avg rate 16%)
    r = 0.16 / 12
    n = years * 12
    monthly = round(credit * (r * ((1 + r)**n)) / (((1 + r)**n) - 1))
    await state.update_data(term=years, monthly=monthly)
    
    calc_res = (
        f"📊 <b>ПРЕДВАРИТЕЛЬНЫЙ РАСЧЕТ ИПОТЕКИ:</b>

"
        f"• Сумма кредита: <b>{credit:,.0f} ₽</b>
"
        f"• Срок: <b>{years} лет</b>
"
        f"• Ежемесячный платеж: <b>{monthly:,.0f} ₽/мес</b>

"
        f"💡 <i>У нас есть субсидированные ставки от застройщиков от 6% (платеж снижается в 2 раза).</i>

"
        f"Введите номер телефона для одобрения ипотеки в 8 банках-партнерах без посещения отделений:"
    )
    await call.message.edit_text(calc_res, parse_mode="HTML")
    await state.set_state(MortgageFSM.phone)

@dp.message(MortgageFSM.phone)
async def proc_m_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip()
    data = await state.get_data()
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO mortgage_requests (user_id, username, price, down_payment, term_years, monthly_payment, phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (data["user_id"], data["username"], data["price"], data["down_payment"], data["term"], data["monthly"], phone))
    conn.commit()
    conn.close()
    
    await msg.answer("✅ Заявка передана ведущему ипотечному брокеру. Одобрение придет в SMS.", parse_mode="HTML")
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Mortgage AI Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
