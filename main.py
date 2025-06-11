# main.py

import asyncio
import logging
import os

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

# --- Импортируем готовые переменные из config.py ---
from config import BOT_TOKEN, ADMIN_IDS 
from handlers import router
from database import init_db

# --- Настройки логгирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Основные переменные из .env ---
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", 10000))
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Путь для вебхука
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# Проверка переменных окружения
if not all([BOT_TOKEN, BASE_WEBHOOK_URL, WEBHOOK_SECRET]):
    missing_vars = [var for var, val in [
        ("BOT_TOKEN", BOT_TOKEN),
        ("BASE_WEBHOOK_URL", BASE_WEBHOOK_URL),
        ("WEBHOOK_SECRET", WEBHOOK_SECRET)
    ] if not val]
    logger.error(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
    raise ValueError(f"Необходимо установить переменные окружения: {', '.join(missing_vars)}")

# --- Установка меню команд ---
async def set_bot_commands(bot: Bot):
    user_commands = [
        BotCommand(command="/start", description="🚀 Начать заново / Главное меню")
    ]
    admin_commands = user_commands + [
        BotCommand(command="/admin", description="⚙️ Админ-панель")
    ]

    try:
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
        for admin_id in ADMIN_IDS:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        logger.info("Меню команд успешно настроено.")
    except Exception as e:
        logger.error(f"Ошибка при установке команд: {e}")

# --- Обработчик ping-запросов ---
async def ping_server(request):
    """Отвечает на 'ping' запросы от сервисов мониторинга."""
    logger.info(f"Получен ping-запрос от {request.remote} с URL: {request.url}")
    return web.Response(text="ok")

# --- Функции жизненного цикла ---
async def on_startup(bot: Bot) -> None:
    if not BASE_WEBHOOK_URL:
        logger.error("BASE_WEBHOOK_URL не задан в переменных окружения!")
        raise ValueError("BASE_WEBHOOK_URL не задан!")

    try:
        await set_bot_commands(bot)
        webhook_url = f"{BASE_WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET)
        logger.info(f"Вебхук установлен на URL: {webhook_url}")
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")
        raise

async def on_shutdown(bot: Bot) -> None:
    try:
        await bot.delete_webhook()
        await bot.session.close()
        logger.info("Вебхук удален и сессия закрыта.")
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}")

async def main():
    # Инициализация базы данных
    init_db()

    # Настройка хранилища и диспетчера
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    
    # Регистрация хуков
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Инициализация бота
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    # Создание aiohttp-приложения
    app = web.Application()
    
    # Добавляем маршрут для пинга
    app.router.add_get("/ping", ping_server)

    # Настройка вебхука
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    setup_application(app, dp, bot=bot)

    # Запуск сервера
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
        await site.start()
        logger.info(f"Сервер запущен на http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
        await asyncio.Event().wait()
    except Exception as e:
        logger.error(f"Ошибка при запуске сервера: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise