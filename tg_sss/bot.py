import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
from database.db import init_db
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from services.reminders import reminder_worker

async def main():
    logging.basicConfig(level=logging.INFO)
    if not settings.BOT_TOKEN:
        raise RuntimeError("Заполните BOT_TOKEN в файле .env")
    await init_db()
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(user_router)
    task = asyncio.create_task(reminder_worker(bot))
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
