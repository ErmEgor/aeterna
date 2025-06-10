# main.py

import asyncio
import logging
import os

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
# --- НОВЫЕ ИМПОРТЫ для меню ---
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

# --- ВАЖНО: Импортируем ADMIN_IDS из config.py ---
from config import BOT_TOKEN, ADMIN_IDS
from handlers import router
from database import init_db

# --- Настройки логгирования ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

# --- Основные переменные из .env ---
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", 10000))
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Путь для вебхука
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"


# --- НОВАЯ ФУНКЦИЯ: Установка меню команд ---
async def set_bot_commands(bot: Bot):
    """
    Создает и устанавливает меню с командами для разных ролей пользователей.
    """
    # Команды для обычных пользователей
    user_commands = [
        BotCommand(command="/start", description="🚀 Начать заново / Главное меню")
    ]
    # Команды для администраторов (включают все пользовательские + админские)
    admin_commands = user_commands + [
        BotCommand(command="/admin", description="⚙️ Админ-панель")
    ]

    # Устанавливаем команды по умолчанию для всех пользователей
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Устанавливаем расширенные команды для каждого администратора
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logging.error(f"Не удалось установить команды для админа {admin_id}: {e}")
    logging.info("Меню команд успешно настроено.")


# --- Функции жизненного цикла: запуск и остановка ---
async def on_startup(bot: Bot) -> None:
    if not BASE_WEBHOOK_URL:
        logging.error("BASE_WEBHOOK_URL не задан в переменных окружения!")
        return

    # Устанавливаем меню команд
    await set_bot_commands(bot)

    # Устанавливаем вебхук
    webhook_url = f"{BASE_WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
    await bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET)
    logging.info(f"Вебхук установлен на URL: {webhook_url}")


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    logging.info("Вебхук удален.")


async def main():
    init_db()
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    app = web.Application()
    
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    setup_application(app, dp, bot=bot)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
    await site.start()

    logging.info(f"Сервер запущен на http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен вручную.")