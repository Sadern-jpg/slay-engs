from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import connect

async def deliver_material(bot,user_id:int,material_id:int):
    async with await connect() as db:
        cur=await db.execute("SELECT * FROM materials WHERE id=? AND active=1",(material_id,))
        m=await cur.fetchone()
        cur=await db.execute("SELECT value FROM settings WHERE key='ad_insert'")
        ad=await cur.fetchone()
    if not m:
        await bot.send_message(user_id,"Этот материал больше недоступен.")
        return
    caption=f"<b>{m['title']}</b>"+(f"\n{m['description']}" if m["description"] else "")
    if m["url"]:
        await bot.send_message(user_id,caption,reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть материал",url=m["url"])]]))
    elif m["file_id"]:
        method={"photo":bot.send_photo,"video":bot.send_video,"document":bot.send_document,"audio":bot.send_audio}.get(m["file_type"])
        if method:
            await method(user_id,m["file_id"],caption=caption)
        else:
            await bot.send_message(user_id,caption)
    else:
        await bot.send_message(user_id,caption)
    if ad and ad["value"]:
        await bot.send_message(user_id,ad["value"])
