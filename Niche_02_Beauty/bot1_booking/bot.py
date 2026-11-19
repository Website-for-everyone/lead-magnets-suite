import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, save_booking

BOT_TOKEN = os.getenv("BOT_TOKEN", "MOCK_TOKEN_BARBER_BOOKING")

class BarberFSM(StatesGroup):
    master = State()
    service = State()
    slot = State()
    phone = State()

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✂️ Топ-барбер Руслан (Стаж 8 лет)", callback_data="m_ruslan")],
        [InlineKeyboardButton(text="⚡ Шеф-барбер Марк (Премиум)", callback_data="m_mark")],
        [InlineKeyboardButton(text="🎲 Любой свободный мастер", callback_data="m_any")]
    ])
    text = (
        f"💈 <b>Atelier Velvet & Blade // Премиум барбершоп</b>

"
        f"Привет, {msg.from_user.first_name}! Бронирование кресла 24/7 без звонков администратору.

"
        f"Выберите мастера:"
    )
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(BarberFSM.master)

@dp.callback_query(F.data.startswith("m_"))
async def cb_master(call: types.CallbackQuery, state: FSMContext):
    masters = {"m_ruslan": "Топ-барбер Руслан", "m_mark": "Шеф-барбер Марк", "m_any": "Ближайший свободный мастер"}
    m = masters.get(call.data, "Мастер")
    await state.update_data(barber=m, user_id=call.from_user.id, username=call.from_user.username or "", client_name=call.from_user.full_name or "")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💈 Мужская стрижка + мытье головы (2 500 ₽)", callback_data="s_hair")],
        [InlineKeyboardButton(text="🧔 Моделирование бороды с распариванием (1 800 ₽)", callback_data="s_beard")],
        [InlineKeyboardButton(text="👑 Полный комплекс: Стрижка + Борода + SPA (3 800 ₽)", callback_data="s_full")]
    ])
    await call.message.edit_text(f"Мастер: <b>{m}</b>

Выберите комплекс услуг:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BarberFSM.service)

@dp.callback_query(F.data.startswith("s_"))
async def cb_service(call: types.CallbackQuery, state: FSMContext):
    services = {
        "s_hair": "Мужская стрижка (2 500 ₽)",
        "s_beard": "Моделирование бороды (1 800 ₽)",
        "s_full": "Комплекс Стрижка + Борода + SPA (3 800 ₽)"
    }
    s = services.get(call.data, "Стрижка")
    await state.update_data(service=s)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓 Сегодня: 17:00", callback_data="t_1"), InlineKeyboardButton(text="🗓 Сегодня: 19:30", callback_data="t_2")],
        [InlineKeyboardButton(text="🗓 Завтра: 12:00", callback_data="t_3"), InlineKeyboardButton(text="🗓 Завтра: 16:00", callback_data="t_4")]
    ])
    await call.message.edit_text(f"Услуга: <b>{s}</b>

Выберите свободное время:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BarberFSM.slot)

@dp.callback_query(F.data.startswith("t_"))
async def cb_time(call: types.CallbackQuery, state: FSMContext):
    times = {"t_1": "Сегодня 17:00", "t_2": "Сегодня 19:30", "t_3": "Завтра 12:00", "t_4": "Завтра 16:00"}
    slot = times.get(call.data, "Время")
    await state.update_data(slot=slot)
    
    await call.message.edit_text(f"Слот: <b>{slot}</b>

Введите номер телефона для SMS-напоминания (например: +79991234567):", parse_mode="HTML")
    await state.set_state(BarberFSM.phone)

@dp.message(BarberFSM.phone)
async def proc_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip()
    await state.update_data(phone=phone)
    data = await state.get_data()
    save_booking(data)
    
    text = (
        f"✅ <b>ВЫ УСПЕШНО ЗАПИСАНЫ!</b>

"
        f"• <b>Мастер:</b> {data['barber']}
"
        f"• <b>Услуга:</b> {data['service']}
"
        f"• <b>Время:</b> {data['slot']}
"
        f"• <b>Телефон:</b> {phone}

"
        f"📍 <i>Адрес: ул. Большая Дмитровка, 12 (м. Театральная). Кофе/виски в баре включены в визит.</i>"
    )
    await msg.answer(text, parse_mode="HTML")
    await state.clear()

async def main():
    init_db()
    if BOT_TOKEN.startswith("MOCK_"):
        print("[MOCK] Barber Booking Bot verified.")
        return
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
