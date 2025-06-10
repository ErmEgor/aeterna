# main.py

import asyncio
import logging
import os # <-- Удалили locale

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN
from handlers import router
from database import init_db

# <-- УДАЛЕН БЛОК С LOCALE.SETLOCALE -->

# --- Настройки логгирования ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

# --- Основные переменные из .env ---
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", 10000))
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Путь для вебхука, по которому Telegram будет присылать обновления
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"


# --- Функции жизненного цикла: запуск и остановка ---
async def on_startup(bot: Bot) -> None:
    if not BASE_WEBHOOK_URL:
        logging.error("BASE_WEBHOOK_URL не задан в переменных окружения!")
        return

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