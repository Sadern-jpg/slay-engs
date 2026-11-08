import time
import aiosqlite
from config import settings

async def init_db():
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.executescript('''
        CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, first_name TEXT DEFAULT '', username TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', material_type TEXT NOT NULL, url TEXT DEFAULT '', file_id TEXT DEFAULT '', active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS offers(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', url TEXT NOT NULL, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS reminders(user_id INTEGER PRIMARY KEY, due_at REAL NOT NULL, acknowledged INTEGER DEFAULT 0);
        ''')
        await db.commit()

async def add_user(user):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT INTO users(user_id,first_name,username) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name,username=excluded.username", (user.id,user.first_name or "",user.username or ""))
        await db.commit()

async def _rows(sql, args=()):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql,args)
        return await cur.fetchall()

async def get_materials(): return await _rows("SELECT * FROM materials WHERE active=1 ORDER BY id DESC")
async def get_material(mid):
    rows = await _rows("SELECT * FROM materials WHERE id=? AND active=1",(mid,))
    return rows[0] if rows else None
async def get_all_materials(): return await _rows("SELECT * FROM materials ORDER BY id DESC")
async def get_offers(): return await _rows("SELECT * FROM offers WHERE active=1 ORDER BY id DESC")
async def get_all_offers(): return await _rows("SELECT * FROM offers ORDER BY id DESC")

async def add_material(title,desc,kind,url="",file_id=""):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT INTO materials(title,description,material_type,url,file_id) VALUES(?,?,?,?,?)",(title,desc,kind,url,file_id)); await db.commit()
async def add_offer(title,desc,url):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT INTO offers(title,description,url) VALUES(?,?,?)",(title,desc,url)); await db.commit()
async def toggle_material(mid):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("UPDATE materials SET active=1-active WHERE id=?",(mid,)); await db.commit()
async def delete_material(mid):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("DELETE FROM materials WHERE id=?",(mid,)); await db.commit()
async def toggle_offer(oid):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("UPDATE offers SET active=1-active WHERE id=?",(oid,)); await db.commit()
async def delete_offer(oid):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("DELETE FROM offers WHERE id=?",(oid,)); await db.commit()

async def schedule_reminder(uid):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO reminders(user_id,due_at,acknowledged) VALUES(?,?,0)",(uid,time.time()+settings.REMINDER_HOURS*3600)); await db.commit()
async def due_reminders():
    return await _rows("SELECT user_id FROM reminders WHERE acknowledged=0 AND due_at<=?",(time.time(),))
async def postpone_reminder(uid):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("UPDATE reminders SET due_at=? WHERE user_id=? AND acknowledged=0",(time.time()+settings.REMINDER_HOURS*3600,uid)); await db.commit()
async def acknowledge_reminder(uid):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("UPDATE reminders SET acknowledged=1 WHERE user_id=?",(uid,)); await db.commit()
async def get_user_ids():
    rows = await _rows("SELECT user_id FROM users")
    return [r["user_id"] for r in rows]
async def get_stats():
    async with aiosqlite.connect(settings.DB_PATH) as db:
        a=await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        b=await (await db.execute("SELECT COUNT(*) FROM materials WHERE active=1")).fetchone()
        c=await (await db.execute("SELECT COUNT(*) FROM offers WHERE active=1")).fetchone()
        return a[0],b[0],c[0]
