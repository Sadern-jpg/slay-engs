import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database.db import init_db
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from services.campaigns import campaign_worker

class Config:
    ADMIN_IDS = config.ADMIN_IDS

async def main():
    logging.basicConfig(level=logging.INFO)
    if not config.BOT_TOKEN or "PASTE_NEW_TOKEN" in config.BOT_TOKEN:
        raise RuntimeError("Заполни BOT_TOKEN в переменных окружения хостинга или в .env")
    await init_db()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)
    dp.include_router(user_router)
    worker_task = asyncio.create_task(campaign_worker(bot))
    try:
        await dp.start_polling(bot, cfg=Config)
    finally:
        worker_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
