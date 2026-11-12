import asyncio,time,json
from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
from database.db import campaigns,users,previous,remember,deactivate,stamp

def markup(raw):
 try:
  a=json.loads(raw or "[]")
  rows=[[InlineKeyboardButton(text=x["text"],url=x["url"])] for x in a if x.get("text") and x.get("url")]
  return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
 except Exception:return None

async def deliver(bot,c,u):
 old=await previous(c["id"],u)
 if old:
  try: await bot.delete_message(u,old["message_id"])
  except Exception: pass
 kb=markup(c["buttons"])
 if c["ctype"]=="photo": m=await bot.send_photo(u,c["file_id"],caption=c["body"] or None,reply_markup=kb)
 elif c["ctype"]=="video": m=await bot.send_video(u,c["file_id"],caption=c["body"] or None,reply_markup=kb)
 elif c["ctype"]=="document": m=await bot.send_document(u,c["file_id"],caption=c["body"] or None,reply_markup=kb)
 elif c["ctype"]=="animation": m=await bot.send_animation(u,c["file_id"],caption=c["body"] or None,reply_markup=kb)
 elif c["ctype"]=="audio": m=await bot.send_audio(u,c["file_id"],caption=c["body"] or None,reply_markup=kb)
 elif c["ctype"]=="voice": m=await bot.send_voice(u,c["file_id"],reply_markup=kb)
 else: m=await bot.send_message(u,c["body"] or " ",reply_markup=kb)
 await remember(c["id"],u,m.message_id)

async def insert_ad(bot,uid):
 for c in await campaigns():
  if c["kind"] == "insert":
   try: await deliver(bot,c,uid)
   except Exception: pass

async def worker(bot):
 while True:
  now=time.time()
  for c in await campaigns():
   if c["kind"] == "insert": continue
   if c["duration_h"] and now>=c["started"]+c["duration_h"]*3600:
    await deactivate(c["id"]); continue
   if now-c["last_sent"] < c["interval_h"]*3600: continue
   for uid in await users():
    try: await deliver(bot,c,uid)
    except Exception: pass
   await stamp(c["id"],now)
  await asyncio.sleep(20)
