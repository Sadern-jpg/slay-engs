import asyncio
import json
import logging
import time
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from database import connect

log = logging.getLogger(__name__)

async def _delete_previous(bot, user_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=user_id, message_id=message_id)
    except TelegramBadRequest:
        # Already deleted, too old, or otherwise not deletable: continue campaign.
        pass
    except TelegramForbiddenError:
        pass

async def scheduler_loop(bot):
    """Deliver active campaigns and replace each user's previous campaign message."""
    while True:
        now = time.time()
        async with await connect() as db:
            cur = await db.execute("SELECT * FROM campaigns WHERE active=1 AND (next_at<=? OR expires_at<=?)", (now, now))
            campaigns = await cur.fetchall()
            cur = await db.execute("SELECT user_id FROM users")
            users = await cur.fetchall()

        for campaign in campaigns:
            try:
                last_ids = json.loads(campaign["last_message_ids"] or "{}")
                if not isinstance(last_ids, dict):
                    last_ids = {}
            except (TypeError, json.JSONDecodeError):
                last_ids = {}

            # At expiry, remove the last campaign message from each reachable chat.
            if campaign["expires_at"] is not None and now >= campaign["expires_at"]:
                for uid, old_id in list(last_ids.items()):
                    try:
                        await _delete_previous(bot, int(uid), int(old_id))
                    except Exception:
                        log.exception("Could not remove expired campaign message %s from %s", campaign["id"], uid)
                async with await connect() as db:
                    await db.execute("UPDATE campaigns SET active=0,last_message_ids='{}' WHERE id=?", (campaign["id"],))
                    await db.commit()
                continue

            for user in users:
                uid = int(user["user_id"])
                uid_key = str(uid)
                old_id = last_ids.get(uid_key)
                if old_id:
                    await _delete_previous(bot, uid, int(old_id))
                try:
                    sent = await bot.copy_message(chat_id=uid, from_chat_id=campaign["chat_id"], message_id=campaign["message_id"])
                    last_ids[uid_key] = sent.message_id
                except TelegramForbiddenError:
                    # User blocked the bot; discard any stale message tracking.
                    last_ids.pop(uid_key, None)
                except TelegramRetryAfter as exc:
                    log.warning("Telegram rate limit: sleeping %.1f sec", exc.retry_after)
                    await asyncio.sleep(exc.retry_after)
                except Exception:
                    log.exception("Campaign %s delivery failed for user %s", campaign["id"], uid)

            async with await connect() as db:
                await db.execute("UPDATE campaigns SET last_message_ids=?,next_at=? WHERE id=?",
                    (json.dumps(last_ids), now + campaign["interval_minutes"] * 60, campaign["id"]))
                await db.commit()
        await asyncio.sleep(15)
