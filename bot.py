import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database.db import init_db
from handlers.admin import router as admin_router
from handlers.user import router as user_router
from services.campaigns import campaign_worker

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в переменных окружения хостинга")
    if not config.ADMIN_IDS:
        logging.warning("ADMIN_IDS не задан: админ-панель будет недоступна")
    await init_db()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)
    dp.include_router(user_router)
    worker = asyncio.create_task(campaign_worker(bot), name="campaign-worker")
    try:
        await dp.start_polling(bot, cfg=config, allowed_updates=dp.resolve_used_update_types())
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
