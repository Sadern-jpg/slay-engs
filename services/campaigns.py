import asyncio
import json
import logging
import time
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import (
    TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter,
    TelegramNetworkError, TelegramServerError,
)
from database.db import (
    get_campaigns, get_users, get_previous, save_delivery,
    deactivate_campaign, update_last_sent, mark_user_blocked,
)

log = logging.getLogger(__name__)


def make_markup(raw):
    try:
        links = json.loads(raw or "[]")
        rows = []
        for link in links:
            label, url = link.get("text"), link.get("url")
            if label and url and url.startswith(("https://", "http://")):
                rows.append([InlineKeyboardButton(text=label[:64], url=url)])
        return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
    except (TypeError, ValueError, AttributeError):
        log.exception("Invalid campaign buttons JSON")
        return None


async def _send_new_message(bot, campaign, user_id, markup):
    body = campaign["body"] or None
    ctype = campaign["ctype"]
    if ctype == "photo":
        return await bot.send_photo(user_id, campaign["file_id"], caption=body, reply_markup=markup)
    if ctype == "video":
        return await bot.send_video(user_id, campaign["file_id"], caption=body, reply_markup=markup)
    if ctype == "document":
        return await bot.send_document(user_id, campaign["file_id"], caption=body, reply_markup=markup)
    if ctype == "audio":
        return await bot.send_audio(user_id, campaign["file_id"], caption=body, reply_markup=markup)
    if ctype == "animation":
        return await bot.send_animation(user_id, campaign["file_id"], caption=body, reply_markup=markup)
    return await bot.send_message(user_id, body or " ", reply_markup=markup)


async def send_campaign_message(bot, campaign, user_id):
    """Send first; only replace the previous message after the new send succeeds."""
    markup = make_markup(campaign["buttons"])
    new_message = await _send_new_message(bot, campaign, user_id, markup)
    previous = await get_previous(campaign["id"], user_id)
    await save_delivery(campaign["id"], user_id, new_message.message_id)
    if previous and previous["message_id"] != new_message.message_id:
        try:
            await bot.delete_message(user_id, previous["message_id"])
        except (TelegramBadRequest, TelegramForbiddenError):
            # A failed deletion must never prevent delivery of the new campaign message.
            log.info("Could not delete previous campaign message for user %s", user_id)
    return new_message


async def send_insert_ad(bot, user_id):
    for campaign in await get_campaigns():
        if campaign["kind"] != "insert":
            continue
        try:
            await send_campaign_message(bot, campaign, user_id)
        except TelegramForbiddenError:
            await mark_user_blocked(user_id)
        except Exception:
            log.exception("Insert ad failed for user %s", user_id)


async def _send_to_user_with_retry(bot, campaign, user_id):
    for attempt in range(3):
        try:
            await send_campaign_message(bot, campaign, user_id)
            return True
        except TelegramRetryAfter as exc:
            # Respect Telegram's flood-control wait, with a bounded number of retries.
            if attempt == 2:
                log.warning("Flood control: giving up user %s for campaign %s", user_id, campaign["id"])
                return False
            await asyncio.sleep(exc.retry_after + 1)
        except TelegramForbiddenError:
            await mark_user_blocked(user_id)
            return False
        except (TelegramNetworkError, TelegramServerError):
            if attempt == 2:
                log.exception("Temporary Telegram error for user %s", user_id)
                return False
            await asyncio.sleep(2 ** attempt)
        except TelegramBadRequest as exc:
            log.warning("Telegram rejected campaign %s for user %s: %s", campaign["id"], user_id, exc)
            return False
        except Exception:
            log.exception("Campaign %s failed for user %s", campaign["id"], user_id)
            return False
    return False


async def campaign_worker(bot):
    while True:
        now = time.time()
        try:
            campaigns = await get_campaigns()
            users = None
            for campaign in campaigns:
                if campaign["kind"] == "insert":
                    continue
                duration = campaign["duration_h"]
                if duration is not None and now >= campaign["started"] + duration * 3600:
                    await deactivate_campaign(campaign["id"])
                    continue
                if now - (campaign["last_sent"] or 0) < campaign["interval_h"] * 3600:
                    continue
                if users is None:
                    users = await get_users()
                for user_id in users:
                    await _send_to_user_with_retry(bot, campaign, user_id)
                    await asyncio.sleep(0.05)
                # Advance schedule after the full audience pass, not after each user.
                await update_last_sent(campaign["id"], time.time())
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Campaign worker iteration failed")
        await asyncio.sleep(15)
