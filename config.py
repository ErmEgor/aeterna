# config.py

import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# --- Основные настройки из .env ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")

# Проверяем, что токен и ID админов заданы
if not BOT_TOKEN:
    raise ValueError("Необходимо указать BOT_TOKEN в .env файле")
if not ADMIN_IDS_STR:
    raise ValueError("Необходимо указать ADMIN_IDS в .env файле")

# Преобразуем строку с ID в список чисел
try:
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',')]
except ValueError:
    raise ValueError("ADMIN_IDS в .env файле должны быть числами, разделенными запятой")


# --- Настройки услуг (остаются здесь для удобства редактирования) ---
# Словарь, где ключ - это внутреннее имя услуги, а значение - словарь с параметрами
SERVICES = {
    'manicure': {'name': 'Маникюр с покрытием', 'price': 2500, 'duration': 90},
    'pedicure': {'name': 'Педикюр', 'price': 3000, 'duration': 75},
    'eyebrows': {'name': 'Коррекция бровей', 'price': 1000, 'duration': 30}
}

# --- Настройки времени работы ---
WORK_HOURS = {
    'start': '10:00',
    'end': '20:00'
}