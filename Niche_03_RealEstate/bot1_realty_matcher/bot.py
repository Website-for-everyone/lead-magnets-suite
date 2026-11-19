import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_REALTY_MATCH")
DB_PATH = os.path.join(os.path.dirname(__file__), "realty_leads.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS viewing_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            property_type TEXT,
            budget TEXT,
            rooms TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class RealtyFSM(StatesGroup):
    ptype = State()
    budget = State()
    rooms = State()
    phone = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙 Новостройки (Элит & Бизнес)", callback_data="p_new")],
        [InlineKeyboardButton(text="🏛 Вторичная недвижимость в центре", callback_data="p_second")],
        [InlineKeyboardButton(text="🌲 Загородные дома и виллы", callback_data="p_house")]
    ])
    text = (
        f"🏢 <b>Aura Prime Realty // Интеллектуальный подбор недвижимости</b>

"
        f"Здравствуйте, {msg.from_user.first_name}! Ответьте на 3 вопроса — бот сформирует персональную закрытую презентацию объектов с доходностью от 18% годовых.

"
        f"Какой сегмент недвижимости вас интересует?"
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(RealtyFSM.ptype)

@dp.callback_query(F.data.startswith("p_"))
async def cb_type(call: types.CallbackQuery, state: FSMContext):
    types_map = {"p_new": "Новостройки Бизнес/Премиум", "p_second": "Вторичка в центре", "p_house": "Загородные дома"}
    t = types_map.get(call.data, "Недвижимость")
    await state.update_data(ptype=t, user_id=call.from_user.id, username=call.from_user.username or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 До 15 млн ₽", callback_data="b_15")],
        [InlineKeyboardButton(text="💰 15 - 30 млн ₽", callback_data="b_30")],
        [InlineKeyboardButton(text="💎 30 - 60+ млн ₽", callback_data="b_60")]
    ])
    await call.message.edit_text(f"Сегмент: <b>{t}</b>

Планируемый бюджет покупки:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(RealtyFSM.budget)

@dp.callback_query(F.data.startswith("b_"))
async def cb_budget(call: types.CallbackQuery, state: FSMContext):
    budgets = {"b_15": "До 15 млн ₽", "b_30": "15 - 30 млн ₽", "b_60": "30 - 60+ млн ₽"}
    b = budgets.get(call.data, "Бюджет")
    await state.update_data(budget=b)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1-2 комнатная (или студия)", callback_data="r_12")],
        [InlineKeyboardButton(text="3-4 комнатная семейная", callback_data="r_34")],
        [InlineKeyboardButton(text="Пентхаус / Свободная планировка", callback_data="r_pent")]
    ])
    await call.message.edit_text(f"Бюджет: <b>{b}</b>

Желаемая комнатность:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(RealtyFSM.rooms)

@dp.callback_query(F.data.startswith("r_"))
async def cb_rooms(call: types.CallbackQuery, state: FSMContext):
    rms = {"r_12": "1-2 комнаты", "r_34": "3-4 комнатная", "r_pent": "Пентхаус"}
    r = rms.get(call.data, "Квартира")
    await state.update_data(rooms=r)
    
    await call.message.edit_text(
        f"✅ <b>Найдено 4 подходящих объекта в закрытой базе!</b>

"
        f"Введите ваш контактный номер телефона для отправки персональной PDF-презентации планировок в WhatsApp/Telegram:",
        parse_mode="HTML"
    )
    await state.set_state(RealtyFSM.phone)

@dp.message(RealtyFSM.phone)
async def proc_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip()
    data = await state.get_data()
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO viewing_leads (user_id, username, property_type, budget, rooms, phone) VALUES (?, ?, ?, ?, ?, ?)",
                (data["user_id"], data["username"], data["ptype"], data["budget"], data["rooms"], phone))
    conn.commit()
    conn.close()
    
    confirm = (
        f"🎯 <b>ЗАПРОС ПРИНЯТ БРОКЕРОМ!</b>

"
        f"• <b>Сегмент:</b> {data['ptype']}
"
        f"• <b>Бюджет:</b> {data['budget']}
"
        f"• <b>Комнатность:</b> {data['rooms']}
"
        f"• <b>Телефон:</b> {phone}

"
        f"📩 <i>Презентация с планировками формируется. Брокер свяжется с вами в течение 5 минут.</i>"
    )
    await msg.answer(confirm, parse_mode="HTML")
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Realty Matcher Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
