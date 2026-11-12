import os
import aiosqlite
from config import DB_PATH


def _ensure_parent():
    parent = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(parent, exist_ok=True)


async def connect():
    _ensure_parent()
    db = await aiosqlite.connect(DB_PATH, timeout=30)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA busy_timeout=30000")
    await db.execute("PRAGMA journal_mode=WAL")
    return db


async def _columns(db, table):
    rows = await (await db.execute(f"PRAGMA table_info({table})")).fetchall()
    return {row["name"] for row in rows}


async def init_db():
    """Create tables and add new columns without deleting existing user data."""
    async with await connect() as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            created_at REAL DEFAULT (strftime('%s','now')),
            is_blocked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
            title TEXT NOT NULL, descr TEXT DEFAULT '', file_id TEXT,
            file_type TEXT, url TEXT, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
            ctype TEXT NOT NULL, body TEXT DEFAULT '', file_id TEXT,
            buttons TEXT DEFAULT '[]', interval_h INTEGER NOT NULL,
            duration_h INTEGER, started REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1, last_sent REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS deliveries (
            campaign_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL, PRIMARY KEY(campaign_id,user_id)
        );
        """)
        # Safe additive migrations for databases created by earlier releases.
        user_cols = await _columns(db, "users")
        if "is_blocked" not in user_cols:
            await db.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER NOT NULL DEFAULT 0")
        item_cols = await _columns(db, "items")
        for name, definition in {
            "kind": "TEXT NOT NULL DEFAULT 'material'", "title": "TEXT NOT NULL DEFAULT ''",
            "descr": "TEXT DEFAULT ''", "file_id": "TEXT", "file_type": "TEXT",
            "url": "TEXT", "active": "INTEGER NOT NULL DEFAULT 1",
        }.items():
            if name not in item_cols:
                await db.execute(f"ALTER TABLE items ADD COLUMN {name} {definition}")
        campaign_cols = await _columns(db, "campaigns")
        for name, definition in {
            "kind": "TEXT NOT NULL DEFAULT 'broadcast'", "ctype": "TEXT NOT NULL DEFAULT 'text'",
            "body": "TEXT DEFAULT ''", "file_id": "TEXT", "buttons": "TEXT DEFAULT '[]'",
            "interval_h": "INTEGER NOT NULL DEFAULT 24", "duration_h": "INTEGER",
            "started": "REAL NOT NULL DEFAULT 0", "active": "INTEGER NOT NULL DEFAULT 1",
            "last_sent": "REAL DEFAULT 0",
        }.items():
            if name not in campaign_cols:
                await db.execute(f"ALTER TABLE campaigns ADD COLUMN {name} {definition}")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_items_kind_active ON items(kind, active)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_active ON campaigns(active, kind)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_blocked ON users(is_blocked)")
        await db.commit()


async def add_user(user):
    async with await connect() as db:
        await db.execute("""INSERT INTO users(id,username,first_name,is_blocked) VALUES(?,?,?,0)
        ON CONFLICT(id) DO UPDATE SET username=excluded.username,
        first_name=excluded.first_name,is_blocked=0""",
        (user.id, user.username, user.first_name))
        await db.commit()


async def get_users():
    async with await connect() as db:
        rows = await (await db.execute("SELECT id FROM users WHERE is_blocked=0 ORDER BY id")).fetchall()
        return [r["id"] for r in rows]


async def mark_user_blocked(user_id):
    async with await connect() as db:
        await db.execute("UPDATE users SET is_blocked=1 WHERE id=?", (user_id,))
        await db.commit()


async def add_item(kind, title, descr, file_id=None, file_type=None, url=None):
    async with await connect() as db:
        cur = await db.execute("INSERT INTO items(kind,title,descr,file_id,file_type,url) VALUES(?,?,?,?,?,?)",
                                (kind, title, descr or "", file_id, file_type, url))
        await db.commit()
        return cur.lastrowid


async def get_items(kind, active_only=False):
    sql = "SELECT * FROM items WHERE kind=?"
    if active_only:
        sql += " AND active=1"
    sql += " ORDER BY id DESC"
    async with await connect() as db:
        return await (await db.execute(sql, (kind,))).fetchall()


async def get_item(item_id):
    async with await connect() as db:
        return await (await db.execute("SELECT * FROM items WHERE id=? AND active=1", (item_id,))).fetchone()


async def toggle_item(item_id):
    async with await connect() as db:
        await db.execute("UPDATE items SET active=CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?", (item_id,))
        await db.commit()


async def delete_item(item_id):
    async with await connect() as db:
        await db.execute("DELETE FROM items WHERE id=?", (item_id,))
        await db.commit()


async def create_campaign(kind, ctype, body, file_id, buttons, interval_h, duration_h):
    import time
    async with await connect() as db:
        await db.execute("UPDATE campaigns SET active=0 WHERE kind=?", (kind,))
        cur = await db.execute("""INSERT INTO campaigns
        (kind,ctype,body,file_id,buttons,interval_h,duration_h,started,active,last_sent)
        VALUES(?,?,?,?,?,?,?,?,1,0)""",
        (kind, ctype, body or "", file_id, buttons or "[]", interval_h, duration_h, time.time()))
        await db.commit()
        return cur.lastrowid


async def get_campaigns():
    async with await connect() as db:
        return await (await db.execute("SELECT * FROM campaigns WHERE active=1 ORDER BY id")).fetchall()


async def get_all_campaigns():
    async with await connect() as db:
        return await (await db.execute("SELECT * FROM campaigns ORDER BY id DESC LIMIT 30")).fetchall()


async def get_previous(campaign_id, user_id):
    async with await connect() as db:
        return await (await db.execute("SELECT message_id FROM deliveries WHERE campaign_id=? AND user_id=?",
                                      (campaign_id, user_id))).fetchone()


async def save_delivery(campaign_id, user_id, message_id):
    async with await connect() as db:
        await db.execute("""INSERT INTO deliveries(campaign_id,user_id,message_id) VALUES(?,?,?)
        ON CONFLICT(campaign_id,user_id) DO UPDATE SET message_id=excluded.message_id""",
        (campaign_id, user_id, message_id))
        await db.commit()


async def deactivate_campaign(campaign_id):
    async with await connect() as db:
        await db.execute("UPDATE campaigns SET active=0 WHERE id=?", (campaign_id,))
        await db.commit()


async def update_last_sent(campaign_id, timestamp):
    async with await connect() as db:
        await db.execute("UPDATE campaigns SET last_sent=? WHERE id=?", (timestamp, campaign_id))
        await db.commit()


async def get_stats():
    async with await connect() as db:
        users = (await (await db.execute("SELECT COUNT(*) n FROM users WHERE is_blocked=0")).fetchone())["n"]
        materials = (await (await db.execute("SELECT COUNT(*) n FROM items WHERE kind='material' AND active=1")).fetchone())["n"]
        courses = (await (await db.execute("SELECT COUNT(*) n FROM items WHERE kind='course' AND active=1")).fetchone())["n"]
        return users, materials, courses
