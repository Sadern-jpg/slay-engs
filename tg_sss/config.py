import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
    ADMIN_IDS: tuple = tuple(int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip())
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "@english_slay").strip()
    CHANNEL_URL: str = os.getenv("CHANNEL_URL", "https://t.me/english_slay").strip()
    DB_PATH: str = os.getenv("DB_PATH", "bot.db").strip()
    REMINDER_HOURS: int = int(os.getenv("REMINDER_HOURS", "24"))

settings = Settings()
