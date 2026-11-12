import aiosqlite
from config import DB_PATH

async def db():
    x=await aiosqlite.connect(DB_PATH); x.row_factory=aiosqlite.Row
    return x

async def init_db():
    async with await db() as x:
        await x.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, first_name TEXT);
        CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT, descr TEXT, file_id TEXT, file_type TEXT, url TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS campaigns(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, ctype TEXT, body TEXT, file_id TEXT, buttons TEXT, interval_h INTEGER, duration_h INTEGER, started REAL, active INTEGER DEFAULT 1, last_sent REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS deliveries(campaign_id INTEGER, user_id INTEGER, message_id INTEGER, PRIMARY KEY(campaign_id,user_id));
        """)
        await x.commit()

async def add_user(u):
    async with await db() as x:
        await x.execute("INSERT INTO users VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name",(u.id,u.username,u.first_name)); await x.commit()
async def users():
    async with await db() as x: return [r[0] for r in await (await x.execute("SELECT id FROM users")).fetchall()]
async def add_item(kind,title,descr,fid,ftype,url):
    async with await db() as x:
        await x.execute("INSERT INTO items(kind,title,descr,file_id,file_type,url) VALUES(?,?,?,?,?,?)",(kind,title,descr,fid,ftype,url)); await x.commit()
async def items(kind):
    async with await db() as x: return await (await x.execute("SELECT * FROM items WHERE kind=? ORDER BY id DESC",(kind,))).fetchall()
async def item(i):
    async with await db() as x: return await (await x.execute("SELECT * FROM items WHERE id=? AND active=1",(i,))).fetchone()
async def delete_item(i):
    async with await db() as x:
        await x.execute("DELETE FROM items WHERE id=?",(i,)); await x.commit()

async def toggle(i):
    async with await db() as x:
        await x.execute("UPDATE items SET active=1-active WHERE id=?",(i,)); await x.commit()
async def create_campaign(kind,ctype,body,fid,buttons,interval,duration):
    import time
    async with await db() as x:
        await x.execute("UPDATE campaigns SET active=0 WHERE kind=?",(kind,))
        await x.execute("INSERT INTO campaigns(kind,ctype,body,file_id,buttons,interval_h,duration_h,started,active,last_sent) VALUES(?,?,?,?,?,?,?,?,1,0)",(kind,ctype,body,fid,buttons,interval,duration,time.time()))
        await x.commit()
async def campaigns():
    async with await db() as x: return await (await x.execute("SELECT * FROM campaigns WHERE active=1")).fetchall()
async def previous(cid,uid):
    async with await db() as x: return await (await x.execute("SELECT message_id FROM deliveries WHERE campaign_id=? AND user_id=?",(cid,uid))).fetchone()
async def remember(cid,uid,mid):
    async with await db() as x:
        await x.execute("INSERT INTO deliveries VALUES(?,?,?) ON CONFLICT(campaign_id,user_id) DO UPDATE SET message_id=excluded.message_id",(cid,uid,mid)); await x.commit()
async def deactivate(cid):
    async with await db() as x: await x.execute("UPDATE campaigns SET active=0 WHERE id=?",(cid,)); await x.commit()
async def stamp(cid,ts):
    async with await db() as x: await x.execute("UPDATE campaigns SET last_sent=? WHERE id=?",(ts,cid)); await x.commit()
async def stats():
    async with await db() as x:
        a=await (await x.execute("SELECT COUNT(*) FROM users")).fetchone()
        b=await (await x.execute("SELECT COUNT(*) FROM items WHERE kind='material' AND active=1")).fetchone()
        c=await (await x.execute("SELECT COUNT(*) FROM items WHERE kind='course' AND active=1")).fetchone()
        return a[0],b[0],c[0]
