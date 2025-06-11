# handlers.py

import logging
import re
from datetime import datetime, timedelta

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, any_state
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb
from config import ADMIN_IDS, SERVICES, WORK_HOURS

router = Router()

def format_date_russian(dt_obj):
    """Форматирует дату в красивый русский формат (e.g., '20 июня 2025 г.')"""
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    return f"{dt_obj.day} {months[dt_obj.month - 1]} {dt_obj.year} г."

# ================================================
#          МАШИНА СОСТОЯНИЙ (FSM)
# ================================================
class Booking(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()

class Admin(StatesGroup):
    panel = State()
    choosing_date_for_view = State()
    choosing_date_for_add = State()
    choosing_time_for_add = State()
    choosing_date_for_remove = State()
    manual_booking_service = State()
    manual_booking_date = State()
    manual_booking_time = State()
    manual_booking_name = State()
    manual_booking_phone = State()

# ================================================
#          ОБЩИЕ ХЕНДЛЕРЫ
# ================================================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n"
        "Добро пожаловать в наш бот для записи. "
        "Выберите действие:",
        reply_markup=kb.main_menu_kb
    )

# (### ИЗМЕНЕНИЕ 1 ###) Новая функция для лаконичного возврата в меню
async def show_main_menu(message: Message, state: FSMContext):
    """Отображает главное меню без приветственного текста."""
    await state.clear()
    await message.answer(
        "Вы вернулись в главное меню. Выберите действие:",
        reply_markup=kb.main_menu_kb
    )

@router.callback_query(F.data == "cancel_process")
async def cancel_process(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # (### ИЗМЕНЕНИЕ 2 ###) Используем новую функцию
    await callback.message.edit_text("Действие отменено.")
    await show_main_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "to_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    # (### ИЗМЕНЕНИЕ 3 ###) Удаляем старое сообщение и используем новую функцию
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()
    
# ================================================
#          ПОЛЬЗОВАТЕЛЬСКИЙ СЦЕНАРИЙ
# ================================================
@router.message(F.text == "📅 Записаться")
async def process_booking(message: Message, state: FSMContext):
    await state.set_state(Booking.choosing_service)
    await message.answer("Выберите услугу:", reply_markup=kb.get_services_kb(SERVICES))

@router.message(F.text == "📔 Мои записи")
async def process_my_bookings(message: Message):
    bookings = db.get_user_bookings(message.from_user.id)
    await message.answer("Ваши активные записи:", reply_markup=kb.get_my_bookings_kb(bookings))

@router.message(F.text == "ℹ️ О нас")
async def process_about(message: Message):
    about_text = """
Добро пожаловать в <b>Студию красоты "Aeterna"</b>!
<i>Место, где ваша красота становится вечной.</i>

Мы рады предложить вам первоклассный сервис и уютную атмосферу, в которой вы сможете по-настояшему расслабиться.

<b>Наши преимущества:</b>
✨ <b>Профессионализм:</b> Наши мастера — сертифицированные специалисты с многолетним опытом.
🛡️ <b>Безопасность:</b> Мы строго соблюдаем все нормы СанПиН. Инструменты проходят 3 этапа стерилизации.
💎 <b>Качество:</b> Работаем только на премиальных, гипоаллергенных материалах от ведущих брендов.
☕ <b>Атмосфера:</b> У нас вы сможете насладиться чашечкой ароматного кофе или чая и отдохнуть от городской суеты.

📍 <b>Наш адрес:</b>
г. Москва, ул. Тверская, д. 15, 2 этаж, офис 214

🕒 <b>Часы работы:</b>
Понедельник - Воскресенье, с 10:00 до 21:00

📞 <b>Телефон для связи:</b>
+7 (495) 123-45-67

<b>Мы в соцсетях:</b>
<a href="https://instagram.com/">Instagram</a> | <a href="https://t.me/">Telegram-канал</a>
"""
    await message.answer(about_text, reply_markup=kb.about_kb)

# --- Шаги записи ---
@router.callback_query(StateFilter(Booking.choosing_service, Admin.manual_booking_service), F.data.startswith(("service:", "admin_service:")))
async def process_service_choice(callback: CallbackQuery, state: FSMContext):
    is_admin = callback.data.startswith("admin_")
    prefix = "admin_" if is_admin else ""
    service_id = callback.data.split(":")[1]
    
    await state.update_data(service_id=service_id)
    next_state = Admin.manual_booking_date if is_admin else Booking.choosing_date
    await state.set_state(next_state)
    
    await callback.message.edit_text(
        f"Вы выбрали: <b>{SERVICES[service_id]['name']}</b>\nТеперь выберите дату:",
        reply_markup=kb.create_calendar_kb(prefix=f"{prefix}date")
    )
    await callback.answer()

# (### ИЗМЕНЕНИЕ 4 ###) Новый обработчик для нажатий на прошедшие даты
@router.callback_query(StateFilter('*'), F.data == "past_date")
async def process_past_date_press(callback: CallbackQuery):
    await callback.answer(
        "Эта дата уже прошла. Пожалуйста, выберите доступную дату.",
        show_alert=True
    )

@router.callback_query(StateFilter(Booking.choosing_date, Admin.manual_booking_date), F.data.startswith(("date:", "admin_date:")))
async def process_date_choice(callback: CallbackQuery, state: FSMContext):
    is_admin = callback.data.startswith("admin_")
    prefix = "admin_" if is_admin else ""
    date_str = callback.data.partition(":")[2]
    await state.update_data(chosen_date=date_str)
    
    user_data = await state.get_data()
    service_id = user_data['service_id']
    
    booked_slots = db.get_booked_slots(date_str)
    admin_slots = db.get_admin_slots(date_str)
    
    available_slots = []
    start_time = datetime.strptime(WORK_HOURS['start'], '%H:%M')
    end_time = datetime.strptime(WORK_HOURS['end'], '%H:%M')
    
    current_time = start_time
    while current_time < end_time:
        slot_time_obj = current_time.time()
        is_booked = any(
            slot_time_obj == booked_slot for booked_slot in booked_slots
        )
        if not is_booked:
            available_slots.append(slot_time_obj)
        current_time += timedelta(minutes=15)
        
    for admin_slot in admin_slots:
        if admin_slot not in [s for s in available_slots] and admin_slot not in booked_slots:
            available_slots.append(admin_slot)
    
    available_slots.sort()

    next_state = Admin.manual_booking_time if is_admin else Booking.choosing_time
    await state.set_state(next_state)

    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    await callback.message.edit_text(
        f"Доступное время на <b>{format_date_russian(date_obj)}</b>:",
        reply_markup=kb.get_time_slots_kb(
            available_slots, 
            back_callback="admin_panel" if is_admin else "back_to_services",
            prefix=f"{prefix}time"
        )
    )
    await callback.answer()

# ... (остальной код до админ-панели остается без изменений) ...

@router.callback_query(StateFilter(Booking.choosing_time, Admin.manual_booking_time), F.data.startswith(("time:", "admin_time:")))
async def process_time_choice(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.partition(":")[2]
    await state.update_data(chosen_time=time_str)
    
    is_admin = callback.data.startswith("admin_")
    next_state = Admin.manual_booking_name if is_admin else Booking.entering_name
    await state.set_state(next_state)
    
    prompt_text = "Введите имя клиента:" if is_admin else "Введите ваше имя:"
    await callback.message.edit_text(prompt_text, reply_markup=kb.cancel_kb)
    await callback.answer()

@router.message(StateFilter(Booking.entering_name, Admin.manual_booking_name))
async def process_name_input(message: Message, state: FSMContext):
    await state.update_data(user_name=message.text)
    
    current_state = await state.get_state()
    is_admin = current_state == Admin.manual_booking_name
    next_state = Admin.manual_booking_phone if is_admin else Booking.entering_phone
    await state.set_state(next_state)
    
    prompt_text = "Введите телефон клиента в формате +79123456789:" if is_admin else "Введите ваш номер телефона в формате +79123456789:"
    await message.answer(prompt_text, reply_markup=kb.cancel_kb)

@router.message(StateFilter(Booking.entering_phone, Admin.manual_booking_phone))
async def process_phone_input(message: Message, state: FSMContext):
    phone_pattern = r'^\+7\d{10}$'
    if not re.match(phone_pattern, message.text):
        await message.answer("Неверный формат номера. Пожалуйста, введите номер в формате +79123456789.", reply_markup=kb.cancel_kb)
        return
    
    await state.update_data(user_phone=message.text)
    user_data = await state.get_data()
    
    service_name = SERVICES[user_data['service_id']]['name']
    booking_dt_obj = datetime.strptime(f"{user_data['chosen_date']} {user_data['chosen_time']}", '%Y-%m-%d %H:%M')
    
    current_state = await state.get_state()
    is_admin = current_state == Admin.manual_booking_phone
    prefix = "admin_" if is_admin else ""

    await message.answer(
        f"✅ <b>Проверьте и подтвердите запись:</b>\n\n"
        f"<b>Услуга:</b> {service_name}\n"
        f"<b>Дата и время:</b> {format_date_russian(booking_dt_obj)}, {booking_dt_obj.strftime('%H:%M')}\n"
        f"<b>Имя:</b> {user_data['user_name']}\n"
        f"<b>Телефон:</b> {message.text}",
        reply_markup=kb.get_confirmation_kb(prefix=prefix)
    )

@router.callback_query(F.data.endswith("confirm_booking"))
async def process_confirm_booking(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state not in (Booking.entering_phone, Admin.manual_booking_phone):
        await callback.answer("Что-то пошло не так. Попробуйте снова.", show_alert=True)
        return
        
    user_data = await state.get_data()
    is_admin = callback.data.startswith("admin_")
    
    service_name = SERVICES[user_data['service_id']]['name']
    booking_datetime = datetime.strptime(f"{user_data['chosen_date']} {user_data['chosen_time']}", '%Y-%m-%d %H:%M')
    user_name, user_phone = user_data['user_name'], user_data['user_phone']
    user_id = callback.from_user.id if not is_admin else 0 
    
    try:
        db.add_booking(user_id, user_name, user_phone, service_name, booking_datetime)
        
        if is_admin:
            final_text = (
                f"🎉 <b>Запись успешно создана!</b>\n\n"
                f"Клиент {user_name} записан на {format_date_russian(booking_datetime)} в {booking_datetime.strftime('%H:%M')}."
            )
        else:
            final_text = (
                f"🎉 <b>Запись успешно создана!</b>\n\n"
                f"Мы ждем вас {format_date_russian(booking_datetime)} в {booking_datetime.strftime('%H:%M')}.\n"
                f"За день до визита мы пришлем напоминание."
            )

        await callback.message.edit_text(final_text, reply_markup=None)
        
        if not is_admin:
            admin_message = (
                f"🔔 <b>Новая запись через бота!</b>\n\n"
                f"<b>Клиент:</b> {user_name}, {user_phone}\n"
                f"<b>Услуга:</b> {service_name}\n"
                f"<b>Когда:</b> {format_date_russian(booking_datetime)} в {booking_datetime.strftime('%H:%M')}\n"
                f"<b>ID клиента:</b> <code>{callback.from_user.id}</code>"
            )
            for admin_id in ADMIN_IDS:
                await callback.bot.send_message(admin_id, admin_message)
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при записи в БД: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании записи. Возможно, это время уже заняли.", reply_markup=None
        )
        await state.clear()
    
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_booking:"))
async def process_cancel_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])
    db.cancel_booking(booking_id)
    await callback.message.edit_text("Ваша запись успешно отменена.", reply_markup=None)
    await callback.answer("Запись отменена")
    
# ================================================
#          АДМИН-ПАНЕЛЬ
# ================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав доступа.")
        return
    await state.set_state(Admin.panel)
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_main_kb)

@router.callback_query(StateFilter(any_state), F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.panel)
    await callback.message.edit_text("Админ-панель:", reply_markup=kb.admin_main_kb)
    await callback.answer()

@router.callback_query(Admin.panel, F.data == "admin_view_bookings")
async def admin_view_bookings(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.choosing_date_for_view)
    # (### ИЗМЕНЕНИЕ 5 ###) Передаем админский префикс
    await callback.message.edit_text("Выберите дату для просмотра записей:", reply_markup=kb.create_calendar_kb(prefix="admin_date"))

# (### ИЗМЕНЕНИЕ 6 ###) Обрабатываем админский префикс
@router.callback_query(Admin.choosing_date_for_view, F.data.startswith("admin_date:"))
async def admin_show_daily_bookings(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.partition(":")[2]
    bookings = db.get_daily_bookings(date_str)
    
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    if not bookings:
        response_text = f"На {format_date_russian(date_obj)} записей нет."
    else:
        response_text = f"📋 <b>Записи на {format_date_russian(date_obj)}:</b>\n\n"
        for booking in bookings:
            booking_time, name, phone, service = booking
            dt_obj = datetime.strptime(booking_time, '%Y-%m-%d %H:%M')
            response_text += f"▪️ <b>{dt_obj.strftime('%H:%M')}</b> - {name}, {phone} (<i>{service}</i>)\n"
            
    await callback.message.edit_text(response_text, reply_markup=kb.admin_back_kb)
    await state.set_state(Admin.panel)

# --- Управление слотами ---
@router.callback_query(Admin.panel, F.data == "admin_manage_slots")
async def admin_manage_slots(callback: CallbackQuery):
    await callback.message.edit_text("Управление свободными слотами:", reply_markup=kb.admin_manage_slots_kb)
    await callback.answer()

@router.callback_query(Admin.panel, F.data == "admin_add_slot")
async def admin_add_slot_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.choosing_date_for_add)
    # (### ИЗМЕНЕНИЕ 7 ###) Передаем админский префикс
    await callback.message.edit_text("Выберите дату для добавления слота:", reply_markup=kb.create_calendar_kb(prefix="admin_date"))

# (### ИЗМЕНЕНИЕ 8 ###) Обрабатываем админский префикс
@router.callback_query(Admin.choosing_date_for_add, F.data.startswith("admin_date:"))
async def admin_add_slot_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.partition(":")[2]
    await state.update_data(admin_chosen_date=date_str)
    await state.set_state(Admin.choosing_time_for_add)
    await callback.message.edit_text("Введите время для нового слота в формате ЧЧ:ММ (например, 14:30).")

@router.message(Admin.choosing_time_for_add)
async def admin_add_slot_time(message: Message, state: FSMContext):
    try:
        time_obj = datetime.strptime(message.text, '%H:%M').time()
        user_data = await state.get_data()
        date_str = user_data['admin_chosen_date']
        slot_datetime = datetime.combine(datetime.strptime(date_str, '%Y-%m-%d'), time_obj)
        db.add_admin_slot(slot_datetime)
        await message.answer(f"✅ Слот <b>{slot_datetime.strftime('%d.%m.%Y %H:%M')}</b> успешно добавлен!", reply_markup=kb.admin_back_kb)
        await state.set_state(Admin.panel)
    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, введите в формате ЧЧ:ММ.")
        
@router.callback_query(Admin.panel, F.data == "admin_remove_slot_start")
async def admin_remove_slot_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.choosing_date_for_remove)
    # (### ИЗМЕНЕНИЕ 9 ###) Передаем админский префикс
    await callback.message.edit_text("Выберите дату для удаления слота:", reply_markup=kb.create_calendar_kb(prefix="admin_date"))

# (### ИЗМЕНЕНИЕ 10 ###) Обрабатываем админский префикс
@router.callback_query(Admin.choosing_date_for_remove, F.data.startswith("admin_date:"))
async def admin_remove_slot_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.partition(":")[2]
    slots_for_removal = db.get_admin_slots(date_str)
    await callback.message.edit_text(
        f"Выберите слот для удаления на {format_date_russian(datetime.strptime(date_str, '%Y-%m-%d'))}:",
        reply_markup=kb.get_slots_for_removal_kb(slots_for_removal, date_str)
    )
    await state.set_state(Admin.panel)

@router.callback_query(Admin.panel, F.data.startswith("admin_delete_slot:"))
async def admin_delete_slot_confirm(callback: CallbackQuery, state: FSMContext):
    _, date_str, time_str = callback.data.split(":")
    slot_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
    db.remove_admin_slot(slot_datetime)
    await callback.message.edit_text(
        f"🗑 Слот <b>{slot_datetime.strftime('%d.%m.%Y %H:%M')}</b> успешно удален.",
        reply_markup=kb.admin_back_kb
    )
    await callback.answer("Слот удален")
    
# --- Ручная запись клиента ---
@router.callback_query(Admin.panel, F.data == "admin_manual_booking_start")
async def admin_manual_booking_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.manual_booking_service)
    await callback.message.edit_text("Шаг 1: Выберите услугу для клиента", reply_markup=kb.get_services_kb(SERVICES, prefix="admin_service"))