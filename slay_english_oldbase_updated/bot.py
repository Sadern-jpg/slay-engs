import asyncio
from aiogram import Bot,Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database.db import init_db
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from services.campaigns import worker
class C: ADMIN_IDS=config.ADMIN_IDS
async def main():
 if not config.BOT_TOKEN or "PASTE_NEW_TOKEN" in config.BOT_TOKEN: raise RuntimeError("Заполни BOT_TOKEN в .env")
 await init_db()
 bot=Bot(config.BOT_TOKEN); dp=Dispatcher(storage=MemoryStorage())
 dp.include_router(admin_router); dp.include_router(user_router)
 asyncio.create_task(worker(bot))
 await dp.start_polling(bot,c=C)
if __name__=="__main__": asyncio.run(main())
