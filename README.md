# Slay English Telegram Bot

Python 3.12 + aiogram 3 + SQLite.

## Hosting variables
Set these in the hosting dashboard (do not commit `.env`):
- `BOT_TOKEN` — current Telegram bot token
- `ADMIN_IDS` — `1105059220,5688806795`
- `CHANNEL_ID` — `@english_slay`
- `CHANNEL_URL` — `https://t.me/english_slay`
- `DB_PATH` — `bot.db`

Add the bot as an administrator of `@english_slay` so Telegram can verify membership.

## Run
`pip install -r requirements.txt`
`python bot.py`

Docker start command is already `python bot.py`. This project uses aiogram 3 and does not use the removed aiogram 2 `executor`.

## Notes
- Keep a persistent disk/volume mounted for `bot.db`; otherwise SQLite data may be lost on redeploy.
- Only one running instance should poll this bot token.
- Admin IDs are configured in `config.py` defaults and can be overridden with `ADMIN_IDS`.

## Included admin workflows
- Materials: add, list, enable/disable, delete.
- Courses: add, list, enable/disable, delete.
- Broadcast: choose 1/6/12/24-hour interval and 1/6/12/24-hour or unlimited duration.
- Recurring ad: choose 1/3/6/12-hour interval; runs until the campaign is stopped in the database.
- Ad insert: plain-text insert after material delivery; send `/disable_insert` in the setup flow to clear it.

The current admin UI does not yet include a campaign stop/list screen. To stop a recurring campaign, set its `active` field to `0` in SQLite. Campaign sends are repeated to users who have started the bot. Telegram may reject delivery to users who blocked the bot.
