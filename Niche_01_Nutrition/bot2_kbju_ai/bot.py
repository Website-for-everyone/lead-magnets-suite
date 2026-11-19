import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, save_profile
from calculator import calculate_kbju

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_NUTRISCAN_AI")

class KbjuFSM(StatesGroup):
    gender = State()
    age = State()
    weight = State()
    height = State()
    activity = State()
    goal = State()
    symptoms = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Мужчина", callback_data="g_male"), InlineKeyboardButton(text="👩 Женщина", callback_data="g_female")]
    ])
    text = (
        f"🔬 <b>NutriScan AI // Метаболический калькулятор и аудит дефицитов</b>\n\n"
        f"Привет, {msg.from_user.first_name}! За 4 шага бот рассчитает твой точный КБЖУ "
        f"по формуле Миффлина-Сан Жеора и определит риски скрытых дефицитов.\n\n"
        f"Укажите ваш пол:"
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(KbjuFSM.gender)

@dp.callback_query(F.data.startswith("g_"))
async def cb_gender(call: types.CallbackQuery, state: FSMContext):
    g = "Мужской" if call.data == "g_male" else "Женский"
    await state.update_data(gender=g, user_id=call.from_user.id, username=call.from_user.username or "")
    await call.message.edit_text(f"Пол: <b>{g}</b>\n\nВведите ваш возраст (полных лет):", parse_mode="HTML")
    await state.set_state(KbjuFSM.age)

@dp.message(KbjuFSM.age)
async def proc_age(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer("Введите возраст числом (например, 29):")
        return
    await state.update_data(age=int(msg.text))
    await msg.answer("Введите ваш текущий вес в кг (например, 72.5):")
    await state.set_state(KbjuFSM.weight)

@dp.message(KbjuFSM.weight)
async def proc_weight(msg: types.Message, state: FSMContext):
    try:
        w = float(msg.text.replace(",", "."))
    except ValueError:
        await msg.answer("Введите вес корректным числом:")
        return
    await state.update_data(weight=w)
    await msg.answer("Введите ваш рост в см (например, 175):")
    await state.set_state(KbjuFSM.height)

@dp.message(KbjuFSM.height)
async def proc_height(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer("Введите рост в см (например, 175):")
        return
    await state.update_data(height=int(msg.text))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛋 Малоподвижный (офис/авто)", callback_data="act_sedentary")],
        [InlineKeyboardButton(text="🚶 1-3 тренировки в неделю", callback_data="act_light")],
        [InlineKeyboardButton(text="🏋️ 3-5 интенсивных тренировок", callback_data="act_moderate")]
    ])
    await msg.answer("Уровень физической активности:", reply_markup=kb)
    await state.set_state(KbjuFSM.activity)

@dp.callback_query(F.data.startswith("act_"))
async def cb_act(call: types.CallbackQuery, state: FSMContext):
    act = call.data.replace("act_", "")
    await state.update_data(activity=act)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Похудение и рельеф", callback_data="goal_def")],
        [InlineKeyboardButton(text="⚖️ Поддержание веса", callback_data="goal_main")],
        [InlineKeyboardButton(text="💪 Набор мышечной массы", callback_data="goal_surp")]
    ])
    await call.message.edit_text("Ваша главная цель на ближайшие 2 месяца:", reply_markup=kb)
    await state.set_state(KbjuFSM.goal)

@dp.callback_query(F.data.startswith("goal_"))
async def cb_goal(call: types.CallbackQuery, state: FSMContext):
    goals = {"goal_def": "Похудение", "goal_main": "Поддержание", "goal_surp": "Набор массы"}
    g_str = goals.get(call.data, "Похудение")
    await state.update_data(goal=g_str)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥱 Сонливость днем и тяга к сладкому", callback_data="sym_sugar")],
        [InlineKeyboardButton(text="🫧 Вздутия после еды / тяжесть в ЖКТ", callback_data="sym_gut")],
        [InlineKeyboardButton(text="💆 Выпадение волос / сухость кожи", callback_data="sym_hair")],
        [InlineKeyboardButton(text="✅ Симптомов нет, всё в норме", callback_data="sym_none")]
    ])
    await call.message.edit_text("Есть ли тревожные маркеры самочувствия?", reply_markup=kb)
    await state.set_state(KbjuFSM.symptoms)

@dp.callback_query(F.data.startswith("sym_"))
async def cb_sym(call: types.CallbackQuery, state: FSMContext):
    sym_map = {
        "sym_sugar": "Тяга к сахару (риск дефицита хрома/инсулинорезистентности)",
        "sym_gut": "Тяжесть в ЖКТ (риск низкой кислотности желудка)",
        "sym_hair": "Сухость/выпадение (риск дефицита ферритина и цинка)",
        "sym_none": "Маркеры в норме"
    }
    symptom_str = sym_map.get(call.data, "В норме")
    data = await state.get_data()
    data["symptoms"] = symptom_str
    
    calc = calculate_kbju(data["gender"], data["weight"], data["height"], data["age"], data["activity"], data["goal"])
    data.update(calc)
    save_profile(data)
    
    result = (
        f"📊 <b>ВАШ ПЕРСОНАЛЬНЫЙ МЕТАБОЛИЧЕСКИЙ ОТЧЕТ:</b>\n\n"
        f"• <b>Базовый обмен (BMR):</b> {calc['bmr']} ккал\n"
        f"• <b>Суточный расход (TDEE):</b> {calc['tdee']} ккал\n\n"
        f"🔥 <b>ЦЕЛЕВОЙ КАЛОРАЖ ({data['goal']}):</b> <code>{calc['calories']} ккал/день</code>\n"
        f"🥩 <b>Белки:</b> {calc['protein']} г | 🥑 <b>Жиры:</b> {calc['fats']} г | 🍚 <b>Углеводы:</b> {calc['carbs']} г\n"
        f"💧 <b>Норма чистой воды:</b> {calc['water']} л/сутки\n\n"
        f"⚠️ <b>Анализ симптома:</b> {symptom_str}\n\n"
        f"🎁 <i>Доктор подготовил гайд «Топ-7 базовых анализов крови». Нажмите кнопку ниже для скачивания:</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Забрать PDF-гайд по анализам", url="https://t.me/idrisov_prod")],
        [InlineKeyboardButton(text="🔄 Пересчитать заново", callback_data="restart")]
    ])
    await call.message.edit_text(result, reply_markup=kb, parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "restart")
async def cb_restart(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await cmd_start(call.message, state)

async def main():
    init_db()
    print("Bot 2 (NutriScan AI) initialized.")
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK MODE] Bot 2 compiled and verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
