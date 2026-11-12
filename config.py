import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(v.strip()) for v in os.getenv("ADMIN_IDS", "").split(",") if v.strip().isdigit()}
CHANNEL_ID = os.getenv("CHANNEL_ID", "@english_slay").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/english_slay").strip()
DB_PATH = os.getenv("DB_PATH", "bot.db").strip()
