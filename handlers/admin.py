import time
from aiogram import Router,F
from aiogram.types import Message,CallbackQuery
from aiogram.fsm.state import StatesGroup,State
from aiogram.fsm.context import FSMContext
from config import settings
from database import connect,set_value
from keyboards import admin_menu,inline

router=Router()
def admin(uid): return uid in settings.admin_ids
def payload(m): return bool(m.text or m.photo or m.video or m.document or m.audio or m.animation or m.voice or m.video_note or m.sticker)

class Material(StatesGroup): title=State(); description=State(); content=State()
class Course(StatesGroup): title=State(); description=State(); url=State()
class Insert(StatesGroup): content=State()
class Campaign(StatesGroup): content=State(); interval=State(); duration=State()
class Ad(StatesGroup): content=State(); interval=State()

@router.message(F.text=="⚙️ Админ-панель")
async def home(m:Message):
    if admin(m.from_user.id): await m.answer("Панель управления:",reply_markup=admin_menu())

@router.message(F.text=="📦 Управление материалами")
async def mats(m:Message):
    if admin(m.from_user.id): await m.answer("Материалы:",reply_markup=inline([("Добавить","add"),("Список","list")],"matadm"))

@router.callback_query(F.data=="matadm:add")
async def mat_add(c:CallbackQuery,s:FSMContext):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    await s.set_state(Material.title); await c.message.answer("Название материала:"); await c.answer()

@router.message(Material.title)
async def mat_title(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if not m.text: await m.answer("Напиши название текстом."); return
    await s.update_data(title=m.text.strip()); await s.set_state(Material.description); await m.answer("Описание или точка, если без описания:")

@router.message(Material.description)
async def mat_desc(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if m.text is None: await m.answer("Пришли описание текстом."); return
    await s.update_data(description="" if m.text.strip()=="." else m.html_text); await s.set_state(Material.content)
    await m.answer("Пришли фото, видео, документ, аудио или ссылку https://")

@router.message(Material.content)
async def mat_content(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    d=await s.get_data(); fid=ft=url=None
    if m.photo: fid,ft=m.photo[-1].file_id,"photo"
    elif m.video: fid,ft=m.video.file_id,"video"
    elif m.document: fid,ft=m.document.file_id,"document"
    elif m.audio: fid,ft=m.audio.file_id,"audio"
    elif m.text and m.text.startswith("https://"): url=m.text.strip()
    else: await m.answer("Нужен файл или https-ссылка."); return
    async with await connect() as db:
        await db.execute("INSERT INTO materials(title,description,file_id,file_type,url) VALUES(?,?,?,?,?)",(d["title"],d["description"],fid,ft,url)); await db.commit()
    await s.clear(); await m.answer("Материал добавлен 💗",reply_markup=admin_menu())

@router.callback_query(F.data=="matadm:list")
async def mat_list(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    async with await connect() as db:
        rows=await (await db.execute("SELECT id,title,active FROM materials ORDER BY id DESC")).fetchall()
    if not rows: await c.message.answer("Материалов пока нет.")
    for r in rows:
        await c.message.answer(f"#{r['id']} {r['title']} · {'активен' if r['active'] else 'выключен'}",reply_markup=inline([("Вкл/выкл",f"toggle:{r['id']}"),("Удалить","delete:"+str(r["id"]))],"mat"))
    await c.answer()

@router.callback_query(F.data.startswith("mat:toggle:"))
async def mat_toggle(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    mid=int(c.data.rsplit(":",1)[1])
    async with await connect() as db: await db.execute("UPDATE materials SET active=1-active WHERE id=?",(mid,)); await db.commit()
    await c.answer("Статус изменён")

@router.callback_query(F.data.startswith("mat:delete:"))
async def mat_delete(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    mid=int(c.data.rsplit(":",1)[1])
    async with await connect() as db: await db.execute("DELETE FROM materials WHERE id=?",(mid,)); await db.commit()
    await c.answer("Материал удалён")

@router.message(F.text=="🎓 Управление курсами")
async def course_menu(m:Message):
    if admin(m.from_user.id): await m.answer("Курсы:",reply_markup=inline([("Добавить","add"),("Список","list")],"courseadm"))

@router.callback_query(F.data=="courseadm:add")
async def course_add(c:CallbackQuery,s:FSMContext):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    await s.set_state(Course.title); await c.message.answer("Название курса:"); await c.answer()

@router.message(Course.title)
async def course_title(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if not m.text: await m.answer("Название текстом."); return
    await s.update_data(title=m.text.strip()); await s.set_state(Course.description); await m.answer("Описание или точка:")

@router.message(Course.description)
async def course_desc(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if m.text is None: await m.answer("Описание текстом."); return
    await s.update_data(description="" if m.text.strip()=="." else m.html_text); await s.set_state(Course.url); await m.answer("Ссылка курса https://")

@router.message(Course.url)
async def course_url(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if not m.text or not m.text.startswith("https://"): await m.answer("Нужна https-ссылка."); return
    d=await s.get_data()
    async with await connect() as db: await db.execute("INSERT INTO courses(title,description,url) VALUES(?,?,?)",(d["title"],d["description"],m.text.strip())); await db.commit()
    await s.clear(); await m.answer("Курс добавлен 💗",reply_markup=admin_menu())

@router.callback_query(F.data=="courseadm:list")
async def course_list(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    async with await connect() as db: rows=await (await db.execute("SELECT id,title,active FROM courses ORDER BY id DESC")).fetchall()
    if not rows: await c.message.answer("Курсов пока нет.")
    for r in rows: await c.message.answer(f"#{r['id']} {r['title']} · {'активен' if r['active'] else 'выключен'}",reply_markup=inline([("Вкл/выкл",f"toggle:{r['id']}"),("Удалить",r['id'])],"course"))
    await c.answer()

@router.callback_query(F.data.startswith("course:toggle:"))
async def course_toggle(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    cid=int(c.data.rsplit(":",1)[1])
    async with await connect() as db: await db.execute("UPDATE courses SET active=1-active WHERE id=?",(cid,)); await db.commit()
    await c.answer("Статус изменён")

@router.callback_query(F.data.startswith("course:delete:"))
async def course_delete(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    cid=int(c.data.rsplit(":",1)[1])
    async with await connect() as db: await db.execute("DELETE FROM courses WHERE id=?",(cid,)); await db.commit()
    await c.answer("Курс удалён")

@router.callback_query(F.data.startswith("courseurl:"))
async def course_open(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Ссылка курса находится в сообщении.",show_alert=True); return
    await c.answer()

@router.message(F.text=="🧩 Рекламная вставка")
async def insert_start(m:Message,s:FSMContext):
    if admin(m.from_user.id): await s.set_state(Insert.content); await m.answer("Отправь текст вставки. /disable_insert — отключить.")

@router.message(Insert.content,F.text=="/disable_insert")
async def insert_off(m:Message,s:FSMContext):
    if admin(m.from_user.id): await set_value("ad_insert",""); await s.clear(); await m.answer("Вставка отключена.",reply_markup=admin_menu())

@router.message(Insert.content)
async def insert_save(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if not m.text: await m.answer("Пока поддерживается текст. Пришли текст."); return
    await set_value("ad_insert",m.html_text); await s.clear(); await m.answer("Вставка сохранена 💗",reply_markup=admin_menu())

@router.message(F.text=="📨 Рассылка")
async def campaign_start(m:Message,s:FSMContext):
    if admin(m.from_user.id): await s.set_state(Campaign.content); await m.answer("Отправь контент рассылки.")

@router.message(Campaign.content)
async def campaign_content(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if not payload(m): await m.answer("Пришли сообщение с контентом."); return
    await s.update_data(chat_id=m.chat.id,message_id=m.message_id); await s.set_state(Campaign.interval)
    await m.answer("Интервал:",reply_markup=inline([("1 час",60),("6 часов",360),("12 часов",720),("24 часа",1440)],"campint"))

@router.callback_query(F.data.startswith("campint:"))
async def campaign_interval(c:CallbackQuery,s:FSMContext):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    if await s.get_state()!=Campaign.interval.state: await c.answer("Шаг устарел",show_alert=True); return
    await s.update_data(interval=int(c.data.split(":")[1])); await s.set_state(Campaign.duration)
    await c.message.answer("Срок:",reply_markup=inline([("1 час",60),("6 часов",360),("12 часов",720),("24 часа",1440),("Бессрочно","forever")],"campdur")); await c.answer()

@router.callback_query(F.data.startswith("campdur:"))
async def campaign_duration(c:CallbackQuery,s:FSMContext):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    if await s.get_state()!=Campaign.duration.state: await c.answer("Шаг устарел",show_alert=True); return
    d=await s.get_data(); val=c.data.split(":")[1]; duration=None if val=="forever" else int(val); now=time.time()
    async with await connect() as db:
        await db.execute("INSERT INTO campaigns(kind,chat_id,message_id,interval_minutes,duration_minutes,started_at,next_at,expires_at) VALUES('broadcast',?,?,?,?,?,?,?)",(d["chat_id"],d["message_id"],d["interval"],duration,now,now,None if duration is None else now+duration*60)); await db.commit()
    await s.clear(); await c.message.answer("Рассылка запущена.",reply_markup=admin_menu()); await c.answer()

@router.message(F.text=="📢 Реклама")
async def ad_start(m:Message,s:FSMContext):
    if admin(m.from_user.id): await s.set_state(Ad.content); await m.answer("Отправь рекламное сообщение.")

@router.message(Ad.content)
async def ad_content(m:Message,s:FSMContext):
    if not admin(m.from_user.id): return
    if not payload(m): await m.answer("Пришли сообщение с контентом."); return
    await s.update_data(chat_id=m.chat.id,message_id=m.message_id); await s.set_state(Ad.interval)
    await m.answer("Интервал рекламы:",reply_markup=inline([("1 час",60),("3 часа",180),("6 часов",360),("12 часов",720)],"adint"))

@router.callback_query(F.data.startswith("adint:"))
async def ad_interval(c:CallbackQuery,s:FSMContext):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    if await s.get_state()!=Ad.interval.state: await c.answer("Шаг устарел",show_alert=True); return
    d=await s.get_data(); now=time.time()
    async with await connect() as db:
        await db.execute("INSERT INTO campaigns(kind,chat_id,message_id,interval_minutes,duration_minutes,started_at,next_at,expires_at) VALUES('ad',?,?,?,?,?,?,NULL)",(d["chat_id"],d["message_id"],int(c.data.split(":")[1]),None,now,now)); await db.commit()
    await s.clear(); await c.message.answer("Реклама запущена.",reply_markup=admin_menu()); await c.answer()

@router.message(F.text=="🛑 Кампании")
async def campaign_list(m:Message):
    if not admin(m.from_user.id): return
    async with await connect() as db: rows=await (await db.execute("SELECT id,kind,interval_minutes FROM campaigns WHERE active=1 ORDER BY id DESC")).fetchall()
    if not rows: await m.answer("Активных кампаний нет."); return
    for r in rows:
        await m.answer(f"Кампания #{r['id']} · {r['kind']} · {r['interval_minutes']} мин.",reply_markup=inline([("Остановить",r["id"])],"campstop"))

@router.callback_query(F.data.startswith("campstop:"))
async def campaign_stop(c:CallbackQuery):
    if not admin(c.from_user.id): await c.answer("Нет доступа",show_alert=True); return
    cid=int(c.data.split(":")[1])
    async with await connect() as db: await db.execute("UPDATE campaigns SET active=0 WHERE id=?",(cid,)); await db.commit()
    await c.answer("Кампания остановлена")
