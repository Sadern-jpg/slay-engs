import asyncio, time, json, logging
from database import connect
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

log=logging.getLogger(__name__)

async def scheduler_loop(bot):
    while True:
        now=time.time()
        async with await connect() as db:
            cur=await db.execute("SELECT * FROM campaigns WHERE active=1 AND next_at<=?",(now,))
            campaigns=await cur.fetchall()
            cur=await db.execute("SELECT user_id FROM users")
            users=await cur.fetchall()
        for camp in campaigns:
            if camp["expires_at"] is not None and now >= camp["expires_at"]:
                async with await connect() as db:
                    await db.execute("UPDATE campaigns SET active=0 WHERE id=?",(camp["id"],)); await db.commit()
                continue
            try:
                last_ids=json.loads(camp["last_message_ids"] or "{}")
            except Exception: last_ids={}
            for user in users:
                uid=str(user["user_id"])
                try:
                    old=last_ids.get(uid)
                    if old:
                        try: await bot.delete_message(int(uid),int(old))
                        except TelegramBadRequest: pass
                    sent=await bot.copy_message(chat_id=int(uid),from_chat_id=camp["chat_id"],message_id=camp["message_id"])
                    last_ids[uid]=sent.message_id
                except TelegramForbiddenError:
                    continue
                except Exception:
                    log.exception("Campaign %s delivery failed for user %s",camp["id"],uid)
            async with await connect() as db:
                await db.execute("UPDATE campaigns SET last_message_ids=?,next_at=? WHERE id=?",
                                 (json.dumps(last_ids),now+camp["interval_minutes"]*60,camp["id"]))
                await db.commit()
        await asyncio.sleep(20)
