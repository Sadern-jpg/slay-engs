# Slay English Telegram Bot

Python 3.11 + aiogram 3.22.0 + aiosqlite + SQLite.

## Hosting environment variables

Set these in BotHost (do not commit `.env` or a real token):

- `BOT_TOKEN` — Telegram bot token
- `ADMIN_IDS` — `1105059220,5688806795`
- `CHANNEL_ID` — `@english_slay`
- `CHANNEL_URL` — `https://t.me/english_slay`
- `DB_PATH` — `bot.db`

Add the bot as an administrator of `@english_slay` so Telegram can verify membership. Keep persistent storage for `bot.db` and run only one bot instance with this token.

## Start

```bash
pip install -r requirements.txt
python bot.py
```

The bot uses aiogram 3 polling (`Dispatcher.start_polling`) and does not use aiogram 2's executor.

## BotHost legacy build-probe compatibility

The current BotHost build log shows that its builder installs aiogram 3.22.0 and then runs `from aiogram.utils import executor`, which is an aiogram 2-era check. `sitecustomize.py` provides a harmless placeholder for that import probe only; bot runtime remains aiogram 3.22.0 and never calls executor. This shim is only a workaround for the host's build check. If BotHost changes the check, this file can be removed.

The Dockerfile uses Python 3.11 to match the BotHost runtime setting. If the host's builder ignores the custom Dockerfile, Python version selection remains controlled by the BotHost setting.

## Included features

- Welcome message and main menu (no “О проекте” button).
- Materials: add a title/description and photo, video, document, audio, or HTTPS link; list, enable/disable, delete.
- Subscription check for every material request; after successful check the selected material is delivered automatically.
- Courses: add, list, enable/disable, delete.
- Admin ad insert: text sent immediately after a material.
- Recurring broadcast: every 1/6/12/24 hours for 1/6/12/24 hours or indefinitely.
- Recurring ad: every 1/3/6/12 hours until stopped.
- Campaign management: list active campaigns and stop them.
- Previous campaign message is deleted per recipient before the next one; messages are also removed when a timed broadcast expires, where Telegram permits deletion.

Campaigns reach users who have started the bot. Telegram does not allow a bot to message users who have never started it or who have blocked it. The bot must remain online for scheduled deliveries.
