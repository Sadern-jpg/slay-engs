from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from config import settings
from database import connect, set_value
from keyboards import admin_menu, main_menu, inline
import json

router = Router()

class MaterialFlow(StatesGroup):
    title = State(); description = State(); content = State()
class CourseFlow(StatesGroup):
    title = State(); description = State(); url = State()
class AdFlow(StatesGroup):
    insert_content = State()
    ad_content = State()
    ad_interval = State()
class CampaignFlow(StatesGroup):
    content = State(); interval = State(); duration = State()

def is_admin(user_id): return user_id in settings.admin_ids

async def safe_edit(message, text, **kwargs):
    try:
        await message.edit_text(text, **kwargs)
    except Exception as exc:
        if "message is not modified" not in str(exc).lower():
            raise

@router.message(F.text == "⚙️ Админ-панель")
async def admin_home(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Панель управления:", reply_markup=admin_menu())

@router.message(F.text == "⬅️ В меню")
async def admin_back(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Главное меню:", reply_markup=main_menu(True))

@router.message(F.text == "📦 Управление материалами")
async def material_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Управление материалами:", reply_markup=inline([("➕ Добавить материал","add"),("📋 Список материалов","list")],"matadm"))

@router.callback_query(F.data == "matadm:add")
async def add_material(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(MaterialFlow.title); await callback.message.answer("Напиши название материала:"); await callback.answer()

@router.message(MaterialFlow.title)
async def material_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip()); await state.set_state(MaterialFlow.description)
    await message.answer("Напиши описание материала (или отправь точку, если без описания):")

@router.message(MaterialFlow.description)
async def material_desc(message: Message, state: FSMContext):
    await state.update_data(description="" if message.text=="." else message.text); await state.set_state(MaterialFlow.content)
    await message.answer("Теперь отправь файл (фото, видео, документ, аудио) или ссылку, начинающуюся с https://")

@router.message(MaterialFlow.content)
async def material_content(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = file_type = url = None
    if message.photo: file_id=message.photo[-1].file_id; file_type="photo"
    elif message.video: file_id=message.video.file_id; file_type="video"
    elif message.document: file_id=message.document.file_id; file_type="document"
    elif message.audio: file_id=message.audio.file_id; file_type="audio"
    elif message.text and message.text.startswith("https://"): url=message.text.strip()
    else:
        await message.answer("Не распознал файл или ссылку. Попробуй ещё раз."); return
    async with await connect() as db:
        await db.execute("INSERT INTO materials(title,description,file_id,file_type,url) VALUES(?,?,?,?,?)",
                         (data["title"],data["description"],file_id,file_type,url)); await db.commit()
    await state.clear(); await message.answer("Материал добавлен 💗", reply_markup=admin_menu())

@router.callback_query(F.data == "matadm:list")
async def list_materials(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    async with await connect() as db:
        cur=await db.execute("SELECT id,title,active FROM materials ORDER BY id DESC"); rows=await cur.fetchall()
    if not rows: await callback.message.answer("Материалов пока нет.")
    for r in rows:
        status="включён" if r["active"] else "выключен"
        await callback.message.answer(f"{r['id']}. {r['title']} — {status}",
            reply_markup=inline([("Вкл/выкл",f"toggle:{r['id']}"),("Удалить",f"delete:{r['id']}")],"mat"))
    await callback.answer()

@router.callback_query(F.data.startswith("mat:toggle:"))
async def toggle_material(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    mid=int(callback.data.split(":")[2])
    async with await connect() as db:
        await db.execute("UPDATE materials SET active=1-active WHERE id=?",(mid,)); await db.commit()
    await callback.answer("Статус изменён")

@router.callback_query(F.data.startswith("mat:delete:"))
async def delete_material(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    mid=int(callback.data.split(":")[2])
    async with await connect() as db:
        await db.execute("DELETE FROM materials WHERE id=?",(mid,)); await db.commit()
    await callback.answer("Удалено")

@router.message(F.text == "🎓 Управление курсами")
async def course_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Управление курсами:", reply_markup=inline([("➕ Добавить курс","add"),("📋 Список курсов","list")],"courseadm"))

@router.callback_query(F.data == "courseadm:add")
async def add_course(callback: CallbackQuery,state:FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(CourseFlow.title); await callback.message.answer("Название курса:"); await callback.answer()

@router.message(CourseFlow.title)
async def course_title(message:Message,state:FSMContext):
    await state.update_data(title=message.text); await state.set_state(CourseFlow.description); await message.answer("Описание курса (или точка):")

@router.message(CourseFlow.description)
async def course_desc(message:Message,state:FSMContext):
    await state.update_data(description="" if message.text=="." else message.text); await state.set_state(CourseFlow.url); await message.answer("Пришли ссылку https://")

@router.message(CourseFlow.url)
async def course_url(message:Message,state:FSMContext):
    if not message.text or not message.text.startswith("https://"):
        await message.answer("Нужна ссылка, начинающаяся с https://"); return
    d=await state.get_data()
    async with await connect() as db:
        await db.execute("INSERT INTO courses(title,description,url) VALUES(?,?,?)",(d["title"],d["description"],message.text.strip())); await db.commit()
    await state.clear(); await message.answer("Курс добавлен 💗",reply_markup=admin_menu())

@router.callback_query(F.data == "courseadm:list")
async def list_courses(callback:CallbackQuery):
    if not is_admin(callback.from_user.id): return
    async with await connect() as db:
        cur=await db.execute("SELECT id,title,active FROM courses ORDER BY id DESC"); rows=await cur.fetchall()
    if not rows: await callback.message.answer("Курсов пока нет.")
    for r in rows:
        await callback.message.answer(f"{r['id']}. {r['title']} — {'включён' if r['active'] else 'выключен'}",
          reply_markup=inline([("Вкл/выкл",f"ctoggle:{r['id']}"),("Удалить",f"cdelete:{r['id']}")],"course"))
    await callback.answer()

@router.callback_query(F.data.startswith("course:ctoggle:"))
async def toggle_course(callback:CallbackQuery):
    if not is_admin(callback.from_user.id): return
    cid=int(callback.data.split(":")[2])
    async with await connect() as db:
        await db.execute("UPDATE courses SET active=1-active WHERE id=?",(cid,)); await db.commit()
    await callback.answer("Статус изменён")

@router.callback_query(F.data.startswith("course:cdelete:"))
async def delete_course(callback:CallbackQuery):
    if not is_admin(callback.from_user.id): return
    cid=int(callback.data.split(":")[2])
    async with await connect() as db:
        await db.execute("DELETE FROM courses WHERE id=?",(cid,)); await db.commit()
    await callback.answer("Удалено")

@router.message(F.text == "🧩 Рекламная вставка")
async def insert_ad_start(message:Message,state:FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdFlow.insert_content); await message.answer("Отправь текст рекламной вставки. Чтобы отключить её, отправь /disable_insert.")

@router.message(AdFlow.insert_content, F.text == "/disable_insert")
async def disable_insert(message:Message,state:FSMContext):
    await set_value("ad_insert",""); await state.clear(); await message.answer("Рекламная вставка отключена.")

@router.message(AdFlow.insert_content)
async def save_insert(message:Message,state:FSMContext):
    if not message.text: await message.answer("Пока рекламная вставка поддерживает текст. Пришли текст."); return
    await set_value("ad_insert",message.html_text); await state.clear(); await message.answer("Рекламная вставка сохранена 💗")

@router.message(F.text == "📨 Рассылка")
async def campaign_start(message:Message,state:FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(CampaignFlow.content); await message.answer("Отправь сообщение для рассылки (текст, фото, видео или документ).")

@router.message(CampaignFlow.content)
async def campaign_content(message:Message,state:FSMContext):
    if not (message.text or message.photo or message.video or message.document):
        await message.answer("Поддерживаются текст, фото, видео и документы."); return
    await state.update_data(source_chat=message.chat.id,source_message=message.message_id)
    await state.set_state(CampaignFlow.interval)
    await message.answer("Выбери интервал:",reply_markup=inline([("1 час",60),("6 часов",360),("12 часов",720),("24 часа",1440)],"campint"))

@router.callback_query(F.data.startswith("campint:"))
async def campaign_interval(callback:CallbackQuery,state:FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.update_data(interval=int(callback.data.split(":")[1]))
    await state.set_state(CampaignFlow.duration)
    await callback.message.answer("На какой срок запустить рассылку?",reply_markup=inline([("1 час",60),("6 часов",360),("12 часов",720),("24 часа",1440),("Бессрочно","forever")],"campdur"))
    await callback.answer()

@router.callback_query(F.data.startswith("campdur:"))
async def campaign_duration(callback:CallbackQuery,state:FSMContext):
    if not is_admin(callback.from_user.id): return
    data=await state.get_data()
    import time
    duration=callback.data.split(":")[1]
    duration_minutes=None if duration=="forever" else int(duration)
    now=time.time()
    async with await connect() as db:
        await db.execute("INSERT INTO campaigns(kind,chat_id,message_id,interval_minutes,duration_minutes,started_at,next_at,expires_at) VALUES('broadcast',?,?,?,?,?,?,?)",
          (data["source_chat"],data["source_message"],data["interval"],duration_minutes,now,now, None if duration_minutes is None else now+duration_minutes*60))
        await db.commit()
    await state.clear(); await callback.message.answer("Рассылка запущена 💗",reply_markup=admin_menu()); await callback.answer()

@router.message(F.text == "📢 Реклама")
async def ad_start(message:Message,state:FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdFlow.ad_content)
    await message.answer("Отправь рекламное сообщение (текст, фото, видео или документ).")

@router.message(AdFlow.ad_content)
async def ad_content(message:Message,state:FSMContext):
    if not (message.text or message.photo or message.video or message.document):
        await message.answer("Поддерживаются текст, фото, видео и документы."); return
    await state.update_data(source_chat=message.chat.id,source_message=message.message_id)
    await state.set_state(AdFlow.ad_interval)
    await message.answer("Выбери интервал показа рекламы:",reply_markup=inline([("1 час",60),("3 часа",180),("6 часов",360),("12 часов",720)],"adint"))

@router.callback_query(F.data.startswith("adint:"))
async def ad_interval(callback:CallbackQuery,state:FSMContext):
    if not is_admin(callback.from_user.id): return
    data=await state.get_data()
    import time
    now=time.time()
    async with await connect() as db:
        await db.execute("INSERT INTO campaigns(kind,chat_id,message_id,interval_minutes,duration_minutes,started_at,next_at,expires_at) VALUES('ad',?,?,?,?,?,?,NULL)",
          (data["source_chat"],data["source_message"],int(callback.data.split(":")[1]),None,now,now))
        await db.commit()
    await state.clear()
    await callback.message.answer("Реклама запущена 💗",reply_markup=admin_menu())
    await callback.answer()

@router.message(AdFlow.ad_content, F.text == "/ad_cancel")
async def ad_cancel(message:Message,state:FSMContext):
    await state.clear(); await message.answer("Отменено.",reply_markup=admin_menu())
