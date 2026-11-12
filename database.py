import aiosqlite
from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS materials (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '',
  file_id TEXT, file_type TEXT, url TEXT, active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '',
  url TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, chat_id INTEGER NOT NULL,
  message_id INTEGER NOT NULL, interval_minutes INTEGER NOT NULL, duration_minutes INTEGER,
  started_at REAL NOT NULL, next_at REAL NOT NULL, expires_at REAL,
  active INTEGER NOT NULL DEFAULT 1, last_message_ids TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS users_pending (user_id INTEGER PRIMARY KEY, material_id INTEGER NOT NULL);
"""

async def connect():
    db = await aiosqlite.connect(settings.db_path, timeout=30)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db

async def init_db():
    async with await connect() as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def set_value(key: str, value: str):
    async with await connect() as db:
        await db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        await db.commit()

async def get_value(key: str):
    async with await connect() as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else None
