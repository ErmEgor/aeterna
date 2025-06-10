# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import calendar

# <-- НОВЫЙ СПИСОК МЕСЯЦЕВ -->
# Список для заголовков календаря (Именительный падеж)
RUSSIAN_MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

# --- Главное меню ---
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Записаться")],
        [KeyboardButton(text="📔 Мои записи"), KeyboardButton(text="ℹ️ О нас")]
    ],
    resize_keyboard=True
)

# --- Клавиатура "О нас" ---
about_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="to_main_menu")]
    ]
)

# --- Универсальная кнопка Отмены ---
cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_process")]
])

# --- Клавиатура для выбора услуги ---
def get_services_kb(services, prefix="service"):
    builder = InlineKeyboardBuilder()
    for service_id, service_info in services.items():
        builder.button(
            text=f"{service_info['name']} ({service_info['price']} руб.)",
            callback_data=f"{prefix}:{service_id}"
        )
    builder.button(text="◀️ Назад", callback_data="to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

# --- Календарь для выбора даты ---
def create_calendar_kb(year=None, month=None, prefix="date"):
    if year is None: year = datetime.now().year
    if month is None: month = datetime.now().month

    builder = InlineKeyboardBuilder()
    
    # <-- ИЗМЕНЕНИЕ ЗДЕСЬ: Используем наш список вместо системного -->
    month_name = RUSSIAN_MONTHS[month - 1]
    builder.row(
        InlineKeyboardButton(text=" ", callback_data="ignore"),
        InlineKeyboardButton(text=f"{month_name} {year}", callback_data="ignore"),
        InlineKeyboardButton(text=" ", callback_data="ignore")
    )
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in days])

    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row_buttons = []
        for day in week:
            if day == 0:
                row_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                current_date = datetime(year, month, day).date()
                if current_date < datetime.now().date():
                    row_buttons.append(InlineKeyboardButton(text=str(day), callback_data="ignore"))
                else:
                    row_buttons.append(InlineKeyboardButton(text=str(day), callback_data=f"{prefix}:{current_date.strftime('%Y-%m-%d')}"))
        builder.row(*row_buttons)

    nav_callback_prefix = prefix.replace('date', '')
    builder.row(
        InlineKeyboardButton(text="<", callback_data=f"{nav_callback_prefix}prev_month:{year}-{month}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_services"),
        InlineKeyboardButton(text=">", callback_data=f"{nav_callback_prefix}next_month:{year}-{month}")
    )
    return builder.as_markup()

# (остальной код файла keyboards.py остается без изменений)
# ... (скопируйте сюда оставшуюся часть вашего файла keyboards.py)
def get_time_slots_kb(available_slots, back_callback="back_to_calendar", prefix="time"):
    builder = InlineKeyboardBuilder()
    if not available_slots:
        builder.button(text="Свободных слотов нет", callback_data="ignore")
    else:
        for slot in available_slots:
            builder.button(text=slot.strftime('%H:%M'), callback_data=f"{prefix}:{slot.strftime('%H:%M')}")
    builder.button(text="◀️ Назад к выбору даты", callback_data=back_callback)
    builder.adjust(4)
    return builder.as_markup()
    
def get_confirmation_kb(prefix=""):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{prefix}confirm_booking")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_process")]
        ]
    )

def get_my_bookings_kb(bookings):
    builder = InlineKeyboardBuilder()
    if not bookings:
        builder.button(text="У вас нет активных записей", callback_data="ignore")
    else:
        for booking in bookings:
            booking_id, service_name, booking_datetime = booking
            dt_obj = datetime.strptime(booking_datetime, '%Y-%m-%d %H:%M')
            text = f"{service_name} - {dt_obj.strftime('%d.%m.%Y %H:%M')}"
            builder.button(text=f"❌ Отменить: {text}", callback_data=f"cancel_booking:{booking_id}")
    
    builder.button(text="◀️ Назад в меню", callback_data="to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

admin_main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📋 Записи на день", callback_data="admin_view_bookings")],
    [InlineKeyboardButton(text="🗓️ Управление слотами", callback_data="admin_manage_slots")],
    [InlineKeyboardButton(text="✍️ Записать клиента", callback_data="admin_manual_booking_start")],
    # <-- НОВАЯ КНОПКА ВЫХОДА -->
    [InlineKeyboardButton(text="🚪 Выйти в главное меню", callback_data="to_main_menu")] 
])


admin_manage_slots_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить слот", callback_data="admin_add_slot")],
    [InlineKeyboardButton(text="➖ Удалить слот", callback_data="admin_remove_slot_start")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
])

def get_slots_for_removal_kb(slots, date_str):
    builder = InlineKeyboardBuilder()
    if not slots:
        builder.button(text="Нет созданных слотов для удаления", callback_data="ignore")
    else:
        for slot in slots:
            builder.button(
                text=f"❌ {slot.strftime('%H:%M')}", 
                callback_data=f"admin_delete_slot:{date_str}_{slot.strftime('%H:%M')}"
            )
    builder.button(text="◀️ Назад", callback_data="admin_manage_slots")
    builder.adjust(4)
    return builder.as_markup()

admin_back_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_panel")]
])