import asyncio,logging
from database.db import due_reminders,postpone_reminder
from keyboards.user import reminder_keyboard

TEXT="<b>Well, that’s a great start! 💅</b>\nрада, что ты забрала свой little gift!\n\nА если ты хочешь не просто собирать полезные материалы, а действительно бустануть свой english, приглашаю тебя на <b>бесплатное пробное занятие</b>\n\nПознакомимся, определим твой уровень, обсудим цели и подумаем, как сделать английский частью твоей жизни 🩷"

async def reminder_worker(bot):
    while True:
        try:
            for row in await due_reminders():
                uid=row["user_id"]
                try: await bot.send_message(uid,TEXT,reply_markup=reminder_keyboard())
                except Exception as e: logging.warning("Reminder to %s failed: %s",uid,e)
                finally: await postpone_reminder(uid)
        except Exception: logging.exception("Reminder loop failed")
        await asyncio.sleep(60)
