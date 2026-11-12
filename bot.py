import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from database import init_db
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from services.scheduler import scheduler_loop

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing. Add it to BotHost environment variables.")
    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)
    dp.include_router(user_router)
    scheduler_task = asyncio.create_task(scheduler_loop(bot), name="campaign-scheduler")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Slay English bot started")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
