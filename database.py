# database.py

import sqlite3
from datetime import datetime

def init_db():
    """Инициализирует базу данных и создает таблицы, если их нет."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    
    # Таблица для хранения записей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        user_phone TEXT NOT NULL,
        service_name TEXT NOT NULL,
        booking_datetime TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'confirmed' -- confirmed, cancelled
    )
    ''')
    
    # Таблица для хранения свободных слотов, управляемых админом
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS time_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_datetime TEXT NOT NULL UNIQUE
    )
    ''')
    
    conn.commit()
    conn.close()

def add_booking(user_id, user_name, user_phone, service_name, booking_datetime):
    """Добавляет новую запись в базу данных."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO bookings (user_id, user_name, user_phone, service_name, booking_datetime, status)
    VALUES (?, ?, ?, ?, ?, 'confirmed')
    ''', (user_id, user_name, user_phone, service_name, booking_datetime.strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    conn.close()

def get_user_bookings(user_id):
    """Получает все активные записи пользователя."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, service_name, booking_datetime FROM bookings
    WHERE user_id = ? AND status = 'confirmed' AND DATETIME(booking_datetime) > DATETIME('now', 'localtime')
    ORDER BY booking_datetime
    ''', (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def cancel_booking(booking_id):
    """Отменяет запись по ее ID."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()

def get_booked_slots(date_str):
    """Получает все забронированные слоты на определенную дату."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT booking_datetime FROM bookings
    WHERE DATE(booking_datetime) = ? AND status = 'confirmed'
    ''', (date_str,))
    booked_times = [datetime.strptime(row[0], '%Y-%m-%d %H:%M').time() for row in cursor.fetchall()]
    conn.close()
    return booked_times

def get_admin_slots(date_str):
    """Получает все созданные админом слоты на дату."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT slot_datetime FROM time_slots
    WHERE DATE(slot_datetime) = ?
    ''', (date_str,))
    admin_slots = [datetime.strptime(row[0], '%Y-%m-%d %H:%M').time() for row in cursor.fetchall()]
    conn.close()
    return admin_slots

def add_admin_slot(slot_datetime):
    """Добавляет новый слот времени, созданный админом."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO time_slots (slot_datetime) VALUES (?)", (slot_datetime.strftime('%Y-%m-%d %H:%M'),))
        conn.commit()
    except sqlite3.IntegrityError:
        # Слот уже существует
        pass
    finally:
        conn.close()

def remove_admin_slot(slot_datetime):
    """Удаляет слот времени, созданный админом."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM time_slots WHERE slot_datetime = ?", (slot_datetime.strftime('%Y-%m-%d %H:%M'),))
    conn.commit()
    conn.close()
    
def get_daily_bookings(date_str):
    """Получает все записи на определенный день для админа."""
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT booking_datetime, user_name, user_phone, service_name FROM bookings
    WHERE DATE(booking_datetime) = ? AND status = 'confirmed'
    ORDER BY booking_datetime
    ''', (date_str,))
    bookings = cursor.fetchall()
    conn.close()
    return bookings