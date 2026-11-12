import os
from dataclasses import dataclass

def _int_set(value: str) -> set[int]:
    result = set()
    for part in value.split(","):
        part = part.strip()
        if part:
            result.add(int(part))
    return result

@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "").strip()
    admin_ids: set[int] = None
    channel_id: str = os.getenv("CHANNEL_ID", "@english_slay").strip()
    channel_url: str = os.getenv("CHANNEL_URL", "https://t.me/english_slay").strip()
    db_path: str = os.getenv("DB_PATH", "bot.db").strip()

settings = Settings(admin_ids=_int_set(os.getenv("ADMIN_IDS", "1105059220,5688806795")))
