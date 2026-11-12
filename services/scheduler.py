import asyncio,json,logging,time
from aiogram.exceptions import TelegramForbiddenError,TelegramBadRequest,TelegramRetryAfter
from database import connect
log=logging.getLogger(__name__)

async def safe_delete(bot,uid,mid):
    try: await bot.delete_message(chat_id=uid,message_id=mid)
    except (TelegramBadRequest,TelegramForbiddenError): pass

async def scheduler_loop(bot):
    while True:
        try:
            now=time.time()
            async with await connect() as db:
                cur=await db.execute("SELECT * FROM campaigns WHERE active=1 AND (next_at<=? OR (expires_at IS NOT NULL AND expires_at<=?))",(now,now))
                campaigns=await cur.fetchall()
                cur=await db.execute("SELECT user_id FROM users")
                users=await cur.fetchall()
            for c in campaigns:
                try: previous=json.loads(c["last_message_ids"] or "{}")
                except (ValueError,TypeError): previous={}
                if c["expires_at"] is not None and now>=c["expires_at"]:
                    for uid,mid in previous.items(): await safe_delete(bot,int(uid),int(mid))
                    async with await connect() as db:
                        await db.execute("UPDATE campaigns SET active=0,last_message_ids='{}' WHERE id=?",(c["id"],)); await db.commit()
                    continue
                for u in users:
                    uid=int(u["user_id"]); key=str(uid)
                    if key in previous: await safe_delete(bot,uid,int(previous[key]))
                    try:
                        sent=await bot.copy_message(chat_id=uid,from_chat_id=c["chat_id"],message_id=c["message_id"])
                        previous[key]=sent.message_id
                    except TelegramForbiddenError: previous.pop(key,None)
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)
                    except Exception: log.exception("Campaign %s delivery failed to %s",c["id"],uid)
                    await asyncio.sleep(0.04)
                async with await connect() as db:
                    await db.execute("UPDATE campaigns SET last_message_ids=?,next_at=? WHERE id=?",(json.dumps(previous),now+c["interval_minutes"]*60,c["id"]))
                    await db.commit()
        except asyncio.CancelledError: raise
        except Exception: log.exception("Scheduler iteration failed")
        await asyncio.sleep(10)
