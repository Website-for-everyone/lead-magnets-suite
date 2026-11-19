import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_EXAM_QUIZ")
DB_PATH = os.path.join(os.path.dirname(__file__), "quiz_leads.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            score INTEGER,
            weak_spot TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class QuizFSM(StatesGroup):
    q1 = State()
    q2 = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A) O(N)", callback_data="ans_1_a")],
        [InlineKeyboardButton(text="B) O(log N)", callback_data="ans_1_b")],
        [InlineKeyboardButton(text="C) O(N log N)", callback_data="ans_1_c")]
    ])
    text = (
        f"📝 <b>Интеллектуальный экспресс-тест ЕГЭ по Информатике</b>

"
        f"Вопрос 1 из 2:
"
        f"Какова асимптотическая сложность бинарного поиска в отсортированном массиве?"
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(QuizFSM.q1)

@dp.callback_query(F.data.startswith("ans_1_"))
async def cb_q1(call: types.CallbackQuery, state: FSMContext):
    is_correct = (call.data == "ans_1_b")
    await state.update_data(score=50 if is_correct else 0, user_id=call.from_user.id, username=call.from_user.username or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A) [x for x in lst if x % 2 == 0]", callback_data="ans_2_a")],
        [InlineKeyboardButton(text="B) lst.filter(lambda x: x%2)", callback_data="ans_2_b")]
    ])
    await call.message.edit_text("Вопрос 2 из 2:
Какой синтаксис Python корректно фильтрует четные числа в List Comprehension?", reply_markup=kb)
    await state.set_state(QuizFSM.q2)

@dp.callback_query(F.data.startswith("ans_2_"))
async def cb_q2(call: types.CallbackQuery, state: FSMContext):
    is_correct = (call.data == "ans_2_a")
    data = await state.get_data()
    final_score = data["score"] + (50 if is_correct else 0)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO exam_scores (user_id, username, score, weak_spot) VALUES (?, ?, ?, ?)",
                (data["user_id"], data["username"], final_score, "Сложность алгоритмов" if final_score < 100 else "Отличный уровень"))
    conn.commit()
    conn.close()
    
    res = (
        f"📊 <b>ВАШ РЕЗУЛЬТАТ ТЕСТИРОВАНИЯ: {final_score}/100 БАЛЛОВ</b>

"
        f"• Рекомендация: Повторить структуры данных и оптимизацию задач №24 и №27.

"
        f"🎁 <i>Вам открыт доступ к закрытому конспекту со всеми формулами ЕГЭ-2026.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Забрать PDF-шпаргалку по формулам", url="https://t.me/idrisov_prod")]
    ])
    await call.message.edit_text(res, reply_markup=kb, parse_mode="HTML")
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Exam Quiz Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
