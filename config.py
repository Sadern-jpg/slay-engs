import os
from dataclasses import dataclass

def parse_admins(raw: str) -> set[int]:
    return {int(x.strip()) for x in raw.split(",") if x.strip()}

@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "").strip()
    admin_ids: set[int] = None
    channel_id: str = os.getenv("CHANNEL_ID", "@english_slay").strip()
    channel_url: str = os.getenv("CHANNEL_URL", "https://t.me/english_slay").strip()
    db_path: str = os.getenv("DB_PATH", "/data/bot.db").strip() or "/data/bot.db"

settings = Settings(admin_ids=parse_admins(os.getenv("ADMIN_IDS", "1105059220,5688806795")))
