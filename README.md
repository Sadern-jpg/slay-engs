# Slay English Telegram bot

Python 3.11 + aiogram 3.22.0 + SQLite. This project uses long polling and is intended to run as one always-on worker/container.

## Required environment variables

- `BOT_TOKEN` — token from BotFather
- `ADMIN_IDS` — comma-separated Telegram numeric IDs, e.g. `1105059220,5688806795`
- `CHANNEL_ID` — channel username, e.g. `@english_slay`
- `CHANNEL_URL` — public channel URL, e.g. `https://t.me/english_slay`
- `DB_PATH` — path to SQLite database. On a host with a persistent volume mounted at `/data`, set `/data/bot.db`.

Do not commit `.env` or your real token to GitHub.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export BOT_TOKEN="..."     # Windows PowerShell: $env:BOT_TOKEN="..."
export ADMIN_IDS="1105059220,5688806795"
export CHANNEL_ID="@english_slay"
export CHANNEL_URL="https://t.me/english_slay"
export DB_PATH="bot.db"
python bot.py
```

## Deployment notes

Deploy as a single always-on worker using the Dockerfile (or the Procfile command `python bot.py`). Attach persistent storage and set `DB_PATH` to a file on that volume (for example `/data/bot.db`). Do not run multiple replicas: SQLite and Telegram long polling are intended for one worker instance.

The application does not require `aiogram.utils.executor`; that API belongs to aiogram 2 and is not used by this aiogram 3 project.
