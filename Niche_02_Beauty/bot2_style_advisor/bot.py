import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_BEAUTY_ADVISOR")
DB_PATH = os.path.join(os.path.dirname(__file__), "style_quiz.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS style_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            face_shape TEXT,
            hair_type TEXT,
            recommendation TEXT,
            promo_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class StyleFSM(StatesGroup):
    face = State()
    hair = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Квадратная / Мужественная", callback_data="f_square")],
        [InlineKeyboardButton(text="⏺ Круглая / Мягкие черты", callback_data="f_round")],
        [InlineKeyboardButton(text="📐 Овальная / Вытянутая", callback_data="f_oval")]
    ])
    text = (
        f"🧔 <b>ИИ-Стилист Atelier Velvet & Blade</b>

"
        f"Пройди тест за 60 секунд: бот подберет идеальную стрижку и бороду под геометрию твоего лица + подарит промокод -15% на первый визит.

"
        f"Какая форма лица ближе к твоей?"
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(StyleFSM.face)

@dp.callback_query(F.data.startswith("f_"))
async def cb_face(call: types.CallbackQuery, state: FSMContext):
    faces = {"f_square": "Квадратная", "f_round": "Круглая", "f_oval": "Овальная"}
    f_val = faces.get(call.data, "Овал")
    await state.update_data(face=f_val, user_id=call.from_user.id, username=call.from_user.username or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="〰️ Прямые и жесткие", callback_data="h_straight")],
        [InlineKeyboardButton(text="➰ Волнистые / Кудрявые", callback_data="h_curly")],
        [InlineKeyboardButton(text="🍂 Редкие / С залысинами", callback_data="h_thin")]
    ])
    await call.message.edit_text(f"Форма лица: <b>{f_val}</b>

Опишите тип и структуру волос:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(StyleFSM.hair)

@dp.callback_query(F.data.startswith("h_"))
async def cb_hair(call: types.CallbackQuery, state: FSMContext):
    hairs = {"h_straight": "Прямые и жесткие", "h_curly": "Волнистые", "h_thin": "Редкие"}
    h_val = hairs.get(call.data, "Прямые")
    data = await state.get_data()
    data["hair"] = h_val
    
    recomms = {
        "Квадратная": "Стрижка: Fade Crop или Side Part с пробором. Борода: короткая щетина с четкой окантовкой щек.",
        "Круглая": "Стрижка: Pompadour или Quiff с объемом сверху для визуального вытягивания лица. Борода: удлиненная клиновидная эспаньолка.",
        "Овальная": "Стрижка: Классический Slick Back или Undercut. Подходит практически любая форма бороды."
    }
    rec = recomms.get(data["face"], "Универсальный Fade")
    promo = "VELVET15"
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO style_leads (user_id, username, face_shape, hair_type, recommendation, promo_code) VALUES (?, ?, ?, ?, ?, ?)",
                (data["user_id"], data["username"], data["face"], h_val, rec, promo))
    conn.commit()
    conn.close()
    
    res_text = (
        f"🎯 <b>ВАШ ПЕРСОНАЛЬНЫЙ СТИЛЬ-ОТЧЕТ:</b>

"
        f"• <b>Рекомендованный образ:</b> {rec}
"
        f"• <b>Стайлинг:</b> Матовая глина с морской солью для текстуры.

"
        f"🎁 <b>ВАШ ПРОМОКОД НА СКИДКУ 15%:</b> <code>{promo}</code>
"
        f"<i>Покажите промокод мастеру на ресепшн при оплате.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💈 Записаться к топ-мастеру со скидкой", url="https://t.me/idrisov_prod")]
    ])
    await call.message.edit_text(res_text, reply_markup=kb, parse_mode="HTML")
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Beauty Style Advisor Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
